"""Unit tests for OpenTelemetry instrumentation"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock

from flashcard_pipeline.telemetry import (
    init_telemetry,
    get_tracer,
    get_meter,
    create_span,
    record_metric,
    set_span_attributes,
    add_event,
    record_exception,
)
from flashcard_pipeline.telemetry.context import (
    extract_context,
    inject_context,
    get_current_span,
    set_trace_baggage,
    get_trace_baggage,
    get_trace_id,
    get_span_id,
)
from flashcard_pipeline.telemetry.instrumentation import (
    instrument_function,
    instrument_async_function,
    instrument_method,
    instrument_class,
)
from flashcard_pipeline.telemetry.exporters import (
    ExporterConfig,
    ExporterType,
    configure_exporters,
    create_default_exporters,
)

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


class TestTracer:
    """Test core tracer functionality"""
    
    @pytest.fixture
    def memory_exporter(self):
        """Create in-memory span exporter for testing"""
        return InMemorySpanExporter()
    
    @pytest.fixture
    def test_tracer(self, memory_exporter):
        """Create test tracer with memory exporter"""
        provider = TracerProvider()
        processor = SimpleSpanProcessor(memory_exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        return trace.get_tracer(__name__)
    
    def test_init_telemetry(self):
        """Test telemetry initialization"""
        init_telemetry(
            service_name="test-service",
            service_version="1.0.0",
            environment="test",
            enable_console_export=False
        )
        
        tracer = get_tracer()
        assert tracer is not None
        
        meter = get_meter()
        assert meter is not None
    
    def test_create_span(self, test_tracer, memory_exporter):
        """Test span creation"""
        with create_span("test.operation") as span:
            assert span is not None
            assert span.is_recording()
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test.operation"
    
    def test_span_attributes(self, test_tracer, memory_exporter):
        """Test setting span attributes"""
        with create_span("test.attributes") as span:
            set_span_attributes({
                "user.id": "123",
                "request.method": "GET",
                "response.status": 200
            })
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        attributes = spans[0].attributes
        assert attributes["user.id"] == "123"
        assert attributes["request.method"] == "GET"
        assert attributes["response.status"] == 200
    
    def test_span_events(self, test_tracer, memory_exporter):
        """Test adding events to spans"""
        with create_span("test.events"):
            add_event("user_login", {"user.id": "123"})
            add_event("permission_check", {"result": "allowed"})
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        events = spans[0].events
        assert len(events) == 2
        assert events[0].name == "user_login"
        assert events[0].attributes["user.id"] == "123"
        assert events[1].name == "permission_check"
    
    def test_span_exception(self, test_tracer, memory_exporter):
        """Test exception recording"""
        try:
            with create_span("test.exception"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.status.status_code == trace.StatusCode.ERROR
        assert "ValueError" in span.status.description
        
        # Check exception was recorded
        events = [e for e in span.events if "exception" in e.name]
        assert len(events) > 0
    
    def test_nested_spans(self, test_tracer, memory_exporter):
        """Test nested span creation"""
        with create_span("parent.operation"):
            with create_span("child.operation"):
                pass
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 2
        
        # Find parent and child
        parent = next(s for s in spans if s.name == "parent.operation")
        child = next(s for s in spans if s.name == "child.operation")
        
        # Verify parent-child relationship
        assert child.parent.span_id == parent.context.span_id


class TestContext:
    """Test context propagation"""
    
    def test_baggage(self):
        """Test baggage get/set"""
        set_trace_baggage("user.id", "123")
        set_trace_baggage("session.id", "abc")
        
        assert get_trace_baggage("user.id") == "123"
        assert get_trace_baggage("session.id") == "abc"
        assert get_trace_baggage("missing") is None
    
    def test_trace_ids(self):
        """Test trace and span ID retrieval"""
        with create_span("test.ids") as span:
            trace_id = get_trace_id()
            span_id = get_span_id()
            
            assert trace_id is not None
            assert span_id is not None
            assert len(trace_id) == 32  # Hex string
            assert len(span_id) == 16   # Hex string
    
    def test_context_injection_extraction(self):
        """Test context injection and extraction"""
        with create_span("test.context"):
            # Inject context into carrier
            carrier = {}
            inject_context(carrier)
            
            assert "traceparent" in carrier
            
            # Extract context from carrier
            context = extract_context(carrier)
            assert context is not None


class TestInstrumentation:
    """Test instrumentation decorators"""
    
    @pytest.fixture
    def memory_exporter(self):
        """Create in-memory span exporter"""
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        return exporter
    
    def test_instrument_function(self, memory_exporter):
        """Test function instrumentation"""
        @instrument_function
        def test_func(x, y):
            return x + y
        
        result = test_func(2, 3)
        assert result == 5
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        assert "test_func" in spans[0].name
    
    @pytest.mark.asyncio
    async def test_instrument_async_function(self, memory_exporter):
        """Test async function instrumentation"""
        @instrument_async_function
        async def test_async_func(x, y):
            await asyncio.sleep(0.01)
            return x * y
        
        result = await test_async_func(3, 4)
        assert result == 12
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        assert "test_async_func" in spans[0].name
        assert spans[0].attributes["code.async"] is True
    
    def test_instrument_with_args(self, memory_exporter):
        """Test instrumentation with argument recording"""
        @instrument_function(record_args=True, record_result=True)
        def test_func(name, count=5):
            return f"{name}:{count}"
        
        result = test_func("test", count=10)
        assert result == "test:10"
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        attributes = spans[0].attributes
        assert attributes["arg.name"] == "test"
        assert attributes["arg.count"] == "10"
        assert attributes["result.type"] == "str"
    
    def test_instrument_with_error(self, memory_exporter):
        """Test instrumentation with error handling"""
        @instrument_function(error_metric=True)
        def test_func():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            test_func()
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        
        span = spans[0]
        assert span.status.status_code == trace.StatusCode.ERROR
        assert "RuntimeError" in span.status.description
    
    def test_instrument_class(self, memory_exporter):
        """Test class instrumentation"""
        @instrument_class
        class TestClass:
            def method1(self):
                return "method1"
            
            def method2(self, x):
                return f"method2:{x}"
            
            def _private_method(self):
                return "private"
        
        obj = TestClass()
        
        # Public methods should be instrumented
        assert obj.method1() == "method1"
        assert obj.method2("test") == "method2:test"
        
        # Private method should not be instrumented
        assert obj._private_method() == "private"
        
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 2  # Only public methods
        
        span_names = [s.name for s in spans]
        assert any("method1" in name for name in span_names)
        assert any("method2" in name for name in span_names)


class TestMetrics:
    """Test metrics recording"""
    
    def test_record_counter(self):
        """Test counter metric recording"""
        # Initialize telemetry
        init_telemetry(enable_console_export=False)
        
        # Record counter
        record_metric(
            "test.counter",
            5,
            metric_type="counter",
            attributes={"environment": "test"}
        )
        
        # No exceptions should be raised
        assert True
    
    def test_record_histogram(self):
        """Test histogram metric recording"""
        init_telemetry(enable_console_export=False)
        
        # Record histogram values
        for i in range(10):
            record_metric(
                "test.latency",
                100 + i * 10,
                metric_type="histogram",
                attributes={"operation": "test"},
                unit="ms"
            )
        
        assert True
    
    def test_record_up_down_counter(self):
        """Test up/down counter metric recording"""
        init_telemetry(enable_console_export=False)
        
        # Record up/down counter
        record_metric(
            "test.queue_size",
            10,
            metric_type="up_down_counter"
        )
        
        record_metric(
            "test.queue_size",
            -3,
            metric_type="up_down_counter"
        )
        
        assert True


class TestExporters:
    """Test exporter configuration"""
    
    def test_create_default_exporters(self):
        """Test default exporter creation"""
        # Development environment
        configs = create_default_exporters("development")
        assert any(c.exporter_type == ExporterType.JAEGER for c in configs)
        assert any(c.exporter_type == ExporterType.CONSOLE for c in configs)
        
        # Production environment
        configs = create_default_exporters("production")
        assert any(c.exporter_type == ExporterType.OTLP for c in configs)
        assert any(c.exporter_type == ExporterType.PROMETHEUS for c in configs)
    
    def test_exporter_config(self):
        """Test exporter configuration"""
        config = ExporterConfig(
            exporter_type=ExporterType.OTLP,
            endpoint="localhost:4317",
            headers={"Authorization": "Bearer token"},
            insecure=False,
            timeout=60
        )
        
        assert config.exporter_type == ExporterType.OTLP
        assert config.endpoint == "localhost:4317"
        assert config.headers["Authorization"] == "Bearer token"
        assert config.insecure is False
        assert config.timeout == 60


@pytest.mark.asyncio
class TestInstrumentedComponents:
    """Test instrumented pipeline components"""
    
    async def test_instrumented_database(self, tmp_path):
        """Test instrumented database manager"""
        from flashcard_pipeline.database.database_manager_instrumented import (
            create_instrumented_database_manager
        )
        
        # Create in-memory exporter
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        
        # Create database
        db = create_instrumented_database_manager(":memory:")
        await db.initialize()
        
        # Execute query
        await db.execute("""
            CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)
        """)
        
        await db.execute(
            "INSERT INTO test (value) VALUES (?)",
            ("test_value",)
        )
        
        # Check spans
        spans = exporter.get_finished_spans()
        assert len(spans) > 0
        
        # Find database spans
        db_spans = [s for s in spans if "db." in s.name]
        assert len(db_spans) > 0
        
        # Check attributes
        for span in db_spans:
            assert span.attributes.get("db.system") == "sqlite"
        
        await db.close()
    
    async def test_instrumented_cache(self):
        """Test instrumented cache manager"""
        from flashcard_pipeline.cache.cache_manager_instrumented import (
            create_instrumented_cache_manager
        )
        
        # Create in-memory exporter
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        
        # Create cache
        cache = create_instrumented_cache_manager()
        
        # Cache operations
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"
        
        # Cache miss
        value = await cache.get("missing_key")
        assert value is None
        
        # Check spans
        spans = exporter.get_finished_spans()
        cache_spans = [s for s in spans if "cache." in s.name]
        assert len(cache_spans) > 0
        
        # Find specific operations
        set_spans = [s for s in cache_spans if s.name == "cache.set"]
        get_spans = [s for s in cache_spans if s.name == "cache.get"]
        
        assert len(set_spans) == 1
        assert len(get_spans) == 2  # One hit, one miss
        
        # Check hit/miss attributes
        hit_span = next(s for s in get_spans if s.attributes.get("cache.hit") is True)
        miss_span = next(s for s in get_spans if s.attributes.get("cache.hit") is False)
        
        assert hit_span.attributes["cache.key"] == "key1"
        assert miss_span.attributes["cache.key"] == "missing_key"