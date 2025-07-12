"""OpenTelemetry exporters configuration"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter as JaegerThriftExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)


class ExporterType(Enum):
    """Supported exporter types"""
    OTLP = "otlp"
    JAEGER = "jaeger"
    PROMETHEUS = "prometheus"
    CONSOLE = "console"


@dataclass
class ExporterConfig:
    """Configuration for exporters"""
    exporter_type: ExporterType
    endpoint: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    insecure: bool = True
    timeout: int = 30
    compression: Optional[str] = None
    
    # Prometheus specific
    prometheus_port: int = 9090
    
    # Batch processor settings
    max_queue_size: int = 2048
    max_export_batch_size: int = 512
    schedule_delay_millis: int = 5000
    export_timeout_millis: int = 30000
    
    # Metric reader settings
    export_interval_millis: int = 60000  # 1 minute


class OTLPExporter:
    """OTLP (OpenTelemetry Protocol) exporter configuration"""
    
    def __init__(self, config: ExporterConfig):
        self.config = config
        self._span_exporter = None
        self._metric_exporter = None
    
    def get_span_exporter(self) -> OTLPSpanExporter:
        """Get OTLP span exporter"""
        if not self._span_exporter:
            endpoint = self.config.endpoint or os.getenv(
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
                "localhost:4317"
            )
            
            self._span_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                headers=self.config.headers,
                insecure=self.config.insecure,
                timeout=self.config.timeout,
                compression=self.config.compression,
            )
        
        return self._span_exporter
    
    def get_metric_exporter(self) -> OTLPMetricExporter:
        """Get OTLP metric exporter"""
        if not self._metric_exporter:
            endpoint = self.config.endpoint or os.getenv(
                "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
                "localhost:4317"
            )
            
            self._metric_exporter = OTLPMetricExporter(
                endpoint=endpoint,
                headers=self.config.headers,
                insecure=self.config.insecure,
                timeout=self.config.timeout,
                compression=self.config.compression,
            )
        
        return self._metric_exporter
    
    def configure_tracer_provider(self, tracer_provider: TracerProvider) -> None:
        """Configure tracer provider with OTLP exporter"""
        span_processor = BatchSpanProcessor(
            self.get_span_exporter(),
            max_queue_size=self.config.max_queue_size,
            max_export_batch_size=self.config.max_export_batch_size,
            schedule_delay_millis=self.config.schedule_delay_millis,
            export_timeout_millis=self.config.export_timeout_millis,
        )
        tracer_provider.add_span_processor(span_processor)
    
    def configure_meter_provider(self, meter_provider: MeterProvider) -> None:
        """Configure meter provider with OTLP exporter"""
        metric_reader = PeriodicExportingMetricReader(
            self.get_metric_exporter(),
            export_interval_millis=self.config.export_interval_millis,
        )
        meter_provider._sdk_config.metric_readers.append(metric_reader)


class JaegerExporter:
    """Jaeger exporter configuration"""
    
    def __init__(self, config: ExporterConfig):
        self.config = config
        self._span_exporter = None
    
    def get_span_exporter(self) -> JaegerThriftExporter:
        """Get Jaeger span exporter"""
        if not self._span_exporter:
            # Parse endpoint
            endpoint = self.config.endpoint or os.getenv(
                "JAEGER_AGENT_ENDPOINT",
                "localhost:6831"
            )
            
            if ":" in endpoint:
                host, port = endpoint.split(":")
                agent_port = int(port)
            else:
                host = endpoint
                agent_port = 6831
            
            self._span_exporter = JaegerThriftExporter(
                agent_host_name=host,
                agent_port=agent_port,
                udp_split_oversized_batches=True,
            )
        
        return self._span_exporter
    
    def configure_tracer_provider(self, tracer_provider: TracerProvider) -> None:
        """Configure tracer provider with Jaeger exporter"""
        span_processor = BatchSpanProcessor(
            self.get_span_exporter(),
            max_queue_size=self.config.max_queue_size,
            max_export_batch_size=self.config.max_export_batch_size,
            schedule_delay_millis=self.config.schedule_delay_millis,
            export_timeout_millis=self.config.export_timeout_millis,
        )
        tracer_provider.add_span_processor(span_processor)


class PrometheusExporter:
    """Prometheus metrics exporter configuration"""
    
    def __init__(self, config: ExporterConfig):
        self.config = config
        self._metric_reader = None
        self._server_started = False
    
    def get_metric_reader(self) -> PrometheusMetricReader:
        """Get Prometheus metric reader"""
        if not self._metric_reader:
            self._metric_reader = PrometheusMetricReader()
        return self._metric_reader
    
    def start_metrics_server(self) -> None:
        """Start Prometheus metrics HTTP server"""
        if not self._server_started:
            start_http_server(
                port=self.config.prometheus_port,
                addr="0.0.0.0"
            )
            self._server_started = True
            logger.info(f"Prometheus metrics server started on port {self.config.prometheus_port}")
    
    def configure_meter_provider(self, meter_provider: MeterProvider) -> None:
        """Configure meter provider with Prometheus exporter"""
        meter_provider._sdk_config.metric_readers.append(self.get_metric_reader())
        self.start_metrics_server()


class ConsoleExporter:
    """Console exporter for debugging"""
    
    def __init__(self, config: ExporterConfig):
        self.config = config
    
    def configure_tracer_provider(self, tracer_provider: TracerProvider) -> None:
        """Configure tracer provider with console exporter"""
        span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
        tracer_provider.add_span_processor(span_processor)
    
    def configure_meter_provider(self, meter_provider: MeterProvider) -> None:
        """Configure meter provider with console exporter"""
        metric_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=self.config.export_interval_millis,
        )
        meter_provider._sdk_config.metric_readers.append(metric_reader)


def configure_exporters(
    tracer_provider: TracerProvider,
    meter_provider: MeterProvider,
    configs: List[ExporterConfig]
) -> None:
    """Configure multiple exporters for traces and metrics
    
    Args:
        tracer_provider: Tracer provider to configure
        meter_provider: Meter provider to configure
        configs: List of exporter configurations
    """
    for config in configs:
        try:
            if config.exporter_type == ExporterType.OTLP:
                exporter = OTLPExporter(config)
                exporter.configure_tracer_provider(tracer_provider)
                exporter.configure_meter_provider(meter_provider)
                
            elif config.exporter_type == ExporterType.JAEGER:
                exporter = JaegerExporter(config)
                exporter.configure_tracer_provider(tracer_provider)
                
            elif config.exporter_type == ExporterType.PROMETHEUS:
                exporter = PrometheusExporter(config)
                exporter.configure_meter_provider(meter_provider)
                
            elif config.exporter_type == ExporterType.CONSOLE:
                exporter = ConsoleExporter(config)
                exporter.configure_tracer_provider(tracer_provider)
                exporter.configure_meter_provider(meter_provider)
                
            logger.info(f"Configured {config.exporter_type.value} exporter")
            
        except Exception as e:
            logger.error(f"Failed to configure {config.exporter_type.value} exporter: {e}")


def create_default_exporters(environment: str = "development") -> List[ExporterConfig]:
    """Create default exporter configurations based on environment
    
    Args:
        environment: Deployment environment
        
    Returns:
        List of exporter configurations
    """
    configs = []
    
    if environment == "development":
        # Development: Jaeger for traces, Console for debugging
        configs.append(ExporterConfig(
            exporter_type=ExporterType.JAEGER,
            endpoint=os.getenv("JAEGER_ENDPOINT", "localhost:6831")
        ))
        configs.append(ExporterConfig(
            exporter_type=ExporterType.CONSOLE
        ))
        
    elif environment == "production":
        # Production: OTLP for both traces and metrics
        configs.append(ExporterConfig(
            exporter_type=ExporterType.OTLP,
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            headers=_parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")),
            insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true"
        ))
        
        # Prometheus for metrics scraping
        configs.append(ExporterConfig(
            exporter_type=ExporterType.PROMETHEUS,
            prometheus_port=int(os.getenv("PROMETHEUS_PORT", "9090"))
        ))
        
    else:
        # Default: Console only
        configs.append(ExporterConfig(
            exporter_type=ExporterType.CONSOLE
        ))
    
    return configs


def _parse_headers(headers_str: str) -> Dict[str, str]:
    """Parse headers from environment variable format
    
    Args:
        headers_str: Headers in format "key1=value1,key2=value2"
        
    Returns:
        Dictionary of headers
    """
    headers = {}
    if headers_str:
        for header in headers_str.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
    return headers