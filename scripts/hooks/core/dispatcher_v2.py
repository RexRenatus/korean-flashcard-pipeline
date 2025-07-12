#!/usr/bin/env python3
"""
Enhanced unified hook dispatcher with configuration-based hook selection.
"""
import asyncio
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import logging
import subprocess

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

try:
    from scripts.hooks.core.context_injector import ContextInjector
    CONTEXT_INJECTION_AVAILABLE = True
except ImportError:
    CONTEXT_INJECTION_AVAILABLE = False

try:
    from scripts.hooks.monitors.notifications import get_notification_manager
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False

try:
    from scripts.hooks.monitors.performance import get_monitor
    PERFORMANCE_MONITOR_AVAILABLE = True
except ImportError:
    PERFORMANCE_MONITOR_AVAILABLE = False

try:
    from scripts.hooks.scanners.security import PreflightSecurityScanner
    PREFLIGHT_SCANNER_AVAILABLE = True
except ImportError:
    PREFLIGHT_SCANNER_AVAILABLE = False

@dataclass
class HookResult:
    hook_id: str
    success: bool
    output: Any
    execution_time: float
    cached: bool = False
    error: Optional[str] = None

class UnifiedHookDispatcher:
    def __init__(self, config_dir: Optional[str] = None):
        # Use new config location by default
        if config_dir is None:
            config_dir = str(Path(__file__).parent.parent / "config")
        
        self.config_dir = Path(config_dir)
        self.hooks_config = self._load_config("hooks.json")
        self.security_config = self._load_config("security.json")
        self.performance_config = self._load_config("performance.json")
        
        # Initialize components
        self.cache = {}  # Simple in-memory cache for now
        self.executor = ThreadPoolExecutor(
            max_workers=self.hooks_config.get('global', {}).get('max_workers', 5)
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize context injector if available
        self.context_injector = None
        if CONTEXT_INJECTION_AVAILABLE:
            self.context_injector = ContextInjector()
            self.logger.info("Context injection enabled")
            
        # Initialize notification manager if available
        self.notification_manager = None
        if NOTIFICATIONS_AVAILABLE:
            notification_config = self.performance_config.get('notifications', {})
            self.notification_manager = get_notification_manager(notification_config)
            self.logger.info("Notification system enabled")
            
        # Initialize performance monitor if available
        self.performance_monitor = None
        if PERFORMANCE_MONITOR_AVAILABLE:
            window_size = self.performance_config.get('window_size', 100)
            self.performance_monitor = get_monitor(window_size)
            # Update thresholds from config
            self.performance_monitor.thresholds = self.performance_config.get('thresholds', {})
            self.logger.info("Performance monitoring enabled")
            
        # Initialize pre-flight security scanner if available
        self.security_scanner = None
        if PREFLIGHT_SCANNER_AVAILABLE:
            self.security_scanner = PreflightSecurityScanner(self.security_config)
            self.logger.info("Pre-flight security scanner enabled")
        
    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load configuration file."""
        config_file = self.config_dir / filename
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return {}
            
    async def dispatch(self, 
                      tool_name: str, 
                      operation: str, 
                      context: Dict[str, Any]) -> Dict[str, HookResult]:
        """Dispatch hooks based on tool and operation."""
        # Add basic context info
        context['tool'] = tool_name
        context['operation'] = operation
        
        # Enrich context if context injector is available
        enriched_context = context
        if self.context_injector:
            try:
                enriched_context = await self.context_injector.enrich(context)
                self.logger.debug(f"Context enriched with project info: {enriched_context.get('project', {}).get('type', 'unknown')}")
            except Exception as e:
                self.logger.warning(f"Context injection failed: {e}")
                enriched_context = context
        
        # Run pre-flight security scan if available
        if self.security_scanner and self.security_config.get('enabled', True):
            try:
                passed, security_issues = await self.security_scanner.scan(enriched_context)
                if not passed:
                    # Create a special result for security failure
                    security_report = self.security_scanner.generate_report(security_issues)
                    return {
                        'preflight_security': HookResult(
                            hook_id='preflight_security',
                            success=False,
                            output=security_report,
                            execution_time=0,
                            error='Security scan failed - operation blocked'
                        )
                    }
                elif security_issues:
                    # Log non-critical issues
                    self.logger.warning(f"Security scan found {len(security_issues)} non-critical issues")
            except Exception as e:
                self.logger.error(f"Pre-flight security scan failed: {e}")
        
        # Determine which hooks to run
        hooks = self._select_hooks(tool_name, operation, enriched_context)
        
        # Group hooks by execution strategy
        parallel_hooks = [h for h in hooks if h.get('parallel', True)]
        sequential_hooks = [h for h in hooks if not h.get('parallel', True)]
        
        results = {}
        
        # Execute parallel hooks with enriched context
        if parallel_hooks:
            parallel_results = await self._execute_parallel(parallel_hooks, enriched_context)
            results.update(parallel_results)
            
        # Execute sequential hooks with enriched context
        for hook in sequential_hooks:
            if self._should_execute(hook, results):
                result = await self._execute_hook_async(hook, enriched_context)
                results[hook['id']] = result
                
        return results
        
    def _select_hooks(self, tool: str, operation: str, context: Dict[str, Any]) -> List[Dict]:
        """Select which hooks to run based on configuration."""
        selected = []
        
        # Use enriched context for smarter hook selection
        project_type = context.get('project', {}).get('type', 'unknown')
        file_ext = context.get('file', {}).get('extension', '')
        file_path = context.get('file_path', '')
        is_test = context.get('file', {}).get('is_test', False)
        
        # Get hooks configuration
        hooks_config = self.hooks_config.get('hooks', {})
        operations_config = self.hooks_config.get('operations', {})
        
        # Get hooks for this operation
        if operation in operations_config:
            hook_ids = operations_config[operation].get('hooks', [])
            
            for hook_id in hook_ids:
                if hook_id in hooks_config:
                    hook_config = hooks_config[hook_id]
                    
                    # Check if hook should run for this file
                    if self._should_run_hook(hook_config, file_ext, file_path, is_test):
                        # Build hook dict from config
                        hook = {
                            'id': hook_id,
                            'command': hook_config.get('command'),
                            'parallel': hook_config.get('parallel', True),
                            'timeout': hook_config.get('timeout', self.hooks_config.get('global', {}).get('default_timeout', 5))
                        }
                        
                        # Check dependencies
                        if 'depends_on' in self.hooks_config.get('dependencies', {}).get(hook_id, {}):
                            hook['depends_on'] = self.hooks_config['dependencies'][hook_id]['depends_on']
                            
                        selected.append(hook)
        
        # Sort by priority if specified
        selected.sort(key=lambda h: hooks_config.get(h['id'], {}).get('priority', 999))
        
        # Log hook selection decision
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Selected {len(selected)} hooks for {operation} on {project_type} project")
            
        return selected
        
    def _should_run_hook(self, hook_config: Dict, file_ext: str, file_path: str, is_test: bool) -> bool:
        """Check if a hook should run for the given file."""
        # Check file patterns
        file_patterns = hook_config.get('file_patterns', ['*'])
        exclude_patterns = hook_config.get('exclude_patterns', [])
        
        # Check if file matches any pattern
        file_matches = False
        if '*' in file_patterns:
            file_matches = True
        else:
            for pattern in file_patterns:
                if pattern.startswith('*') and file_ext == pattern[1:]:
                    file_matches = True
                    break
                elif pattern in file_path:
                    file_matches = True
                    break
        
        if not file_matches:
            return False
            
        # Check exclusions
        for pattern in exclude_patterns:
            if pattern in file_path or (is_test and ('test' in pattern)):
                return False
                
        return True
        
    async def _execute_parallel(self, 
                               hooks: List[Dict], 
                               context: Dict[str, Any]) -> Dict[str, HookResult]:
        """Execute hooks in parallel with proper error handling."""
        futures = []
        
        for hook in hooks:
            future = self.executor.submit(self._execute_hook_sync, hook, context)
            futures.append((hook['id'], future))
            
        results = {}
        for hook_id, future in futures:
            try:
                result = future.result(timeout=10)
                results[hook_id] = result
            except Exception as e:
                results[hook_id] = HookResult(
                    hook_id=hook_id,
                    success=False,
                    output=None,
                    execution_time=0,
                    error=str(e)
                )
                
        return results
        
    def _execute_hook_sync(self, hook: Dict, context: Dict[str, Any]) -> HookResult:
        """Synchronous hook execution with caching, notifications, and monitoring."""
        start_time = time.time()
        hook_id = hook['id']
        
        # Notify hook start
        if self.notification_manager:
            self.notification_manager.notify_hook_start(hook_id, context)
        
        # Check cache
        cache_key = self._get_cache_key(hook, context)
        cache_ttl = self._get_cache_ttl(hook_id)
        
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if time.time() - cached_entry['timestamp'] < cache_ttl:
                return HookResult(
                    hook_id=hook_id,
                    success=True,
                    output=cached_entry['value'],
                    execution_time=0,
                    cached=True
                )
            
        try:
            # Prepare environment
            env = os.environ.copy()
            env['HOOK_CONTEXT'] = json.dumps(context)
            
            result = subprocess.run(
                hook['command'].split(),
                capture_output=True,
                text=True,
                timeout=hook.get('timeout', 5),
                env=env
            )
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            output = result.stdout
            
            # Record performance metrics
            if self.performance_monitor:
                self.performance_monitor.record_execution(
                    hook_id=hook_id,
                    execution_time=execution_time,
                    success=success,
                    timeout=False
                )
            
            # Notify hook completion
            if self.notification_manager:
                self.notification_manager.notify_hook_complete(hook_id, success, execution_time)
            
            if success:
                # Cache successful result
                self.cache[cache_key] = {
                    'value': output,
                    'timestamp': time.time()
                }
                
                return HookResult(
                    hook_id=hook_id,
                    success=True,
                    output=output,
                    execution_time=execution_time
                )
            else:
                return HookResult(
                    hook_id=hook_id,
                    success=False,
                    output=None,
                    execution_time=execution_time,
                    error=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            
            # Record timeout
            if self.performance_monitor:
                self.performance_monitor.record_execution(
                    hook_id=hook_id,
                    execution_time=execution_time,
                    success=False,
                    timeout=True
                )
                
            return HookResult(
                hook_id=hook_id,
                success=False,
                output=None,
                execution_time=execution_time,
                error=f"Hook timed out after {hook.get('timeout', 5)}s"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record failure
            if self.performance_monitor:
                self.performance_monitor.record_execution(
                    hook_id=hook_id,
                    execution_time=execution_time,
                    success=False,
                    timeout=False
                )
                
            return HookResult(
                hook_id=hook_id,
                success=False,
                output=None,
                execution_time=execution_time,
                error=str(e)
            )
            
    def _get_cache_key(self, hook: Dict, context: Dict[str, Any]) -> str:
        """Generate cache key for hook result."""
        # Create deterministic key from hook ID and relevant context
        key_data = {
            'hook_id': hook['id'],
            'file_path': context.get('file_path', ''),
            'operation': context.get('operation', ''),
            'file_hash': context.get('file_hash', '')
        }
        
        # Include enriched context in cache key if available
        if 'file' in context and 'hash' in context['file']:
            key_data['file_hash'] = context['file']['hash']
        if 'project' in context and 'git' in context['project']:
            key_data['git_commit'] = context['project']['git'].get('commit', '')
            
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
        
    def _get_cache_ttl(self, hook_id: str) -> int:
        """Get cache TTL for a specific hook."""
        cache_config = self.performance_config.get('cache', {}).get('ttl', {})
        by_hook = cache_config.get('by_hook', {})
        return by_hook.get(hook_id, cache_config.get('default', 300))
        
    def _should_execute(self, hook: Dict, results: Dict[str, HookResult]) -> bool:
        """Check if hook should execute based on dependencies."""
        # Check if dependencies are satisfied
        deps = hook.get('depends_on', [])
        for dep in deps:
            if isinstance(dep, str):
                if dep not in results or not results[dep].success:
                    return False
            elif isinstance(dep, list):
                # List means any one of the dependencies
                if not any(d in results and results[d].success for d in dep):
                    return False
        return True
        
    async def _execute_hook_async(self, hook: Dict, context: Dict[str, Any]) -> HookResult:
        """Async wrapper for hook execution."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_hook_sync, hook, context)

def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Hook Dispatcher')
    parser.add_argument('operation', choices=['validate', 'documentation', 'error'],
                       help='Operation to perform')
    parser.add_argument('--tool', default='Write', help='Tool name')
    parser.add_argument('--file', help='File path')
    parser.add_argument('--context', help='Additional context as JSON')
    parser.add_argument('--config-dir', help='Configuration directory')
    
    args = parser.parse_args()
    
    # Build context
    context = {
        'tool': args.tool,
        'operation': args.operation,
        'file_path': args.file or ''
    }
    
    if args.context:
        try:
            context.update(json.loads(args.context))
        except json.JSONDecodeError:
            print("Error: Invalid JSON context")
            sys.exit(1)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run dispatcher
    dispatcher = UnifiedHookDispatcher(args.config_dir)
    results = asyncio.run(dispatcher.dispatch(args.tool, args.operation, context))
    
    # Print results
    for hook_id, result in results.items():
        print(f"\n{hook_id}:")
        print(f"  Success: {result.success}")
        print(f"  Cached: {result.cached}")
        print(f"  Time: {result.execution_time:.3f}s")
        if result.error:
            print(f"  Error: {result.error}")
        if result.output:
            print(f"  Output: {result.output[:100]}...")

if __name__ == "__main__":
    main()