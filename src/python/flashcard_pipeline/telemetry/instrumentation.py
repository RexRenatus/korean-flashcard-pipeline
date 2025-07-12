"""Auto-instrumentation utilities for Flashcard Pipeline components"""

import logging
import time
import functools
import inspect
from typing import Any, Callable, Optional, Dict, Type, List
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.instrumentation.utils import unwrap

from .tracer import get_tracer, record_metric, create_span
from .context import get_current_span, set_trace_baggage

logger = logging.getLogger(__name__)


def instrument_function(
    func: Callable,
    span_name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False,
    record_result: bool = False,
    measure_latency: bool = True,
    error_metric: bool = True
) -> Callable:
    """Instrument a synchronous function with tracing and metrics
    
    Args:
        func: Function to instrument
        span_name: Custom span name (defaults to function name)
        kind: Span kind
        attributes: Additional span attributes
        record_args: Whether to record function arguments
        record_result: Whether to record function result
        measure_latency: Whether to measure execution time
        error_metric: Whether to record error metrics
        
    Returns:
        Instrumented function
    """
    name = span_name or f"{func.__module__}.{func.__name__}"
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        span_attributes = {
            "code.function": func.__name__,
            "code.namespace": func.__module__,
        }
        
        if attributes:
            span_attributes.update(attributes)
        
        if record_args:
            # Record non-sensitive arguments
            _record_function_args(span_attributes, func, args, kwargs)
        
        start_time = time.time() if measure_latency else None
        
        with create_span(name, kind=kind, attributes=span_attributes) as span:
            try:
                result = func(*args, **kwargs)
                
                if record_result and result is not None:
                    span.set_attribute("result.type", type(result).__name__)
                    if hasattr(result, "__len__"):
                        span.set_attribute("result.length", len(result))
                
                if measure_latency:
                    latency = (time.time() - start_time) * 1000  # ms
                    span.set_attribute("duration.ms", latency)
                    record_metric(
                        f"{name}.latency",
                        latency,
                        metric_type="histogram",
                        attributes={"function": func.__name__},
                        unit="ms"
                    )
                
                return result
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                if error_metric:
                    record_metric(
                        f"{name}.errors",
                        1,
                        metric_type="counter",
                        attributes={
                            "function": func.__name__,
                            "error_type": type(e).__name__
                        }
                    )
                raise
    
    # Mark as instrumented
    wrapper.__wrapped__ = func
    wrapper.__instrumented__ = True
    
    return wrapper


def instrument_async_function(
    func: Callable,
    span_name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False,
    record_result: bool = False,
    measure_latency: bool = True,
    error_metric: bool = True
) -> Callable:
    """Instrument an asynchronous function with tracing and metrics"""
    name = span_name or f"{func.__module__}.{func.__name__}"
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        span_attributes = {
            "code.function": func.__name__,
            "code.namespace": func.__module__,
            "code.async": True,
        }
        
        if attributes:
            span_attributes.update(attributes)
        
        if record_args:
            _record_function_args(span_attributes, func, args, kwargs)
        
        start_time = time.time() if measure_latency else None
        
        with create_span(name, kind=kind, attributes=span_attributes) as span:
            try:
                result = await func(*args, **kwargs)
                
                if record_result and result is not None:
                    span.set_attribute("result.type", type(result).__name__)
                    if hasattr(result, "__len__"):
                        span.set_attribute("result.length", len(result))
                
                if measure_latency:
                    latency = (time.time() - start_time) * 1000
                    span.set_attribute("duration.ms", latency)
                    record_metric(
                        f"{name}.latency",
                        latency,
                        metric_type="histogram",
                        attributes={"function": func.__name__},
                        unit="ms"
                    )
                
                return result
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                
                if error_metric:
                    record_metric(
                        f"{name}.errors",
                        1,
                        metric_type="counter",
                        attributes={
                            "function": func.__name__,
                            "error_type": type(e).__name__
                        }
                    )
                raise
    
    wrapper.__wrapped__ = func
    wrapper.__instrumented__ = True
    
    return wrapper


def instrument_method(
    span_name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False,
    record_result: bool = False,
    measure_latency: bool = True,
    error_metric: bool = True
):
    """Decorator to instrument a class method"""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            return instrument_async_function(
                func, span_name, kind, attributes,
                record_args, record_result, measure_latency, error_metric
            )
        else:
            return instrument_function(
                func, span_name, kind, attributes,
                record_args, record_result, measure_latency, error_metric
            )
    
    return decorator


def instrument_class(
    cls: Type,
    methods: Optional[List[str]] = None,
    exclude_methods: Optional[List[str]] = None,
    span_prefix: Optional[str] = None,
    **instrument_kwargs
) -> Type:
    """Instrument all or specific methods of a class
    
    Args:
        cls: Class to instrument
        methods: Specific methods to instrument (None = all public methods)
        exclude_methods: Methods to exclude from instrumentation
        span_prefix: Prefix for span names
        **instrument_kwargs: Arguments passed to instrument_method
        
    Returns:
        Instrumented class
    """
    exclude_methods = exclude_methods or []
    exclude_methods.extend(['__init__', '__new__', '__del__'])
    
    class_name = f"{cls.__module__}.{cls.__name__}"
    
    # Get methods to instrument
    if methods:
        methods_to_instrument = methods
    else:
        methods_to_instrument = [
            name for name in dir(cls)
            if not name.startswith('_') and callable(getattr(cls, name))
        ]
    
    # Instrument each method
    for method_name in methods_to_instrument:
        if method_name in exclude_methods:
            continue
        
        try:
            method = getattr(cls, method_name)
            if not callable(method):
                continue
            
            # Skip already instrumented methods
            if hasattr(method, '__instrumented__'):
                continue
            
            # Create span name
            if span_prefix:
                span_name = f"{span_prefix}.{method_name}"
            else:
                span_name = f"{class_name}.{method_name}"
            
            # Instrument the method
            instrumented = instrument_method(
                span_name=span_name,
                **instrument_kwargs
            )(method)
            
            setattr(cls, method_name, instrumented)
            
        except Exception as e:
            logger.warning(f"Failed to instrument {class_name}.{method_name}: {e}")
    
    # Mark class as instrumented
    cls.__instrumented__ = True
    
    return cls


def _record_function_args(
    attributes: Dict[str, Any],
    func: Callable,
    args: tuple,
    kwargs: dict,
    max_length: int = 100
) -> None:
    """Record function arguments as span attributes
    
    Args:
        attributes: Dictionary to add attributes to
        func: Function being called
        args: Positional arguments
        kwargs: Keyword arguments
        max_length: Maximum string length for argument values
    """
    try:
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        for param_name, param_value in bound_args.arguments.items():
            # Skip 'self' and 'cls' parameters
            if param_name in ('self', 'cls'):
                continue
            
            # Convert value to string and limit length
            value_str = str(param_value)
            if len(value_str) > max_length:
                value_str = value_str[:max_length] + "..."
            
            attributes[f"arg.{param_name}"] = value_str
            attributes[f"arg.{param_name}.type"] = type(param_value).__name__
            
    except Exception as e:
        logger.debug(f"Failed to record function arguments: {e}")


class ComponentInstrumentor:
    """Base class for component-specific instrumentation"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.tracer = get_tracer()
        self._instrumented = False
    
    def instrument(self) -> None:
        """Instrument the component"""
        if self._instrumented:
            logger.warning(f"{self.component_name} already instrumented")
            return
        
        self._instrument_component()
        self._instrumented = True
        logger.info(f"{self.component_name} instrumented successfully")
    
    def uninstrument(self) -> None:
        """Remove instrumentation from the component"""
        if not self._instrumented:
            return
        
        self._uninstrument_component()
        self._instrumented = False
        logger.info(f"{self.component_name} instrumentation removed")
    
    def _instrument_component(self) -> None:
        """Override in subclasses to implement component-specific instrumentation"""
        raise NotImplementedError
    
    def _uninstrument_component(self) -> None:
        """Override in subclasses to implement component-specific uninstrumentation"""
        raise NotImplementedError


class DatabaseInstrumentor(ComponentInstrumentor):
    """Instrumentor for database operations"""
    
    def __init__(self):
        super().__init__("Database")
    
    def _instrument_component(self) -> None:
        """Add database-specific instrumentation"""
        # This would be implemented to wrap database operations
        # For now, we'll use manual instrumentation in DatabaseManager
        pass
    
    def _uninstrument_component(self) -> None:
        """Remove database instrumentation"""
        pass


class CacheInstrumentor(ComponentInstrumentor):
    """Instrumentor for cache operations"""
    
    def __init__(self):
        super().__init__("Cache")
    
    def _instrument_component(self) -> None:
        """Add cache-specific instrumentation"""
        # This would be implemented to wrap cache operations
        # For now, we'll use manual instrumentation in CacheManager
        pass
    
    def _uninstrument_component(self) -> None:
        """Remove cache instrumentation"""
        pass


class APIClientInstrumentor(ComponentInstrumentor):
    """Instrumentor for API client operations"""
    
    def __init__(self):
        super().__init__("APIClient")
    
    def _instrument_component(self) -> None:
        """Add API client instrumentation"""
        # This would wrap HTTP client operations
        # For now, we'll use manual instrumentation
        pass
    
    def _uninstrument_component(self) -> None:
        """Remove API client instrumentation"""
        pass


# Convenience function to instrument all components
def instrument_all() -> None:
    """Instrument all Flashcard Pipeline components"""
    instrumentors = [
        DatabaseInstrumentor(),
        CacheInstrumentor(),
        APIClientInstrumentor(),
    ]
    
    for instrumentor in instrumentors:
        try:
            instrumentor.instrument()
        except Exception as e:
            logger.error(f"Failed to instrument {instrumentor.component_name}: {e}")