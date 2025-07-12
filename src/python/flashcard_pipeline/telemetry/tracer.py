"""Core OpenTelemetry tracer and meter setup"""

import os
import logging
from typing import Optional, Dict, Any, Union, Callable
from contextlib import contextmanager
import functools

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.composite import CompositePropagator

logger = logging.getLogger(__name__)

# Global references
_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None
_tracer_provider: Optional[TracerProvider] = None
_meter_provider: Optional[MeterProvider] = None
_initialized: bool = False


def init_telemetry(
    service_name: str = "flashcard-pipeline",
    service_version: str = "1.0.0",
    environment: str = "development",
    enable_console_export: bool = False,
    custom_resource_attributes: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """Initialize OpenTelemetry with tracers and meters
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        environment: Deployment environment (development, staging, production)
        enable_console_export: Whether to export to console for debugging
        custom_resource_attributes: Additional resource attributes
        **kwargs: Additional configuration options
    """
    global _tracer, _meter, _tracer_provider, _meter_provider, _initialized
    
    if _initialized:
        logger.warning("Telemetry already initialized, skipping")
        return
    
    # Create resource
    resource_attributes = {
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment,
        "telemetry.sdk.language": "python",
        "telemetry.sdk.name": "opentelemetry",
    }
    
    if custom_resource_attributes:
        resource_attributes.update(custom_resource_attributes)
    
    resource = Resource.create(resource_attributes)
    
    # Initialize tracing
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)
    
    # Add console exporter if enabled
    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(
            SimpleSpanProcessor(console_exporter)
        )
    
    # Initialize metrics
    if enable_console_export:
        metric_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=kwargs.get("metric_export_interval", 60000)
        )
    else:
        metric_reader = None
    
    _meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader] if metric_reader else []
    )
    metrics.set_meter_provider(_meter_provider)
    
    # Get tracer and meter
    _tracer = trace.get_tracer(
        __name__,
        service_version,
        tracer_provider=_tracer_provider
    )
    _meter = metrics.get_meter(
        __name__,
        service_version,
        meter_provider=_meter_provider
    )
    
    # Set up propagators
    set_global_textmap(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ])
    )
    
    _initialized = True
    logger.info(f"Telemetry initialized for service: {service_name}")


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance"""
    if not _tracer:
        init_telemetry()
    return _tracer


def get_meter() -> metrics.Meter:
    """Get the global meter instance"""
    if not _meter:
        init_telemetry()
    return _meter


@contextmanager
def create_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
):
    """Create a new span with automatic exception handling
    
    Args:
        name: Span name
        kind: Type of span (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        attributes: Initial span attributes
        record_exception: Whether to record exceptions automatically
        set_status_on_exception: Whether to set error status on exception
        
    Yields:
        The created span
    """
    tracer = get_tracer()
    
    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes or {},
        record_exception=record_exception,
        set_status_on_exception=set_status_on_exception
    ) as span:
        try:
            yield span
        except Exception as e:
            if record_exception:
                span.record_exception(e)
            if set_status_on_exception:
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def set_span_attributes(attributes: Dict[str, Any]) -> None:
    """Set attributes on the current span
    
    Args:
        attributes: Dictionary of attributes to set
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current span
    
    Args:
        name: Event name
        attributes: Event attributes
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def record_exception(
    exception: Exception,
    attributes: Optional[Dict[str, Any]] = None,
    escaped: bool = False
) -> None:
    """Record an exception on the current span
    
    Args:
        exception: The exception to record
        attributes: Additional attributes
        escaped: Whether the exception escaped the span
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span.record_exception(exception, attributes=attributes, escaped=escaped)
        if escaped:
            span.set_status(Status(StatusCode.ERROR, str(exception)))


class MetricRecorder:
    """Helper class for recording metrics"""
    
    def __init__(self):
        self._meter = get_meter()
        self._counters = {}
        self._histograms = {}
        self._gauges = {}
        self._up_down_counters = {}
    
    def counter(
        self,
        name: str,
        description: str = "",
        unit: str = "1"
    ) -> metrics.Counter:
        """Get or create a counter metric"""
        if name not in self._counters:
            self._counters[name] = self._meter.create_counter(
                name,
                description=description,
                unit=unit
            )
        return self._counters[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "ms"
    ) -> metrics.Histogram:
        """Get or create a histogram metric"""
        if name not in self._histograms:
            self._histograms[name] = self._meter.create_histogram(
                name,
                description=description,
                unit=unit
            )
        return self._histograms[name]
    
    def gauge(
        self,
        name: str,
        callback: Callable[[CallbackOptions], Observation],
        description: str = "",
        unit: str = "1"
    ) -> metrics.ObservableGauge:
        """Create an observable gauge metric"""
        if name not in self._gauges:
            self._gauges[name] = self._meter.create_observable_gauge(
                name,
                callbacks=[callback],
                description=description,
                unit=unit
            )
        return self._gauges[name]
    
    def up_down_counter(
        self,
        name: str,
        description: str = "",
        unit: str = "1"
    ) -> metrics.UpDownCounter:
        """Get or create an up/down counter metric"""
        if name not in self._up_down_counters:
            self._up_down_counters[name] = self._meter.create_up_down_counter(
                name,
                description=description,
                unit=unit
            )
        return self._up_down_counters[name]


# Global metric recorder
_metric_recorder = MetricRecorder()


def record_metric(
    metric_name: str,
    value: Union[int, float],
    metric_type: str = "counter",
    attributes: Optional[Dict[str, Any]] = None,
    description: str = "",
    unit: str = "1"
) -> None:
    """Record a metric value
    
    Args:
        metric_name: Name of the metric
        value: Value to record
        metric_type: Type of metric (counter, histogram, up_down_counter)
        attributes: Metric attributes/labels
        description: Metric description
        unit: Unit of measurement
    """
    attributes = attributes or {}
    
    if metric_type == "counter":
        counter = _metric_recorder.counter(metric_name, description, unit)
        counter.add(value, attributes)
    elif metric_type == "histogram":
        histogram = _metric_recorder.histogram(metric_name, description, unit)
        histogram.record(value, attributes)
    elif metric_type == "up_down_counter":
        up_down = _metric_recorder.up_down_counter(metric_name, description, unit)
        up_down.add(value, attributes)
    else:
        logger.warning(f"Unknown metric type: {metric_type}")


# Utility decorators for common patterns
def trace_method(
    span_name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False
):
    """Decorator to trace a method or function
    
    Args:
        span_name: Custom span name (defaults to function name)
        kind: Span kind
        attributes: Additional attributes
        record_args: Whether to record function arguments as attributes
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"
            span_attributes = attributes or {}
            
            if record_args:
                # Record function arguments (be careful with sensitive data)
                span_attributes.update({
                    f"arg.{i}": str(arg)[:100]  # Limit length
                    for i, arg in enumerate(args)
                })
                span_attributes.update({
                    f"kwarg.{k}": str(v)[:100]
                    for k, v in kwargs.items()
                })
            
            with create_span(name, kind=kind, attributes=span_attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


def trace_async_method(
    span_name: Optional[str] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_args: bool = False
):
    """Decorator to trace an async method or function"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"
            span_attributes = attributes or {}
            
            if record_args:
                span_attributes.update({
                    f"arg.{i}": str(arg)[:100]
                    for i, arg in enumerate(args)
                })
                span_attributes.update({
                    f"kwarg.{k}": str(v)[:100]
                    for k, v in kwargs.items()
                })
            
            with create_span(name, kind=kind, attributes=span_attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator