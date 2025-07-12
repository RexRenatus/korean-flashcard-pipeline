"""OpenTelemetry instrumentation for Flashcard Pipeline"""

from .tracer import (
    init_telemetry,
    get_tracer,
    get_meter,
    create_span,
    record_metric,
    set_span_attributes,
    add_event,
    record_exception,
)

from .context import (
    extract_context,
    inject_context,
    get_current_span,
    with_span,
    propagate_context,
)

from .instrumentation import (
    instrument_function,
    instrument_async_function,
    instrument_method,
    instrument_class,
)

from .exporters import (
    configure_exporters,
    OTLPExporter,
    JaegerExporter,
    PrometheusExporter,
    ConsoleExporter,
)

__all__ = [
    # Core functions
    "init_telemetry",
    "get_tracer",
    "get_meter",
    "create_span",
    "record_metric",
    "set_span_attributes",
    "add_event",
    "record_exception",
    
    # Context management
    "extract_context",
    "inject_context",
    "get_current_span",
    "with_span",
    "propagate_context",
    
    # Instrumentation decorators
    "instrument_function",
    "instrument_async_function",
    "instrument_method",
    "instrument_class",
    
    # Exporters
    "configure_exporters",
    "OTLPExporter",
    "JaegerExporter", 
    "PrometheusExporter",
    "ConsoleExporter",
]