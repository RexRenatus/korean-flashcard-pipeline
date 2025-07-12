#!/usr/bin/env python3
"""
Debug hooks system for the flashcard pipeline.
Integrates with ref.tools MCP for enhanced debugging capabilities.
"""

import os
import sys
import json
import logging
import functools
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Callable, List
from pathlib import Path
import inspect
import time
from contextlib import contextmanager

# Configure debug logger
debug_logger = logging.getLogger("debug_hooks")
debug_handler = logging.FileHandler("debug_hooks.log")
debug_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
debug_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_handler)
debug_logger.setLevel(logging.DEBUG)


class DebugHooks:
    """Central debugging hooks system with ref.tools integration."""
    
    def __init__(self):
        self.enabled = os.environ.get('DEBUG_HOOKS', 'true').lower() == 'true'
        self.ref_tools_enabled = os.environ.get('REF_TOOLS_ENABLED', 'true').lower() == 'true'
        self.breakpoints = set()
        self.watch_variables = {}
        self.performance_traces = []
        self.api_traces = []
        self.error_contexts = []
        
    def hook(self, name: str = None, log_args: bool = True, log_result: bool = True, 
             measure_time: bool = True, ref_search: bool = False):
        """
        Decorator to add debugging hooks to functions.
        
        Args:
            name: Custom name for the hook
            log_args: Log function arguments
            log_result: Log function result
            measure_time: Measure execution time
            ref_search: Enable ref.tools search on errors
        """
        def decorator(func: Callable):
            hook_name = name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                # Pre-execution hook
                start_time = time.time()
                call_id = f"{hook_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                
                debug_logger.debug(f"[HOOK START] {hook_name}")
                
                if log_args:
                    # Get argument names
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    debug_logger.debug(f"[ARGS] {hook_name}: {json.dumps(self._serialize_args(bound_args.arguments), indent=2)}")
                
                # Check breakpoints
                if hook_name in self.breakpoints:
                    self._handle_breakpoint(hook_name, bound_args.arguments if log_args else {})
                
                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Post-execution hook
                    if log_result:
                        debug_logger.debug(f"[RESULT] {hook_name}: {self._serialize_result(result)}")
                    
                    if measure_time:
                        elapsed = time.time() - start_time
                        debug_logger.debug(f"[TIMING] {hook_name}: {elapsed:.3f}s")
                        self.performance_traces.append({
                            "function": hook_name,
                            "call_id": call_id,
                            "duration": elapsed,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    return result
                    
                except Exception as e:
                    # Error hook
                    error_context = {
                        "function": hook_name,
                        "call_id": call_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc(),
                        "args": self._serialize_args(bound_args.arguments) if log_args else {},
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    self.error_contexts.append(error_context)
                    debug_logger.error(f"[ERROR] {hook_name}: {e}")
                    debug_logger.error(f"[TRACEBACK]\n{error_context['traceback']}")
                    
                    if ref_search and self.ref_tools_enabled:
                        self._search_error_docs(e, hook_name)
                    
                    raise
                    
            return wrapper
        return decorator
    
    def api_hook(self, endpoint: str):
        """Special hook for API calls with enhanced debugging."""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                call_id = f"api_{endpoint}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                debug_logger.debug(f"[API CALL START] {endpoint}")
                
                # Log request details
                request_data = {
                    "endpoint": endpoint,
                    "call_id": call_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                if args and hasattr(args[0], '__dict__'):
                    request_data["request_body"] = self._serialize_args(args[0].__dict__)
                
                debug_logger.debug(f"[API REQUEST] {json.dumps(request_data, indent=2)}")
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Log response
                    response_data = {
                        "endpoint": endpoint,
                        "call_id": call_id,
                        "duration": time.time() - start_time,
                        "status": "success",
                        "response_preview": str(result)[:500] if result else None
                    }
                    
                    debug_logger.debug(f"[API RESPONSE] {json.dumps(response_data, indent=2)}")
                    self.api_traces.append(response_data)
                    
                    return result
                    
                except Exception as e:
                    # Log API error
                    error_data = {
                        "endpoint": endpoint,
                        "call_id": call_id,
                        "duration": time.time() - start_time,
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    
                    debug_logger.error(f"[API ERROR] {json.dumps(error_data, indent=2)}")
                    self.api_traces.append(error_data)
                    
                    if self.ref_tools_enabled:
                        debug_logger.info(f"[REF.TOOLS] Search for API error: {endpoint} {type(e).__name__}")
                    
                    raise
                    
            return wrapper
        return decorator
    
    @contextmanager
    def trace_block(self, name: str, **context):
        """Context manager for tracing code blocks."""
        if not self.enabled:
            yield
            return
            
        debug_logger.debug(f"[BLOCK START] {name}")
        if context:
            debug_logger.debug(f"[CONTEXT] {name}: {json.dumps(context, indent=2)}")
        
        start_time = time.time()
        
        try:
            yield self
        except Exception as e:
            debug_logger.error(f"[BLOCK ERROR] {name}: {e}")
            raise
        finally:
            elapsed = time.time() - start_time
            debug_logger.debug(f"[BLOCK END] {name}: {elapsed:.3f}s")
    
    def checkpoint(self, name: str, **data):
        """Create a debug checkpoint with optional data."""
        if not self.enabled:
            return
            
        checkpoint_data = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        debug_logger.debug(f"[CHECKPOINT] {json.dumps(checkpoint_data, indent=2)}")
    
    def watch(self, name: str, value: Any):
        """Watch a variable for changes."""
        if not self.enabled:
            return
            
        old_value = self.watch_variables.get(name)
        if old_value != value:
            debug_logger.debug(f"[WATCH] {name}: {old_value} -> {value}")
            self.watch_variables[name] = value
    
    def set_breakpoint(self, function_name: str):
        """Set a breakpoint on a function."""
        self.breakpoints.add(function_name)
        debug_logger.info(f"[BREAKPOINT SET] {function_name}")
    
    def _handle_breakpoint(self, name: str, args: Dict):
        """Handle breakpoint - in real implementation, this could pause execution."""
        debug_logger.warning(f"[BREAKPOINT HIT] {name}")
        debug_logger.warning(f"[BREAKPOINT ARGS] {json.dumps(self._serialize_args(args), indent=2)}")
        # In a real debugger, this would pause execution
        # For now, just log extensively
    
    def _serialize_args(self, args: Any) -> Any:
        """Serialize arguments for logging."""
        if isinstance(args, (str, int, float, bool, type(None))):
            return args
        elif isinstance(args, (list, tuple)):
            return [self._serialize_args(item) for item in args]
        elif isinstance(args, dict):
            return {k: self._serialize_args(v) for k, v in args.items()}
        elif hasattr(args, '__dict__'):
            return self._serialize_args(args.__dict__)
        else:
            return str(args)
    
    def _serialize_result(self, result: Any) -> str:
        """Serialize function result for logging."""
        serialized = self._serialize_args(result)
        result_str = json.dumps(serialized, indent=2) if isinstance(serialized, (dict, list)) else str(serialized)
        if len(result_str) > 1000:
            return result_str[:1000] + "... (truncated)"
        return result_str
    
    def _search_error_docs(self, error: Exception, context: str):
        """Integration point for ref.tools error search."""
        debug_logger.info(f"[REF.TOOLS] Would search for: {type(error).__name__} in context: {context}")
        # This is where ref.tools MCP would be called
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance analysis report."""
        if not self.performance_traces:
            return {"message": "No performance data collected"}
        
        # Analyze performance data
        function_stats = {}
        for trace in self.performance_traces:
            func_name = trace["function"]
            if func_name not in function_stats:
                function_stats[func_name] = {
                    "calls": 0,
                    "total_time": 0,
                    "min_time": float('inf'),
                    "max_time": 0
                }
            
            stats = function_stats[func_name]
            stats["calls"] += 1
            stats["total_time"] += trace["duration"]
            stats["min_time"] = min(stats["min_time"], trace["duration"])
            stats["max_time"] = max(stats["max_time"], trace["duration"])
        
        # Calculate averages
        for stats in function_stats.values():
            stats["avg_time"] = stats["total_time"] / stats["calls"]
        
        return {
            "function_stats": function_stats,
            "total_traces": len(self.performance_traces),
            "slowest_calls": sorted(self.performance_traces, key=lambda x: x["duration"], reverse=True)[:10]
        }
    
    def get_error_report(self) -> Dict[str, Any]:
        """Get error analysis report."""
        if not self.error_contexts:
            return {"message": "No errors recorded"}
        
        error_summary = {}
        for error in self.error_contexts:
            error_type = error["error_type"]
            if error_type not in error_summary:
                error_summary[error_type] = []
            error_summary[error_type].append({
                "function": error["function"],
                "message": error["error_message"],
                "timestamp": error["timestamp"]
            })
        
        return {
            "total_errors": len(self.error_contexts),
            "error_types": error_summary,
            "recent_errors": self.error_contexts[-10:]
        }
    
    def save_debug_session(self, filepath: str = "debug_session.json"):
        """Save debug session data."""
        session_data = {
            "timestamp": datetime.now().isoformat(),
            "performance_traces": self.performance_traces,
            "api_traces": self.api_traces,
            "error_contexts": self.error_contexts,
            "watch_variables": self.watch_variables,
            "performance_report": self.get_performance_report(),
            "error_report": self.get_error_report()
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        debug_logger.info(f"[SESSION SAVED] {filepath}")


# Global debug hooks instance
debug_hooks = DebugHooks()

# Convenience decorators
hook = debug_hooks.hook
api_hook = debug_hooks.api_hook
trace_block = debug_hooks.trace_block
checkpoint = debug_hooks.checkpoint
watch = debug_hooks.watch