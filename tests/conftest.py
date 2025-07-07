"""Pytest configuration and shared fixtures"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

from flashcard_pipeline.models import VocabularyItem, Stage1Response, Stage2Response, FlashcardRow, Comparison
from flashcard_pipeline.cli.config import Config


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_env(monkeypatch) -> Dict[str, str]:
    """Mock environment variables"""
    env_vars = {
        "OPENROUTER_API_KEY": "test-api-key-12345",
        "FLASHCARD_LOG_LEVEL": "DEBUG",
        "FLASHCARD_CACHE_DIR": "/tmp/test_cache"
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def sample_vocabulary_items() -> list[VocabularyItem]:
    """Sample vocabulary items for testing"""
    return [
        VocabularyItem(position=1, term="안녕하세요", type="greeting"),
        VocabularyItem(position=2, term="감사합니다", type="phrase"),
        VocabularyItem(position=3, term="사랑", type="noun"),
        VocabularyItem(position=4, term="하다", type="verb"),
        VocabularyItem(position=5, term="예쁘다", type="adjective")
    ]


@pytest.fixture
def sample_stage1_response() -> Stage1Response:
    """Sample Stage 1 API response"""
    return Stage1Response(
        romanization="annyeonghaseyo",
        definitions=["hello", "good day"],
        part_of_speech="greeting",
        difficulty_level="beginner",
        formality_level="formal",
        additional_info={
            "literal": "Are you at peace?",
            "usage": "Standard polite greeting"
        },
        example_sentence="안녕하세요, 만나서 반갑습니다.",
        homonyms=[],
        comparisons=[
            Comparison(
                term="안녕",
                romanization="annyeong",
                relationship="informal_variant",
                explanation="Casual version used with friends"
            )
        ]
    )


@pytest.fixture
def sample_flashcard_rows() -> list[FlashcardRow]:
    """Sample flashcard rows"""
    return [
        FlashcardRow(
            position=1,
            term="안녕하세요",
            term_number=1,
            tab_name="Scene",
            primer="You enter your memory room...",
            front="What greeting do you use?",
            back="안녕하세요 - formal hello",
            tags="greeting,formal,beginner",
            honorific_level="formal"
        ),
        FlashcardRow(
            position=1,
            term="안녕하세요",
            term_number=1,
            tab_name="Usage",
            primer="You enter your memory room...",
            front="When do you use this greeting?",
            back="Use with strangers, elders, or in formal situations",
            tags="greeting,usage,formal",
            honorific_level="formal"
        )
    ]


@pytest.fixture
def sample_config(temp_dir: Path) -> Config:
    """Sample configuration for testing"""
    config_data = {
        "api": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "claude-3-5-sonnet-20241022",
            "timeout": 30,
            "max_retries": 3
        },
        "processing": {
            "rate_limit_rpm": 600,
            "max_concurrent": 10,
            "batch_size": 100
        },
        "cache": {
            "directory": str(temp_dir / "cache"),
            "ttl_hours": 0,  # Permanent cache
            "max_size_mb": 100
        },
        "output": {
            "directory": str(temp_dir / "output"),
            "default_format": "tsv"
        },
        "database": {
            "path": str(temp_dir / "test.db")
        }
    }
    
    config = Config(**config_data)
    return config


@pytest.fixture
def mock_api_responses() -> Dict[str, Any]:
    """Mock API responses for testing"""
    return {
        "stage1_success": {
            "id": "test-id-1",
            "model": "claude-3-5-sonnet",
            "object": "chat.completion",
            "created": 1234567890,
            "choices": [{
                "message": {
                    "content": '{"romanization":"annyeonghaseyo","definitions":["hello"],"part_of_speech":"greeting","difficulty_level":"beginner","formality_level":"formal","additional_info":{},"example_sentence":"안녕하세요.","homonyms":[],"comparisons":[]}'
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        },
        "stage2_success": {
            "id": "test-id-2",
            "model": "claude-3-5-sonnet",
            "object": "chat.completion",
            "created": 1234567891,
            "choices": [{
                "message": {
                    "content": 'position\tterm\tterm_number\ttab_name\tprimer\tfront\tback\ttags\thonorific_level\n1\t안녕하세요\t1\tScene\tYou enter...\tWhat greeting?\t안녕하세요 - hello\tgreeting,formal\tformal'
                }
            }],
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            }
        }
    }