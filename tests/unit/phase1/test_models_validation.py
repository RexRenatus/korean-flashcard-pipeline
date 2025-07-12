"""Phase 1: Model Validation Tests

Tests for VocabularyItem, Stage1Response, Stage2Response, and FlashcardRow models
to ensure they correctly parse and validate various input formats.
"""

import pytest
from pydantic import ValidationError
import json
from datetime import datetime

from flashcard_pipeline.models import (
    VocabularyItem,
    Stage1Response,
    Stage2Response,
    FlashcardRow,
    Homonym,
    Comparison,
    PartOfSpeech,
    ApiUsage,
    ApiResponse,
    BatchProgress
)


class TestVocabularyItemParsing:
    """Test VocabularyItem handles various CSV formats"""
    
    def test_standard_format(self):
        """Test parsing standard format (position, term, type)"""
        item = VocabularyItem(
            position=1,
            term="안녕하세요",
            type="interjection"
        )
        assert item.position == 1
        assert item.term == "안녕하세요"
        assert item.type == "interjection"
    
    def test_type_abbreviation_mapping(self):
        """Test type abbreviation mappings"""
        # Test abbreviations
        mappings = [
            ("n", "noun"),
            ("v", "verb"),
            ("adj", "adjective"),
            ("adv", "adverb"),
            ("int", "interjection"),
            ("phr", "phrase"),
            ("part", "particle")
        ]
        
        for abbr, expected in mappings:
            item = VocabularyItem(position=1, term="테스트", type=abbr)
            assert item.type == expected
    
    def test_missing_type_field(self):
        """Test handling missing type field with default"""
        item = VocabularyItem(
            position=10,
            term="한국어"
        )
        assert item.position == 10
        assert item.term == "한국어"
        assert item.type == "unknown"  # Should default to 'unknown'
    
    def test_invalid_position_type(self):
        """Test validation error for invalid position type"""
        with pytest.raises(ValidationError) as exc_info:
            VocabularyItem(
                position="not_a_number",  # Invalid type
                term="테스트"
            )
        assert "position" in str(exc_info.value)
    
    def test_empty_term(self):
        """Test validation for empty term"""
        with pytest.raises(ValidationError) as exc_info:
            VocabularyItem(
                position=1,
                term=""  # Empty term should fail
            )
        assert "string" in str(exc_info.value).lower()


class TestStage1ResponseStructure:
    """Test Stage1Response model validation"""
    
    def test_required_fields_present(self):
        """Test all required fields must be present"""
        response = Stage1Response(
            term_number=1,
            term="안녕",
            ipa="[annyeong]",
            pos="interjection",
            primary_meaning="hello",
            metaphor="A warm wave of greeting",
            metaphor_noun="wave",
            metaphor_action="greeting",
            suggested_location="entrance",
            anchor_object="door",
            anchor_sensory="warmth",
            explanation="Casual greeting",
            comparison=Comparison(vs="안녕하세요", nuance="More formal"),
            korean_keywords=["인사", "친구"]
        )
        
        assert response.term_number == 1
        assert response.term == "안녕"
        assert response.ipa == "[annyeong]"
        assert response.pos == "interjection"
    
    def test_optional_fields_handled(self):
        """Test optional fields have proper defaults"""
        response = Stage1Response(
            term_number=1,
            term="테스트",
            ipa="[test]",
            pos="noun",
            primary_meaning="test",
            metaphor="A challenge",
            metaphor_noun="challenge",
            metaphor_action="testing",
            suggested_location="classroom",
            anchor_object="paper",
            anchor_sensory="stress",
            explanation="An examination",
            comparison=Comparison(vs="시험", nuance="Less formal"),
            korean_keywords=["시험"]
        )
        assert response.other_meanings == ""
        assert response.usage_context is None
        assert response.homonyms == []
    
    def test_nested_comparison_structure(self):
        """Test nested Comparison objects are validated"""
        comparison = Comparison(
            vs="안녕하세요",
            nuance="More formal greeting"
        )
        
        response = Stage1Response(
            term_number=1,
            term="안녕",
            ipa="[annyeong]",
            pos="interjection",
            primary_meaning="hello",
            metaphor="A wave",
            metaphor_noun="wave",
            metaphor_action="waving",
            suggested_location="door",
            anchor_object="hand",
            anchor_sensory="warmth",
            explanation="Casual hello",
            comparison=comparison,
            korean_keywords=["인사"]
        )
        
        assert response.comparison.vs == "안녕하세요"
        assert response.comparison.nuance == "More formal greeting"
    
    def test_pos_validation(self):
        """Test part of speech validation"""
        # Valid POS
        response = Stage1Response(
            term_number=1,
            term="테스트",
            ipa="[test]",
            pos="noun",
            primary_meaning="test",
            metaphor="Trial",
            metaphor_noun="trial",
            metaphor_action="testing",
            suggested_location="room",
            anchor_object="paper",
            anchor_sensory="anxiety",
            explanation="A test",
            comparison=Comparison(vs="시험", nuance="Similar"),
            korean_keywords=["시험"]
        )
        assert response.pos == "noun"
        
        # Invalid POS should be converted to 'unknown'
        response = Stage1Response(
            term_number=1,
            term="테스트",
            ipa="[test]",
            pos="invalid_pos",
            primary_meaning="test",
            metaphor="Trial",
            metaphor_noun="trial",
            metaphor_action="testing",
            suggested_location="room",
            anchor_object="paper",
            anchor_sensory="anxiety",
            explanation="A test",
            comparison=Comparison(vs="시험", nuance="Similar"),
            korean_keywords=["시험"]
        )
        assert response.pos == "unknown"
    
    def test_homonyms_null_handling(self):
        """Test homonyms field accepts null/None values"""
        response = Stage1Response(
            term_number=1,
            term="테스트",
            ipa="[test]",
            pos="noun",
            primary_meaning="test",
            metaphor="Trial",
            metaphor_noun="trial",
            metaphor_action="testing",
            suggested_location="room",
            anchor_object="paper",
            anchor_sensory="anxiety",
            explanation="A test",
            comparison=Comparison(vs="시험", nuance="Similar"),
            korean_keywords=["시험"],
            homonyms=None  # Should be converted to empty list
        )
        assert response.homonyms == []


class TestFlashcardRowGeneration:
    """Test FlashcardRow creation and validation"""
    
    def test_all_fields_populated(self):
        """Test flashcard with all fields"""
        row = FlashcardRow(
            position=1,
            term="한국 [hanguk]",
            term_number=1,
            tab_name="Scene",
            primer="Memory room entry...",
            front="What country?",
            back="Korea - 한국",
            tags="country,noun",
            honorific_level="neutral"
        )
        
        assert row.position == 1
        assert row.term == "한국 [hanguk]"
        assert row.term_number == 1
        assert row.tab_name == "Scene"
        assert "country" in row.tags
    
    def test_defaults_applied_correctly(self):
        """Test default values are applied"""
        row = FlashcardRow(
            position=5,
            term="테스트",
            term_number=1,
            tab_name="Test",
            primer="",
            front="Q",
            back="A",
            tags=""
            # honorific_level should default to empty string
        )
        assert row.honorific_level == ""
        assert row.tags == ""
    
    def test_tsv_row_generation(self):
        """Test TSV row output format"""
        row = FlashcardRow(
            position=1,
            term="안녕 [annyeong]",
            term_number=1,
            tab_name="Scene",
            primer="Enter room",
            front="Greeting?",
            back="Hello",
            tags="greeting",
            honorific_level="casual"
        )
        
        tsv = row.to_tsv_row()
        parts = tsv.split('\t')
        
        assert len(parts) == 9
        assert parts[0] == "1"
        assert parts[1] == "안녕 [annyeong]"
        assert parts[2] == "1"
        assert parts[3] == "Scene"
        assert parts[8] == "casual"
    
    def test_validation_rules_enforced(self):
        """Test validation rules for flashcard fields"""
        # Position must be positive
        with pytest.raises(ValidationError):
            FlashcardRow(
                position=-1,  # Invalid
                term="test",
                term_number=1,
                tab_name="Test",
                primer="",
                front="Q",
                back="A",
                tags=""
            )
        
        # Term cannot be empty
        with pytest.raises(ValidationError):
            FlashcardRow(
                position=1,
                term="",  # Invalid
                term_number=1,
                tab_name="Test",
                primer="",
                front="Q",
                back="A",
                tags=""
            )


class TestStage2ResponseParsing:
    """Test Stage2Response TSV parsing"""
    
    def test_parse_tsv_without_header(self):
        """Test parsing TSV content without header"""
        tsv_content = """1	안녕 [annyeong]	1	Scene	Enter room	Greeting?	Hello	greeting	casual
1	안녕 [annyeong]	2	Usage	Enter room	When to use?	With friends	usage	casual"""
        
        response = Stage2Response.from_tsv_content(tsv_content)
        assert len(response.rows) == 2
        assert response.rows[0].term == "안녕 [annyeong]"
        assert response.rows[0].tab_name == "Scene"
        assert response.rows[1].tab_name == "Usage"
    
    def test_parse_tsv_with_header(self):
        """Test parsing TSV content with header row"""
        tsv_content = """position	term	term_number	tab_name	primer	front	back	tags	honorific_level
1	안녕 [annyeong]	1	Scene	Enter room	Greeting?	Hello	greeting	casual"""
        
        response = Stage2Response.from_tsv_content(tsv_content)
        assert len(response.rows) == 1
        assert response.rows[0].term == "안녕 [annyeong]"
    
    def test_parse_empty_tsv(self):
        """Test parsing empty TSV content"""
        response = Stage2Response.from_tsv_content("")
        assert len(response.rows) == 0
    
    def test_parse_malformed_tsv(self):
        """Test error handling for malformed TSV"""
        # Too few columns
        tsv_content = "1	안녕	1"  # Only 3 columns
        
        response = Stage2Response.from_tsv_content(tsv_content)
        assert len(response.rows) == 0  # Should skip invalid rows
    
    def test_to_tsv_format(self):
        """Test converting Stage2Response to TSV format"""
        rows = [
            FlashcardRow(
                position=1, term="안녕 [annyeong]", term_number=1, tab_name="Scene",
                primer="Enter", front="Q", back="A", tags="test", honorific_level=""
            )
        ]
        response = Stage2Response(rows=rows)
        
        tsv = response.to_tsv()
        lines = tsv.strip().split('\n')
        
        assert len(lines) == 2  # Header + 1 data row
        assert lines[0].startswith("position\tterm")
        assert "안녕 [annyeong]" in lines[1]


class TestApiUsageCalculation:
    """Test API usage tracking and cost calculation"""
    
    def test_token_counting(self):
        """Test token usage tracking"""
        usage = ApiUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
    
    def test_cost_calculation(self):
        """Test cost calculation for Claude Sonnet 4"""
        # At $15/1M tokens
        usage = ApiUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500
        )
        
        expected_cost = (1500 / 1_000_000) * 15.0
        assert abs(usage.estimated_cost - expected_cost) < 0.0001
    
    def test_large_token_cost(self):
        """Test cost calculation for large token counts"""
        usage = ApiUsage(
            prompt_tokens=50_000,
            completion_tokens=25_000,
            total_tokens=75_000
        )
        
        expected_cost = (75_000 / 1_000_000) * 15.0
        assert abs(usage.estimated_cost - expected_cost) < 0.01


class TestBatchProgress:
    """Test batch progress tracking"""
    
    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        progress = BatchProgress(
            batch_id="test-batch",
            total_items=100,
            completed_items=75,
            failed_items=5,
            started_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert progress.progress_percentage == 75.0
    
    def test_items_per_second(self):
        """Test processing rate calculation"""
        from datetime import timedelta
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)
        
        progress = BatchProgress(
            batch_id="test-batch",
            total_items=100,
            completed_items=50,
            failed_items=0,
            started_at=start_time,
            updated_at=end_time
        )
        
        # Should be 5 items per second (50 items in 10 seconds)
        assert abs(progress.items_per_second - 5.0) < 0.1


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_unicode_handling(self):
        """Test proper Unicode/Korean character handling"""
        item = VocabularyItem(
            position=1,
            term="🇰🇷 한국 Korea",  # Mixed unicode
            type="noun"
        )
        assert "🇰🇷" in item.term
        assert "한국" in item.term
    
    def test_very_long_text(self):
        """Test handling of very long text fields"""
        long_text = "설명" * 500  # Very long explanation
        
        row = FlashcardRow(
            position=1,
            term="test",
            term_number=1,
            tab_name="Test",
            primer="",
            front="Q",
            back=long_text,
            tags="",
            honorific_level=""
        )
        assert len(row.back) == len(long_text)
    
    def test_special_characters_in_tsv(self):
        """Test handling of special characters that could break TSV"""
        row = FlashcardRow(
            position=1,
            term="test\ttab",  # Tab in term
            term_number=1,
            tab_name="Test\nNewline",  # Newline in field
            primer="",
            front="Q",
            back="A",
            tags="",
            honorific_level=""
        )
        
        # Should handle special characters when converting to TSV
        tsv = row.to_tsv_row()
        assert "\t" in tsv  # Should still have tab delimiters
        assert tsv.count("\t") == 8  # Should have exactly 8 tabs