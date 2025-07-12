"""Instrumented version of API client with OpenTelemetry"""

import time
import aiohttp
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .telemetry import (
    create_span,
    record_metric,
    set_span_attributes,
    inject_context,
    trace_async_method,
)
from .telemetry.context import ContextPropagator
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .api_client import OpenRouterClient, APIResponse


class InstrumentedOpenRouterClient(OpenRouterClient):
    """OpenRouter API client with comprehensive OpenTelemetry instrumentation"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize API client metrics"""
        self.metric_names = {
            "requests": "api.requests",
            "latency": "api.latency",
            "errors": "api.errors",
            "tokens": "api.tokens",
            "rate_limit": "api.rate_limit",
            "retries": "api.retries",
        }
    
    @trace_async_method(
        kind=trace.SpanKind.CLIENT,
        record_args=True,
        measure_latency=True
    )
    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> APIResponse:
        """Create completion with full instrumentation"""
        model = model or self.default_model
        parsed_url = urlparse(self.base_url)
        
        with create_span(
            "api.create_completion",
            kind=trace.SpanKind.CLIENT,
            attributes={
                "http.method": "POST",
                "http.url": f"{self.base_url}/chat/completions",
                "http.scheme": parsed_url.scheme,
                "http.host": parsed_url.netloc,
                "api.model": model,
                "api.temperature": temperature,
                "api.max_tokens": max_tokens,
                "api.message_count": len(messages),
                "api.provider": "openrouter",
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Prepare headers with trace context
                headers = dict(self.headers)
                inject_context(headers)
                
                # Make API call
                response = await super().create_completion(
                    messages, model, temperature, max_tokens, **kwargs
                )
                
                # Record success metrics
                duration = (time.time() - start_time) * 1000
                
                span.set_attributes({
                    "http.status_code": 200,
                    "api.response.id": response.id,
                    "api.response.model": response.model,
                    "api.usage.prompt_tokens": response.usage.get("prompt_tokens", 0),
                    "api.usage.completion_tokens": response.usage.get("completion_tokens", 0),
                    "api.usage.total_tokens": response.usage.get("total_tokens", 0),
                    "api.duration_ms": duration,
                })
                
                # Record metrics
                self._record_request_metrics(
                    model=model,
                    duration=duration,
                    tokens=response.usage.get("total_tokens", 0),
                    status="success"
                )
                
                return response
                
            except aiohttp.ClientResponseError as e:
                # Handle HTTP errors
                span.set_attributes({
                    "http.status_code": e.status,
                    "error.type": "http_error",
                    "error.message": str(e),
                })
                span.set_status(Status(StatusCode.ERROR, f"HTTP {e.status}"))
                
                self._record_error_metrics(
                    model=model,
                    error_type="http_error",
                    status_code=e.status
                )
                
                # Record rate limit metrics
                if e.status == 429:
                    record_metric(
                        self.metric_names["rate_limit"],
                        1,
                        metric_type="counter",
                        attributes={"model": model}
                    )
                
                raise
                
            except Exception as e:
                # Handle other errors
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                self._record_error_metrics(
                    model=model,
                    error_type=type(e).__name__
                )
                
                raise
    
    async def _request_with_retries(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with retry instrumentation"""
        retry_count = 0
        last_error = None
        
        with create_span(
            f"http.{method.lower()}",
            kind=trace.SpanKind.CLIENT,
            attributes={
                "http.method": method,
                "http.url": url,
                "http.retry.enabled": True,
                "http.retry.max_attempts": self.max_retries,
            }
        ) as span:
            while retry_count <= self.max_retries:
                try:
                    # Add retry information
                    if retry_count > 0:
                        span.set_attribute("http.retry.count", retry_count)
                        record_metric(
                            self.metric_names["retries"],
                            1,
                            metric_type="counter",
                            attributes={
                                "attempt": retry_count,
                                "url": urlparse(url).path
                            }
                        )
                    
                    # Make request
                    response = await self.session.request(method, url, **kwargs)
                    response.raise_for_status()
                    
                    span.set_attribute("http.status_code", response.status)
                    return response
                    
                except aiohttp.ClientResponseError as e:
                    last_error = e
                    
                    if e.status not in self.retry_status_codes or retry_count >= self.max_retries:
                        raise
                    
                    # Calculate backoff
                    backoff = self._calculate_backoff(retry_count, e)
                    span.add_event(
                        "http.retry",
                        attributes={
                            "retry_count": retry_count,
                            "status_code": e.status,
                            "backoff_ms": backoff * 1000
                        }
                    )
                    
                    await asyncio.sleep(backoff)
                    retry_count += 1
                    
                except Exception as e:
                    last_error = e
                    raise
            
            # Max retries exceeded
            if last_error:
                raise last_error
    
    def _record_request_metrics(
        self,
        model: str,
        duration: float,
        tokens: int,
        status: str
    ):
        """Record API request metrics"""
        # Request count
        record_metric(
            self.metric_names["requests"],
            1,
            metric_type="counter",
            attributes={
                "model": model,
                "status": status
            }
        )
        
        # Latency
        record_metric(
            self.metric_names["latency"],
            duration,
            metric_type="histogram",
            attributes={
                "model": model,
                "status": status
            },
            unit="ms"
        )
        
        # Token usage
        if tokens > 0:
            record_metric(
                self.metric_names["tokens"],
                tokens,
                metric_type="counter",
                attributes={"model": model}
            )
    
    def _record_error_metrics(
        self,
        model: str,
        error_type: str,
        status_code: Optional[int] = None
    ):
        """Record API error metrics"""
        attributes = {
            "model": model,
            "error_type": error_type
        }
        
        if status_code:
            attributes["status_code"] = str(status_code)
        
        record_metric(
            self.metric_names["errors"],
            1,
            metric_type="counter",
            attributes=attributes
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check with instrumentation"""
        with create_span(
            "api.health_check",
            attributes={"api.provider": "openrouter"}
        ) as span:
            try:
                result = await super().health_check()
                
                span.set_attributes({
                    "health.status": result.get("status", "unknown"),
                    "health.latency_ms": result.get("latency_ms", 0)
                })
                
                # Record health metrics
                record_metric(
                    "api.health.latency",
                    result.get("latency_ms", 0),
                    metric_type="histogram",
                    unit="ms"
                )
                
                record_metric(
                    "api.health.status",
                    1 if result.get("status") == "healthy" else 0,
                    metric_type="gauge"
                )
                
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR))
                
                record_metric(
                    "api.health.status",
                    0,
                    metric_type="gauge"
                )
                
                raise


class InstrumentedFlashcardAPIClient:
    """High-level flashcard API client with instrumentation"""
    
    def __init__(self, api_client: InstrumentedOpenRouterClient):
        self.api_client = api_client
    
    @trace_async_method(
        span_name="flashcard.process_stage1",
        record_args=True
    )
    async def process_stage1(self, word: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Process stage 1 with instrumentation"""
        with create_span(
            "flashcard.stage1",
            attributes={
                "flashcard.word": word,
                "flashcard.has_context": context is not None,
                "flashcard.stage": 1
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Create prompt
                prompt = self._create_stage1_prompt(word, context)
                
                # Call API
                response = await self.api_client.create_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                
                # Parse response
                result = self._parse_stage1_response(response)
                
                duration = (time.time() - start_time) * 1000
                span.set_attributes({
                    "flashcard.duration_ms": duration,
                    "flashcard.difficulty": result.get("difficulty"),
                    "flashcard.translation_count": len(result.get("translations", [])),
                })
                
                # Record business metrics
                record_metric(
                    "flashcard.stage1.processed",
                    1,
                    metric_type="counter",
                    attributes={"difficulty": str(result.get("difficulty", "unknown"))}
                )
                
                record_metric(
                    "flashcard.stage1.duration",
                    duration,
                    metric_type="histogram",
                    unit="ms"
                )
                
                return result
                
            except Exception as e:
                span.record_exception(e)
                
                record_metric(
                    "flashcard.stage1.errors",
                    1,
                    metric_type="counter",
                    attributes={"error_type": type(e).__name__}
                )
                
                raise
    
    @trace_async_method(
        span_name="flashcard.process_stage2",
        record_args=True
    )
    async def process_stage2(self, stage1_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process stage 2 with instrumentation"""
        with create_span(
            "flashcard.stage2",
            attributes={
                "flashcard.word": stage1_result.get("word"),
                "flashcard.stage": 2
            }
        ) as span:
            start_time = time.time()
            
            try:
                # Create prompt
                prompt = self._create_stage2_prompt(stage1_result)
                
                # Call API
                response = await self.api_client.create_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=1000
                )
                
                # Parse response
                result = self._parse_stage2_response(response, stage1_result)
                
                duration = (time.time() - start_time) * 1000
                span.set_attributes({
                    "flashcard.duration_ms": duration,
                    "flashcard.nuance_count": len(result.get("nuances", [])),
                    "flashcard.example_count": len(result.get("examples", [])),
                })
                
                # Record business metrics
                record_metric(
                    "flashcard.stage2.processed",
                    1,
                    metric_type="counter"
                )
                
                record_metric(
                    "flashcard.stage2.duration",
                    duration,
                    metric_type="histogram",
                    unit="ms"
                )
                
                return result
                
            except Exception as e:
                span.record_exception(e)
                
                record_metric(
                    "flashcard.stage2.errors",
                    1,
                    metric_type="counter",
                    attributes={"error_type": type(e).__name__}
                )
                
                raise
    
    def _create_stage1_prompt(self, word: str, context: Optional[str]) -> str:
        """Create stage 1 prompt"""
        # Implementation details...
        return f"Translate '{word}' to English"
    
    def _create_stage2_prompt(self, stage1_result: Dict[str, Any]) -> str:
        """Create stage 2 prompt"""
        # Implementation details...
        return f"Create nuances for {stage1_result['word']}"
    
    def _parse_stage1_response(self, response: APIResponse) -> Dict[str, Any]:
        """Parse stage 1 response"""
        # Implementation details...
        return {
            "word": "example",
            "translations": ["example"],
            "difficulty": 3
        }
    
    def _parse_stage2_response(
        self,
        response: APIResponse,
        stage1_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse stage 2 response"""
        # Implementation details...
        return {
            **stage1_result,
            "nuances": ["nuance1", "nuance2"],
            "examples": ["example1", "example2"]
        }


def create_instrumented_api_client(
    api_key: str,
    **kwargs
) -> InstrumentedFlashcardAPIClient:
    """Factory function to create instrumented API client
    
    Args:
        api_key: OpenRouter API key
        **kwargs: Additional configuration
        
    Returns:
        Instrumented flashcard API client
    """
    openrouter_client = InstrumentedOpenRouterClient(api_key, **kwargs)
    return InstrumentedFlashcardAPIClient(openrouter_client)