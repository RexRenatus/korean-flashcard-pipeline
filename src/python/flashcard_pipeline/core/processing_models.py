"""Processing-related models shared across the pipeline"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .models import Stage1Response, Stage2Response


@dataclass
class ProcessingResult:
    """Result from processing a single vocabulary item"""
    term: str
    pos: str
    term_number: int
    stage1_output: Optional[Stage1Response] = None
    stage2_output: Optional[Stage2Response] = None
    success: bool = False
    error: Optional[str] = None
    cached_stage1: bool = False
    cached_stage2: bool = False


@dataclass
class BatchProcessingResult:
    """Result from batch processing"""
    results: List[ProcessingResult]
    total_processed: int
    total_failed: int
    processing_time: float
    metadata: Dict[str, Any]