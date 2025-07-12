#!/usr/bin/env python3
"""
Unified hook dispatcher with intelligent routing and caching.
Consolidates multiple hook operations for better performance.
Enhanced with context injection inspired by Claude Code Development Kit.
"""
import asyncio
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    def __init__(self, config_path: Optional[str] = None):
        # Use new config location by default
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "hooks.json")
        self.config = self._load_config(config_path)
        self.cache = {}  # Simple in-memory cache for now
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.logger = logging.getLogger(__name__)
        
        # Initialize context injector if available
        self.context_injector = None
        if CONTEXT_INJECTION_AVAILABLE:
            self.context_injector = ContextInjector()
            self.logger.info("Context injection enabled")
            
        # Initialize notification manager if available
        self.notification_manager = None
        if NOTIFICATIONS_AVAILABLE:
            self.notification_manager = get_notification_manager()
            self.logger.info("Notification system enabled")
            
        # Initialize performance monitor if available
        self.performance_monitor = None
        if PERFORMANCE_MONITOR_AVAILABLE:
            self.performance_monitor = get_monitor()
            self.logger.info("Performance monitoring enabled")
            
        # Initialize pre-flight security scanner if available
        self.security_scanner = None
        if PREFLIGHT_SCANNER_AVAILABLE:
            self.security_scanner = PreflightSecurityScanner()
            self.logger.info("Pre-flight security scanner enabled")
        
    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load hook configuration."""
        config_file = Path(path)
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return {
            "hooks": [],
            "cache_ttl": 300,
            "parallel_execution": True
        }
            
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
        if self.security_scanner:
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
        """Select which hooks to run based on context."""
        selected = []
        
        # Use enriched context for smarter hook selection
        project_type = context.get('project', {}).get('type', 'unknown')
        file_ext = context.get('file', {}).get('extension', '')
        is_test = context.get('file', {}).get('is_test', False)
        
        # For now, return predefined hook sets based on operation
        if operation == "validate":
            hooks = []
            
            # Always run security check
            hooks.append({"id": "security_check", "command": "python scripts/validators/security_check.py", "parallel": True, "timeout": 3})
            
            # Language-specific syntax check
            if file_ext in ['.py', '.js', '.json', '.yml', '.yaml', '.md', '.sh']:
                hooks.append({"id": "syntax_check", "command": "python scripts/validators/syntax_check.py", "parallel": True, "timeout": 2})
            
            # SOLID check only for non-test Python files
            if file_ext == '.py' and not is_test:
                hooks.append({"id": "solid_check", "command": "python scripts/solid_enforcer_v2.py", "parallel": True, "timeout": 5})
            
            selected = hooks
            
        elif operation == "documentation":
            # Enhanced documentation search with project context
            selected = [
                {"id": "doc_search", "command": "python scripts/mcp_ref_hooks/unified_documentation.py", "parallel": True, "timeout": 8}
            ]
            
        # Log hook selection decision
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Selected {len(selected)} hooks for {operation} on {project_type} project")
            
        return selected
        
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
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if time.time() - cached_entry['timestamp'] < self.config.get('cache_ttl', 300):
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
        
    def _should_execute(self, hook: Dict, results: Dict[str, HookResult]) -> bool:
        """Check if hook should execute based on dependencies."""
        # Check if dependencies are satisfied
        deps = hook.get('depends_on', [])
        for dep in deps:
            if dep not in results or not results[dep].success:
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
    dispatcher = UnifiedHookDispatcher()
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