"""Pydantic models for API requests and responses"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import json
import logging

logger = logging.getLogger(__name__)


class NuanceLevel(str, Enum):
    """Nuance level categories"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    NATIVE = "native"


class FlashcardDifficulty(str, Enum):
    """Flashcard difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class PartOfSpeech(str, Enum):
    """Part of speech categories"""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    INTERJECTION = "interjection"
    PHRASE = "phrase"
    PARTICLE = "particle"
    UNKNOWN = "unknown"


class ExportFormat(str, Enum):
    """Supported export formats"""
    TSV = "tsv"
    ANKI = "anki"
    JSON = "json"
    PDF = "pdf"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"


class ValidationStatus(str, Enum):
    """Flashcard validation status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_REVIEW = "in_review"


class ProcessingStage(str, Enum):
    """Processing stage for flashcards"""
    INGRESS = "ingress"
    STAGE1 = "stage1"
    STAGE2 = "stage2"
    VALIDATION = "validation"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"


class VocabularyItem(BaseModel):
    """Input vocabulary item from CSV"""
    position: int = Field(gt=0)
    term: str = Field(min_length=1)
    type: str = Field(default="unknown")
    nuance_level: Optional[NuanceLevel] = None
    
    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, v):
        if v is None or v == "":
            return PartOfSpeech.UNKNOWN.value
        # Map common variations
        type_mapping = {
            'n': PartOfSpeech.NOUN.value,
            'v': PartOfSpeech.VERB.value,
            'adj': PartOfSpeech.ADJECTIVE.value,
            'adv': PartOfSpeech.ADVERB.value,
            'int': PartOfSpeech.INTERJECTION.value,
            'phr': PartOfSpeech.PHRASE.value,
            'part': PartOfSpeech.PARTICLE.value
        }
        return type_mapping.get(v.lower(), v.lower())
    
    def cache_key(self) -> str:
        """Generate cache key for this vocabulary item"""
        return f"{self.term}:{self.type}:{self.position}"


class Homonym(BaseModel):
    """Homonym information for Korean words"""
    hanja: str
    reading: str
    meaning: str
    differentiator: str


class Comparison(BaseModel):
    """Comparison with similar terms"""
    vs: str = Field(description="Term being compared against")
    nuance: str = Field(description="Nuance difference explanation")


class Stage1Response(BaseModel):
    """Response from Stage 1: Semantic Analysis"""
    term_number: int
    term: str
    ipa: str
    pos: str
    primary_meaning: str
    other_meanings: Optional[str] = ""
    metaphor: str
    metaphor_noun: str
    metaphor_action: str
    suggested_location: str
    anchor_object: str
    anchor_sensory: str
    explanation: str
    usage_context: Optional[str] = None
    comparison: Comparison
    homonyms: Optional[List[Homonym]] = Field(default_factory=list)
    korean_keywords: List[str]
    
    @field_validator('homonyms', mode='before')
    @classmethod
    def validate_homonyms(cls, v):
        return v if v is not None else []
    
    @field_validator('pos')
    @classmethod
    def validate_pos(cls, v):
        # Ensure POS is valid
        valid_pos = [e.value for e in PartOfSpeech]
        if v.lower() not in valid_pos:
            return PartOfSpeech.UNKNOWN.value
        return v.lower()


class Stage1Request(BaseModel):
    """Request format for Stage 1 API"""
    model: str = "@preset/nuance-creator"
    messages: List[Dict[str, str]]
    
    @classmethod
    def from_vocabulary_item(cls, item: VocabularyItem) -> 'Stage1Request':
        """Create Stage 1 request from vocabulary item"""
        return cls(
            messages=[{
                "role": "user",
                "content": json.dumps({
                    "position": item.position,
                    "term": item.term,
                    "type": item.type
                }, ensure_ascii=False)
            }]
        )


class Stage2Request(BaseModel):
    """Request format for Stage 2 API"""
    model: str = "@preset/nuance-flashcard-generator"
    messages: List[Dict[str, str]]
    
    @classmethod
    def from_stage1_result(cls, item: VocabularyItem, stage1_result: Stage1Response) -> 'Stage2Request':
        """Create Stage 2 request from Stage 1 result"""
        return cls(
            messages=[{
                "role": "user",
                "content": json.dumps({
                    "position": item.position,
                    "term": item.term,
                    "stage1_result": stage1_result.model_dump()
                }, ensure_ascii=False)
            }]
        )


class FlashcardRow(BaseModel):
    """Single row in TSV output"""
    position: int = Field(gt=0)
    term: str = Field(min_length=1)  # With IPA
    term_number: int = Field(gt=0)
    tab_name: str
    primer: str
    front: str
    back: str
    tags: str
    honorific_level: str = ""
    
    def to_tsv_row(self) -> str:
        """Convert to TSV format"""
        fields = [
            str(self.position),
            self.term.replace('\t', '\\t').replace('\n', '\\n'),
            str(self.term_number),
            self.tab_name.replace('\t', '\\t').replace('\n', '\\n'),
            self.primer.replace('\t', '\\t').replace('\n', '\\n'),
            self.front.replace('\t', '\\t').replace('\n', '\\n'),
            self.back.replace('\t', '\\t').replace('\n', '\\n'),
            self.tags.replace('\t', '\\t').replace('\n', '\\n'),
            self.honorific_level.replace('\t', '\\t').replace('\n', '\\n')
        ]
        return "\t".join(fields)


class Stage2Response(BaseModel):
    """Response from Stage 2: Flashcard Generation"""
    rows: List[FlashcardRow]
    
    @classmethod
    def from_tsv_content(cls, content: str) -> 'Stage2Response':
        """Parse TSV content into structured response"""
        lines = content.strip().split('\n')
        
        # Skip header if present
        if lines and lines[0].startswith('position'):
            lines = lines[1:]
        
        rows = []
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split('\t')
            if len(parts) >= 8:
                try:
                    # Skip if this is another header line
                    if parts[0] == 'position':
                        continue
                        
                    row = FlashcardRow(
                        position=int(parts[0]),
                        term=parts[1],
                        term_number=int(parts[2]),
                        tab_name=parts[3],
                        primer=parts[4],
                        front=parts[5],
                        back=parts[6],
                        tags=parts[7],
                        honorific_level=parts[8] if len(parts) > 8 else ""
                    )
                    rows.append(row)
                except ValueError as e:
                    # Log the error but continue processing
                    logger.warning(f"Skipping invalid TSV line: {e}")
                    continue
        
        # If no valid rows were parsed, create a minimal response
        if not rows:
            raise ValueError(f"No valid data rows found in TSV content: {content}")
        
        return cls(rows=rows)
    
    def to_tsv(self) -> str:
        """Convert to complete TSV format with header"""
        header = "position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level"
        rows = [row.to_tsv_row() for row in self.rows]
        return header + "\n" + "\n".join(rows)


class ApiUsage(BaseModel):
    """API usage information from response"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
    @property
    def estimated_cost(self) -> float:
        """Calculate estimated cost (Claude Sonnet 4: $15/1M tokens)"""
        return (self.total_tokens / 1_000_000) * 15.0


class ApiResponse(BaseModel):
    """Complete API response wrapper"""
    id: str
    model: str
    object: str
    created: int
    choices: List[Dict[str, Any]]
    usage: ApiUsage
    
    def get_content(self) -> str:
        """Extract content from first choice"""
        if self.choices and len(self.choices) > 0:
            return self.choices[0]["message"]["content"]
        return ""
    
    @property
    def finish_reason(self) -> Optional[str]:
        """Get finish reason"""
        if self.choices and len(self.choices) > 0:
            return self.choices[0].get("finish_reason")
        return None


class RateLimitInfo(BaseModel):
    """Rate limit information from headers"""
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional['RateLimitInfo']:
        """Parse rate limit info from response headers"""
        try:
            limit = int(headers.get('X-RateLimit-Limit', '60'))
            remaining = int(headers.get('X-RateLimit-Remaining', '60'))
            reset_timestamp = int(headers.get('X-RateLimit-Reset', '0'))
            
            if reset_timestamp:
                reset_at = datetime.fromtimestamp(reset_timestamp)
            else:
                reset_at = datetime.now()
            
            retry_after = headers.get('Retry-After')
            if retry_after:
                retry_after = int(retry_after)
            
            return cls(
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=retry_after
            )
        except (ValueError, TypeError):
            return None


class BatchProgress(BaseModel):
    """Progress tracking for batch processing"""
    batch_id: str
    total_items: int
    completed_items: int
    failed_items: int
    current_stage: str = "stage1"
    started_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def items_per_second(self) -> float:
        """Calculate processing rate"""
        elapsed = (self.updated_at - self.started_at).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.completed_items / elapsed
    
    def estimate_completion(self) -> Optional[datetime]:
        """Estimate completion time"""
        if self.items_per_second == 0:
            return None
        
        remaining = self.total_items - self.completed_items
        seconds_remaining = remaining / self.items_per_second
        
        return datetime.now() + timedelta(seconds=seconds_remaining)


class CacheStats(BaseModel):
    """Cache statistics"""
    stage1_hits: int = 0
    stage1_misses: int = 0
    stage2_hits: int = 0
    stage2_misses: int = 0
    total_tokens_saved: int = 0
    estimated_cost_saved: float = 0.0
    
    @property
    def stage1_hit_rate(self) -> float:
        """Calculate Stage 1 cache hit rate"""
        total = self.stage1_hits + self.stage1_misses
        if total == 0:
            return 0.0
        return (self.stage1_hits / total) * 100
    
    @property
    def stage2_hit_rate(self) -> float:
        """Calculate Stage 2 cache hit rate"""
        total = self.stage2_hits + self.stage2_misses
        if total == 0:
            return 0.0
        return (self.stage2_hits / total) * 100
    
    @property
    def overall_hit_rate(self) -> float:
        """Calculate overall cache hit rate"""
        total_hits = self.stage1_hits + self.stage2_hits
        total_requests = total_hits + self.stage1_misses + self.stage2_misses
        if total_requests == 0:
            return 0.0
        return (total_hits / total_requests) * 100


class Tag(BaseModel):
    """Tag model for flashcards"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    usage_count: int = 0


class Deck(BaseModel):
    """Deck model for organizing flashcards"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    card_count: int = 0
    parent_deck_id: Optional[str] = None


class Flashcard(BaseModel):
    """Complete flashcard model"""
    id: Optional[str] = None
    korean: str
    english: str
    romanization: Optional[str] = None
    explanation: Optional[str] = None
    deck_id: Optional[str] = None
    tags: List[Tag] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    validation_status: Optional[ValidationStatus] = ValidationStatus.PENDING
    processing_stage: Optional[ProcessingStage] = ProcessingStage.INGRESS
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional fields from FlashcardRow
    position: Optional[int] = None
    term_number: Optional[int] = None
    tab_name: Optional[str] = None
    primer: Optional[str] = None
    honorific_level: Optional[str] = None


class Stage1Insight(BaseModel):
    """Insights from Stage 1 analysis"""
    term: str
    insight_type: str
    content: str
    confidence: float = Field(ge=0.0, le=1.0)


class FlashcardFront(BaseModel):
    """Front side of a flashcard"""
    korean: str
    romanization: str
    audio_url: Optional[str] = None


class FlashcardBack(BaseModel):
    """Back side of a flashcard"""
    english: str
    explanation: str
    example_sentence: Optional[str] = None
    literal_translation: Optional[str] = None


class FlashcardExample(BaseModel):
    """Example usage of a flashcard"""
    korean: str
    english: str
    context: Optional[str] = None


class BatchRequest(BaseModel):
    """Request for batch processing"""
    batch_id: str
    items: List[VocabularyItem]
    stage: str = "stage1"


class BatchStatus(str, Enum):
    """Batch processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class BatchResult(BaseModel):
    """Result of batch processing"""
    batch_id: str
    status: BatchStatus
    total_items: int
    processed_items: int
    failed_items: int
    results: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ProcessingMetrics(BaseModel):
    """Metrics collected during processing"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    total_tokens_used: int = 0
    cache_hit_rate: float = 0.0


class ErrorInfo(BaseModel):
    """Information about an error"""
    error_type: str
    error_message: str
    timestamp: datetime
    retry_after: Optional[int] = None


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    value: Optional[Any] = None