"""Test data factories for the Korean Flashcard Pipeline.

This module provides factory classes for generating test data
using the factory pattern. It creates realistic test objects
for all major data models in the system.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from src.python.flashcard_pipeline.models import (
    VocabularyItem,
    NuanceLevel,
    FlashcardDifficulty,
    Stage1Request,
    Stage1Response,
    Stage1Insight,
    Stage2Request,
    Stage2Response,
    Flashcard,
    FlashcardFront,
    FlashcardBack,
    FlashcardExample,
    BatchRequest,
    BatchResult,
    BatchStatus,
    ProcessingMetrics,
    ErrorInfo,
    RateLimitInfo,
    ValidationError,
)


class BaseFactory:
    """Base factory class with common utilities."""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_korean_word() -> str:
        """Generate a random Korean word."""
        korean_chars = ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하']
        return ''.join(random.choices(korean_chars, k=random.randint(2, 4)))
    
    @staticmethod
    def random_sentence(word_count: int = 10) -> str:
        """Generate a random sentence."""
        words = [BaseFactory.random_string(random.randint(3, 8)) for _ in range(word_count)]
        return ' '.join(words).capitalize() + '.'
    
    @staticmethod
    def random_korean_sentence() -> str:
        """Generate a random Korean sentence."""
        words = [BaseFactory.random_korean_word() for _ in range(random.randint(3, 7))]
        return ' '.join(words) + '.'


class VocabularyFactory(BaseFactory):
    """Factory for creating VocabularyItem instances."""
    
    @classmethod
    def create(
        cls,
        korean: Optional[str] = None,
        english: Optional[str] = None,
        nuance_level: Optional[NuanceLevel] = None,
        created_at: Optional[datetime] = None,
        **kwargs
    ) -> VocabularyItem:
        """Create a VocabularyItem with optional overrides."""
        return VocabularyItem(
            korean=korean or cls.random_korean_word(),
            english=english or cls.random_string(8),
            nuance_level=nuance_level or random.choice(list(NuanceLevel)),
            created_at=created_at or datetime.utcnow(),
            **kwargs
        )
    
    @classmethod
    def create_batch(cls, count: int = 10) -> List[VocabularyItem]:
        """Create a batch of VocabularyItems."""
        return [cls.create() for _ in range(count)]
    
    @classmethod
    def create_with_nuance(cls, nuance_level: NuanceLevel) -> VocabularyItem:
        """Create a VocabularyItem with specific nuance level."""
        return cls.create(nuance_level=nuance_level)


class Stage1ResponseFactory(BaseFactory):
    """Factory for creating Stage1Response instances."""
    
    @classmethod
    def create_insight(
        cls,
        insight_type: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[List[str]] = None,
        importance_score: Optional[float] = None,
    ) -> Stage1Insight:
        """Create a Stage1Insight."""
        return Stage1Insight(
            insight_type=insight_type or random.choice(['usage', 'formality', 'context', 'connotation']),
            description=description or cls.random_sentence(15),
            examples=examples or [cls.random_korean_sentence() for _ in range(2)],
            importance_score=importance_score or round(random.uniform(0.5, 1.0), 2)
        )
    
    @classmethod
    def create(
        cls,
        korean_word: Optional[str] = None,
        english_translation: Optional[str] = None,
        primary_insight: Optional[str] = None,
        nuances: Optional[List[Stage1Insight]] = None,
        **kwargs
    ) -> Stage1Response:
        """Create a Stage1Response with optional overrides."""
        return Stage1Response(
            korean_word=korean_word or cls.random_korean_word(),
            english_translation=english_translation or cls.random_string(10),
            primary_insight=primary_insight or cls.random_sentence(20),
            nuances=nuances or [cls.create_insight() for _ in range(random.randint(2, 4))],
            **kwargs
        )
    
    @classmethod
    def create_detailed(cls) -> Stage1Response:
        """Create a detailed Stage1Response with rich nuances."""
        return cls.create(
            nuances=[
                cls.create_insight('usage', 'Formal business context', importance_score=0.9),
                cls.create_insight('formality', 'High formality level', importance_score=0.8),
                cls.create_insight('context', 'Professional settings', importance_score=0.85),
                cls.create_insight('connotation', 'Respectful tone', importance_score=0.7),
            ]
        )


class FlashcardFactory(BaseFactory):
    """Factory for creating Flashcard instances."""
    
    @classmethod
    def create_example(
        cls,
        korean: Optional[str] = None,
        english: Optional[str] = None,
        highlight_pattern: Optional[str] = None,
    ) -> FlashcardExample:
        """Create a FlashcardExample."""
        return FlashcardExample(
            korean=korean or cls.random_korean_sentence(),
            english=english or cls.random_sentence(),
            highlight_pattern=highlight_pattern or cls.random_korean_word()
        )
    
    @classmethod
    def create_front(
        cls,
        main_word: Optional[str] = None,
        context_hint: Optional[str] = None,
        visual_cue: Optional[str] = None,
    ) -> FlashcardFront:
        """Create a FlashcardFront."""
        return FlashcardFront(
            main_word=main_word or cls.random_korean_word(),
            context_hint=context_hint or cls.random_sentence(8),
            visual_cue=visual_cue or f"[{cls.random_string(5)}]"
        )
    
    @classmethod
    def create_back(
        cls,
        primary_meaning: Optional[str] = None,
        nuance_explanation: Optional[str] = None,
        usage_notes: Optional[List[str]] = None,
        example_sentences: Optional[List[FlashcardExample]] = None,
        memory_tip: Optional[str] = None,
    ) -> FlashcardBack:
        """Create a FlashcardBack."""
        return FlashcardBack(
            primary_meaning=primary_meaning or cls.random_string(10),
            nuance_explanation=nuance_explanation or cls.random_sentence(15),
            usage_notes=usage_notes or [cls.random_sentence(10) for _ in range(2)],
            example_sentences=example_sentences or [cls.create_example() for _ in range(2)],
            memory_tip=memory_tip or f"Remember: {cls.random_sentence(8)}"
        )
    
    @classmethod
    def create(
        cls,
        id: Optional[str] = None,
        vocabulary_item_id: Optional[int] = None,
        difficulty: Optional[FlashcardDifficulty] = None,
        card_type: Optional[str] = None,
        front: Optional[FlashcardFront] = None,
        back: Optional[FlashcardBack] = None,
        **kwargs
    ) -> Flashcard:
        """Create a Flashcard with optional overrides."""
        return Flashcard(
            id=id or str(uuid4()),
            vocabulary_item_id=vocabulary_item_id or random.randint(1, 1000),
            difficulty=difficulty or random.choice(list(FlashcardDifficulty)),
            card_type=card_type or random.choice(['basic', 'context', 'usage']),
            front=front or cls.create_front(),
            back=back or cls.create_back(),
            **kwargs
        )
    
    @classmethod
    def create_set(cls, vocabulary_item_id: int, count: int = 3) -> List[Flashcard]:
        """Create a set of flashcards for a vocabulary item."""
        difficulties = [FlashcardDifficulty.BEGINNER, FlashcardDifficulty.INTERMEDIATE, FlashcardDifficulty.ADVANCED]
        return [
            cls.create(
                vocabulary_item_id=vocabulary_item_id,
                difficulty=difficulties[i % len(difficulties)]
            )
            for i in range(count)
        ]


class Stage2ResponseFactory(BaseFactory):
    """Factory for creating Stage2Response instances."""
    
    @classmethod
    def create(
        cls,
        vocabulary_item_id: Optional[int] = None,
        total_cards_generated: Optional[int] = None,
        flashcards: Optional[List[Flashcard]] = None,
        generation_notes: Optional[str] = None,
        **kwargs
    ) -> Stage2Response:
        """Create a Stage2Response with optional overrides."""
        vocab_id = vocabulary_item_id or random.randint(1, 1000)
        cards = flashcards or FlashcardFactory.create_set(vocab_id)
        
        return Stage2Response(
            vocabulary_item_id=vocab_id,
            total_cards_generated=total_cards_generated or len(cards),
            flashcards=cards,
            generation_notes=generation_notes or "Generated successfully",
            **kwargs
        )


class MetricDataFactory(BaseFactory):
    """Factory for creating monitoring and metrics data."""
    
    @classmethod
    def create_processing_metrics(
        cls,
        total_requests: Optional[int] = None,
        successful_requests: Optional[int] = None,
        failed_requests: Optional[int] = None,
        avg_response_time_ms: Optional[float] = None,
        total_tokens_used: Optional[int] = None,
        cache_hit_rate: Optional[float] = None,
    ) -> ProcessingMetrics:
        """Create ProcessingMetrics."""
        total = total_requests or random.randint(100, 1000)
        successful = successful_requests or int(total * 0.95)
        
        return ProcessingMetrics(
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed_requests or (total - successful),
            avg_response_time_ms=avg_response_time_ms or round(random.uniform(100, 500), 2),
            total_tokens_used=total_tokens_used or random.randint(10000, 100000),
            cache_hit_rate=cache_hit_rate or round(random.uniform(0.3, 0.8), 2)
        )
    
    @classmethod
    def create_rate_limit_info(
        cls,
        requests_remaining: Optional[int] = None,
        requests_limit: Optional[int] = None,
        reset_at: Optional[datetime] = None,
    ) -> RateLimitInfo:
        """Create RateLimitInfo."""
        limit = requests_limit or 1000
        return RateLimitInfo(
            remaining=requests_remaining or random.randint(0, limit),
            limit=limit,
            reset_at=reset_at or (datetime.utcnow() + timedelta(hours=1))
        )
    
    @classmethod
    def create_error_info(
        cls,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        retry_after: Optional[int] = None,
    ) -> ErrorInfo:
        """Create ErrorInfo."""
        return ErrorInfo(
            error_type=error_type or random.choice(['RateLimitError', 'APIError', 'ValidationError']),
            error_message=error_message or cls.random_sentence(10),
            timestamp=timestamp or datetime.utcnow(),
            retry_after=retry_after or random.randint(30, 300)
        )


class BatchFactory(BaseFactory):
    """Factory for creating batch processing objects."""
    
    @classmethod
    def create_batch_request(
        cls,
        batch_id: Optional[str] = None,
        items: Optional[List[VocabularyItem]] = None,
        stage: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> BatchRequest:
        """Create a BatchRequest."""
        return BatchRequest(
            batch_id=batch_id or str(uuid4()),
            items=items or VocabularyFactory.create_batch(5),
            stage=stage or random.choice(['stage1', 'stage2']),
            priority=priority or random.randint(1, 10)
        )
    
    @classmethod
    def create_batch_result(
        cls,
        batch_id: Optional[str] = None,
        status: Optional[BatchStatus] = None,
        total_items: Optional[int] = None,
        processed_items: Optional[int] = None,
        failed_items: Optional[int] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        errors: Optional[List[ErrorInfo]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> BatchResult:
        """Create a BatchResult."""
        total = total_items or 10
        processed = processed_items or total - 1
        
        return BatchResult(
            batch_id=batch_id or str(uuid4()),
            status=status or BatchStatus.COMPLETED,
            total_items=total,
            processed_items=processed,
            failed_items=failed_items or (total - processed),
            results=results or [],
            errors=errors or [],
            started_at=started_at or datetime.utcnow(),
            completed_at=completed_at or datetime.utcnow()
        )


class TestScenarioFactory:
    """Factory for creating complete test scenarios."""
    
    @classmethod
    def create_full_pipeline_scenario(cls) -> Dict[str, Any]:
        """Create a complete pipeline test scenario."""
        # Create vocabulary items
        vocab_items = VocabularyFactory.create_batch(5)
        
        # Create Stage 1 responses
        stage1_responses = [
            Stage1ResponseFactory.create(
                korean_word=item.korean,
                english_translation=item.english
            )
            for item in vocab_items
        ]
        
        # Create Stage 2 responses with flashcards
        stage2_responses = [
            Stage2ResponseFactory.create(vocabulary_item_id=i)
            for i in range(len(vocab_items))
        ]
        
        # Create metrics
        metrics = MetricDataFactory.create_processing_metrics()
        
        return {
            'vocabulary_items': vocab_items,
            'stage1_responses': stage1_responses,
            'stage2_responses': stage2_responses,
            'metrics': metrics,
            'batch_id': str(uuid4()),
            'timestamp': datetime.utcnow()
        }
    
    @classmethod
    def create_error_scenario(cls) -> Dict[str, Any]:
        """Create an error scenario for testing."""
        vocab_items = VocabularyFactory.create_batch(3)
        errors = [
            MetricDataFactory.create_error_info()
            for _ in range(2)
        ]
        
        return {
            'vocabulary_items': vocab_items,
            'errors': errors,
            'batch_id': str(uuid4()),
            'timestamp': datetime.utcnow()
        }
    
    @classmethod
    def create_rate_limit_scenario(cls) -> Dict[str, Any]:
        """Create a rate limit scenario."""
        return {
            'rate_limit_info': MetricDataFactory.create_rate_limit_info(
                requests_remaining=0,
                reset_at=datetime.utcnow() + timedelta(minutes=30)
            ),
            'error': MetricDataFactory.create_error_info(
                error_type='RateLimitError',
                error_message='Rate limit exceeded',
                retry_after=1800
            )
        }