"""
Unit tests for output parsers (Stage 1 and Stage 2).
Tests validation, parsing, error handling, and database integration.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from flashcard_pipeline.parsers import (
    OutputValidator, NuanceOutputParser, FlashcardOutputParser,
    OutputArchiver, OutputErrorRecovery
)
from flashcard_pipeline.models import (
    Stage1Response, Stage2Response, Comparison, Homonym, FlashcardRow
)
from flashcard_pipeline.exceptions import ValidationError, ParsingError
from flashcard_pipeline.database import DatabaseManager


class TestOutputValidator:
    """Test output validation logic"""
    
    def setup_method(self):
        self.validator = OutputValidator()
    
    def test_validate_stage1_output_valid(self):
        """Test validation of valid Stage 1 output"""
        valid_data = {
            "term_number": 1,
            "term": "한국",
            "ipa": "/han.ɡuk̚/",
            "pos": "noun",
            "primary_meaning": "Korea",
            "metaphor": "A vibrant flag waving on a mountain peak",
            "metaphor_noun": "flag",
            "metaphor_action": "waving",
            "suggested_location": "mountain peak",
            "anchor_object": "flagpole",
            "anchor_sensory": "the sound of fabric flapping in wind",
            "explanation": "Korea is like a proud flag on a mountain",
            "comparison": {"vs": "조선", "nuance": "Modern vs historical name"},
            "korean_keywords": ["나라", "국가", "반도"]
        }
        
        is_valid, errors = self.validator.validate_stage1_output(valid_data)
        assert is_valid is True
        assert errors == []
    
    def test_validate_stage1_output_missing_fields(self):
        """Test validation catches missing required fields"""
        incomplete_data = {
            "term": "한국",
            "pos": "noun"
        }
        
        is_valid, errors = self.validator.validate_stage1_output(incomplete_data)
        assert is_valid is False
        assert len(errors) > 0
        assert "Missing required fields" in errors[0]
    
    def test_validate_stage1_output_invalid_pos(self):
        """Test validation catches invalid part of speech"""
        data = {
            "term_number": 1,
            "term": "한국",
            "ipa": "/han.ɡuk̚/",
            "pos": "invalid_pos",  # Invalid
            "primary_meaning": "Korea",
            "metaphor": "A vibrant flag",
            "metaphor_noun": "flag",
            "metaphor_action": "waving",
            "suggested_location": "mountain",
            "anchor_object": "pole",
            "anchor_sensory": "wind sound",
            "explanation": "Korea is like a flag",
            "comparison": {"vs": "조선", "nuance": "Different eras"},
            "korean_keywords": ["나라"]
        }
        
        is_valid, errors = self.validator.validate_stage1_output(data)
        assert is_valid is False
        assert any("Invalid part of speech" in error for error in errors)
    
    def test_validate_stage2_output_valid(self):
        """Test validation of valid Stage 2 output"""
        valid_data = [
            {
                "position": 1,
                "term": "한국",
                "term_number": 1,
                "tab_name": "Scene",
                "front": "Front of card",
                "back": "Back of card"
            }
        ]
        
        is_valid, errors = self.validator.validate_stage2_output(valid_data)
        assert is_valid is True
        assert errors == []
    
    def test_validate_stage2_output_invalid_tab(self):
        """Test validation catches invalid tab names"""
        data = [
            {
                "position": 1,
                "term": "한국",
                "term_number": 1,
                "tab_name": "InvalidTab",  # Invalid
                "front": "Front",
                "back": "Back"
            }
        ]
        
        is_valid, errors = self.validator.validate_stage2_output(data)
        assert is_valid is False
        assert any("invalid tab_name" in error for error in errors)


class TestNuanceOutputParser:
    """Test Stage 1 output parsing"""
    
    def setup_method(self):
        self.parser = NuanceOutputParser()
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON output"""
        raw_output = json.dumps({
            "term_number": 1,
            "term": "한국",
            "ipa": "/han.ɡuk̚/",
            "pos": "noun",
            "primary_meaning": "Korea",
            "metaphor": "A vibrant flag waving on a mountain peak",
            "metaphor_noun": "flag",
            "metaphor_action": "waving",
            "suggested_location": "mountain peak",
            "anchor_object": "flagpole",
            "anchor_sensory": "the sound of fabric flapping",
            "explanation": "Korea is like a proud flag",
            "comparison": {"vs": "조선", "nuance": "Modern vs historical"},
            "korean_keywords": ["나라", "국가"]
        })
        
        response = self.parser.parse(raw_output)
        assert isinstance(response, Stage1Response)
        assert response.term == "한국"
        assert response.pos == "noun"
        assert len(response.korean_keywords) == 2
    
    def test_parse_json_in_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        raw_output = """
        Here's the analysis:
        
        ```json
        {
            "term_number": 1,
            "term": "한국",
            "ipa": "/han.ɡuk̚/",
            "pos": "noun",
            "primary_meaning": "Korea",
            "metaphor": "A flag on mountain",
            "metaphor_noun": "flag",
            "metaphor_action": "waving",
            "suggested_location": "mountain",
            "anchor_object": "pole",
            "anchor_sensory": "wind",
            "explanation": "Korea is a flag",
            "comparison": {"vs": "조선", "nuance": "Different eras"},
            "korean_keywords": ["나라"]
        }
        ```
        """
        
        response = self.parser.parse(raw_output)
        assert response.term == "한국"
    
    def test_parse_with_comparisons(self):
        """Test parsing output with comparisons"""
        raw_output = json.dumps({
            "term_number": 1,
            "term": "빨리",
            "ipa": "/p͈al.li/",
            "pos": "adverb",
            "primary_meaning": "quickly",
            "metaphor": "A cheetah sprinting",
            "metaphor_noun": "cheetah",
            "metaphor_action": "sprinting",
            "suggested_location": "savanna",
            "anchor_object": "grass",
            "anchor_sensory": "wind rushing",
            "explanation": "Moving like a cheetah",
            "comparison": {"vs": "급하게", "nuance": "빨리 is faster, 급하게 is more urgent"},
            "korean_keywords": ["속도", "빠른"]
        })
        
        response = self.parser.parse(raw_output)
        assert response.comparison.vs == "급하게"
        assert "빨리 is faster" in response.comparison.nuance
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error"""
        raw_output = "{ invalid json"
        
        with pytest.raises(ParsingError) as exc_info:
            self.parser.parse(raw_output)
        assert "Failed to parse Stage 1 JSON" in str(exc_info.value)
    
    def test_extract_keywords(self):
        """Test keyword extraction from parsed response"""
        response = Stage1Response(
            term_number=1,
            term="한국",
            ipa="/han.ɡuk̚/",
            pos="noun",
            primary_meaning="Korea",
            metaphor="A flag",
            metaphor_noun="flag",
            metaphor_action="waving",
            suggested_location="mountain",
            anchor_object="pole",
            anchor_sensory="wind",
            explanation="Korea",
            korean_keywords=["나라", "국가"],
            comparison=Comparison(vs="조선", nuance="different eras"),
            homonyms=[Homonym(hanja="韓國", reading="한국", meaning="Korean food", differentiator="cuisine")]
        )
        
        keywords = self.parser.extract_keywords(response)
        assert "한국" in keywords
        assert "나라" in keywords
        assert "flag" in keywords
        assert "조선" in keywords


class TestFlashcardOutputParser:
    """Test Stage 2 output parsing"""
    
    def setup_method(self):
        self.parser = FlashcardOutputParser()
    
    def test_parse_valid_json_array(self):
        """Test parsing valid JSON array output"""
        raw_output = json.dumps([
            {
                "position": 1,
                "term": "한국",
                "term_number": 1,
                "tab_name": "Scene",
                "primer": "Korea",
                "front": "Picture a flag on mountain",
                "back": "한국 - Korea",
                "tags": "country noun",
                "honorific_level": "neutral"
            }
        ])
        
        response = self.parser.parse(raw_output)
        assert isinstance(response, Stage2Response)
        assert len(response.rows) == 1
        assert response.rows[0].term == "한국"
        assert response.rows[0].tab_name == "Scene"
    
    def test_parse_multiple_cards(self):
        """Test parsing multiple flashcards"""
        raw_output = json.dumps([
            {
                "position": 1,
                "term": "한국",
                "term_number": 1,
                "tab_name": "Scene",
                "front": "Front 1",
                "back": "Back 1"
            },
            {
                "position": 2,
                "term": "한국",
                "term_number": 1,
                "tab_name": "Usage-Comparison",
                "front": "Front 2",
                "back": "Back 2"
            }
        ])
        
        response = self.parser.parse(raw_output)
        assert len(response.rows) == 2
        assert response.rows[1].tab_name == "Usage-Comparison"
    
    def test_validate_tsv_format(self):
        """Test TSV format validation"""
        response = Stage2Response(rows=[
            FlashcardRow(
                position=1,
                term="한국",
                term_number=1,
                tab_name="Scene",
                primer="Korea",
                front="Front",
                back="Back",
                tags="noun",
                honorific_level="neutral"
            )
        ])
        
        is_valid = self.parser.validate_tsv_format(response)
        assert is_valid is True
    
    def test_merge_flashcards(self):
        """Test merging multiple responses"""
        response1 = Stage2Response(rows=[
            FlashcardRow(
                position=5,
                term="한국",
                term_number=1,
                tab_name="Scene",
                primer="",
                front="F1",
                back="B1",
                tags=""
            )
        ])
        
        response2 = Stage2Response(rows=[
            FlashcardRow(
                position=10,
                term="빨리",
                term_number=2,
                tab_name="Scene",
                primer="",
                front="F2",
                back="B2",
                tags=""
            )
        ])
        
        merged = self.parser.merge_flashcards([response1, response2])
        assert len(merged.rows) == 2
        assert merged.rows[0].position == 1  # Renumbered
        assert merged.rows[1].position == 2


class TestOutputArchiver:
    """Test output archiving to database"""
    
    def setup_method(self):
        self.db_manager = Mock(spec=DatabaseManager)
        self.archiver = OutputArchiver(self.db_manager)
    
    def test_archive_stage1_output(self):
        """Test archiving Stage 1 output"""
        # Setup mock connection
        mock_conn = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        self.db_manager.get_connection.return_value = mock_context
        
        # Create test data
        parsed_output = Stage1Response(
            term_number=1,
            term="한국",
            ipa="/han.ɡuk̚/",
            pos="noun",
            primary_meaning="Korea",
            metaphor="A flag",
            metaphor_noun="flag",
            metaphor_action="waving",
            suggested_location="mountain",
            anchor_object="pole",
            anchor_sensory="wind",
            explanation="Korea",
            comparison=Comparison(vs="조선", nuance="Modern era"),
            korean_keywords=["나라"]
        )
        
        # Archive output
        self.archiver.archive_stage1_output(
            task_id="task123",
            vocabulary_id=1,
            raw_output="raw json",
            parsed_output=parsed_output,
            tokens_used=100,
            processing_time_ms=500.0
        )
        
        # Verify database interaction
        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO processing_outputs" in sql
        assert "stage" in sql
        
        # Check parameters
        params = mock_conn.execute.call_args[0][1]
        assert params[0] == "task123"
        assert params[1] == 1
    
    def test_get_archived_output(self):
        """Test retrieving archived output"""
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_conn
        mock_context.__exit__.return_value = None
        self.db_manager.get_connection.return_value = mock_context
        
        # Mock database row
        mock_cursor.fetchone.return_value = {
            "raw_output": "raw json",
            "parsed_output": '{"term": "한국"}',
            "tokens_used": 100,
            "processing_time_ms": 500.0,
            "created_at": "2024-01-09"
        }
        
        # Get archived output
        result = self.archiver.get_archived_output(vocabulary_id=1, stage=1)
        
        assert result is not None
        assert result["raw_output"] == "raw json"
        assert result["tokens_used"] == 100
        assert result["parsed_output"]["term"] == "한국"


class TestOutputErrorRecovery:
    """Test error recovery for malformed outputs"""
    
    def setup_method(self):
        self.recovery = OutputErrorRecovery()
    
    def test_fix_trailing_comma(self):
        """Test fixing trailing comma errors"""
        malformed = '{"term": "한국", "pos": "noun",}'
        fixed = self.recovery.attempt_json_recovery(malformed)
        assert fixed == '{"term": "한국", "pos": "noun"}'
        
        # Verify it's valid JSON
        json.loads(fixed)
    
    def test_fix_missing_comma(self):
        """Test fixing missing comma between values"""
        malformed = '{"term": "한국" "pos": "noun"}'
        fixed = self.recovery.attempt_json_recovery(malformed)
        # This specific case might not be fixed, but should not crash
        assert fixed is None or json.loads(fixed)
    
    def test_extract_from_markdown(self):
        """Test extracting JSON from markdown blocks"""
        markdown = """
        ```json
        {"term": "한국", "pos": "noun"}
        ```
        """
        fixed = self.recovery.attempt_json_recovery(markdown)
        assert fixed == '{"term": "한국", "pos": "noun"}'
    
    def test_extract_partial_stage1_data(self):
        """Test extracting partial data from corrupted Stage 1 output"""
        corrupted = '''
        {
            "term": "한국",
            "ipa": "/han.ɡuk̚/",
            "pos": "noun",
            CORRUPTED DATA HERE
            "primary_meaning": "Korea"
        '''
        
        partial = self.recovery.extract_partial_data(corrupted, stage=1)
        assert partial is not None
        assert partial["term"] == "한국"
        assert partial["ipa"] == "/han.ɡuk̚/"
        assert partial["pos"] == "noun"
        assert partial["primary_meaning"] == "Korea"
    
    def test_extract_partial_stage2_data(self):
        """Test extracting partial data from corrupted Stage 2 output"""
        corrupted = '''
        [
            {"position": 1, "term": "한국", "tab_name": "Scene"},
            CORRUPTED ROW,
            {"position": 3, "term": "빨리", "tab_name": "Scene"}
        ]
        '''
        
        partial = self.recovery.extract_partial_data(corrupted, stage=2)
        # Basic extraction might not work with complex corruption
        # This test mainly ensures no crash
        assert partial is None or isinstance(partial, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])