"""Context propagation utilities for distributed tracing"""

import logging
from typing import Dict, Any, Optional, TypeVar, Callable
from contextlib import contextmanager
import functools

from opentelemetry import trace, baggage
from opentelemetry.propagate import inject, extract
from opentelemetry.trace import Span, Link
from opentelemetry.context import Context, attach, detach, get_current
from opentelemetry.trace.propagation import get_current_span

logger = logging.getLogger(__name__)

T = TypeVar('T')


def extract_context(carrier: Dict[str, Any], getter=None) -> Context:
    """Extract trace context from a carrier (e.g., HTTP headers)
    
    Args:
        carrier: Dictionary containing trace context
        getter: Optional getter function for extracting values
        
    Returns:
        Extracted context
    """
    return extract(carrier, getter=getter)


def inject_context(carrier: Dict[str, Any], context: Optional[Context] = None, setter=None) -> None:
    """Inject trace context into a carrier
    
    Args:
        carrier: Dictionary to inject context into
        context: Optional context to inject (uses current if not provided)
        setter: Optional setter function for injecting values
    """
    inject(carrier, context=context, setter=setter)


def get_current_span() -> Span:
    """Get the currently active span
    
    Returns:
        Current span or invalid span if none active
    """
    return trace.get_current_span()


@contextmanager
def with_span(span: Span):
    """Context manager to make a span current
    
    Args:
        span: Span to make current
        
    Yields:
        The span
    """
    token = trace.use_span(span, end_on_exit=True)
    try:
        yield span
    finally:
        if token:
            trace.use_span(None, token=token)


def propagate_context(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to propagate trace context across function calls
    
    Useful for callbacks, thread pools, and async boundaries
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Capture current context
        ctx = get_current()
        
        # Attach context and execute function
        token = attach(ctx)
        try:
            return func(*args, **kwargs)
        finally:
            detach(token)
    
    return wrapper


def propagate_context_async(func: Callable[..., T]) -> Callable[..., T]:
    """Async version of context propagation decorator"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = get_current()
        token = attach(ctx)
        try:
            return await func(*args, **kwargs)
        finally:
            detach(token)
    
    return wrapper


class TraceContextManager:
    """Manager for trace context with baggage support"""
    
    def __init__(self):
        self._tokens = []
    
    def set_baggage(self, key: str, value: str) -> None:
        """Set a baggage item in the current context
        
        Args:
            key: Baggage key
            value: Baggage value
        """
        ctx = baggage.set_baggage(key, value)
        token = attach(ctx)
        self._tokens.append(token)
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get a baggage item from the current context
        
        Args:
            key: Baggage key
            
        Returns:
            Baggage value or None
        """
        return baggage.get_baggage(key)
    
    def remove_baggage(self, key: str) -> None:
        """Remove a baggage item from the current context
        
        Args:
            key: Baggage key to remove
        """
        ctx = baggage.remove_baggage(key)
        token = attach(ctx)
        self._tokens.append(token)
    
    def get_all_baggage(self) -> Dict[str, str]:
        """Get all baggage items from the current context
        
        Returns:
            Dictionary of all baggage items
        """
        return dict(baggage.get_all())
    
    def clear_context(self) -> None:
        """Clear all attached contexts"""
        for token in reversed(self._tokens):
            detach(token)
        self._tokens.clear()
    
    def create_child_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[Link]] = None
    ) -> Span:
        """Create a child span of the current span
        
        Args:
            name: Span name
            attributes: Span attributes
            links: Links to other spans
            
        Returns:
            Created span
        """
        tracer = trace.get_tracer(__name__)
        return tracer.start_span(
            name,
            attributes=attributes,
            links=links
        )
    
    @contextmanager
    def async_context(self, context: Optional[Context] = None):
        """Context manager for async context propagation
        
        Args:
            context: Optional context to use (uses current if not provided)
            
        Yields:
            The attached context
        """
        ctx = context or get_current()
        token = attach(ctx)
        try:
            yield ctx
        finally:
            detach(token)


# Global context manager instance
_context_manager = TraceContextManager()


def set_trace_baggage(key: str, value: str) -> None:
    """Set a baggage item that will be propagated with the trace
    
    Args:
        key: Baggage key
        value: Baggage value
    """
    _context_manager.set_baggage(key, value)


def get_trace_baggage(key: str) -> Optional[str]:
    """Get a baggage item from the trace context
    
    Args:
        key: Baggage key
        
    Returns:
        Baggage value or None
    """
    return _context_manager.get_baggage(key)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID
    
    Returns:
        Trace ID as hex string or None
    """
    span = get_current_span()
    if span and span.is_recording():
        span_context = span.get_span_context()
        if span_context.is_valid:
            return format(span_context.trace_id, '032x')
    return None


def get_span_id() -> Optional[str]:
    """Get the current span ID
    
    Returns:
        Span ID as hex string or None
    """
    span = get_current_span()
    if span and span.is_recording():
        span_context = span.get_span_context()
        if span_context.is_valid:
            return format(span_context.span_id, '016x')
    return None


def link_spans(spans: List[Span]) -> List[Link]:
    """Create links to other spans
    
    Args:
        spans: List of spans to link to
        
    Returns:
        List of links
    """
    links = []
    for span in spans:
        if span and span.is_recording():
            span_context = span.get_span_context()
            if span_context.is_valid:
                links.append(Link(span_context))
    return links


class ContextPropagator:
    """Helper for propagating context across service boundaries"""
    
    @staticmethod
    def to_headers(context: Optional[Context] = None) -> Dict[str, str]:
        """Convert context to HTTP headers
        
        Args:
            context: Optional context (uses current if not provided)
            
        Returns:
            Dictionary of headers
        """
        headers = {}
        inject_context(headers, context=context)
        return headers
    
    @staticmethod
    def from_headers(headers: Dict[str, str]) -> Context:
        """Extract context from HTTP headers
        
        Args:
            headers: HTTP headers dictionary
            
        Returns:
            Extracted context
        """
        return extract_context(headers)
    
    @staticmethod
    def to_message_attributes(context: Optional[Context] = None) -> Dict[str, Any]:
        """Convert context to message attributes (for queues)
        
        Args:
            context: Optional context (uses current if not provided)
            
        Returns:
            Dictionary of message attributes
        """
        attributes = {}
        inject_context(attributes, context=context)
        return attributes
    
    @staticmethod
    def from_message_attributes(attributes: Dict[str, Any]) -> Context:
        """Extract context from message attributes
        
        Args:
            attributes: Message attributes dictionary
            
        Returns:
            Extracted context
        """
        return extract_context(attributes)