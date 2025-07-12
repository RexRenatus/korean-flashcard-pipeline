"""
Output parsers for Stage 1 (Nuance Creator) and Stage 2 (Flashcard Generator).
Handles structured output validation and parsing.
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from ..core.models import (
    Stage1Response, Stage2Response, Comparison, Homonym, 
    FlashcardRow, VocabularyItem
)
from ..database import DatabaseManager
from ..core.exceptions import ValidationError, ParsingError

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates output against specifications"""
    
    # Required fields for Stage 1
    STAGE1_REQUIRED_FIELDS = {
        "term_number", "term", "ipa", "pos", "primary_meaning",
        "metaphor", "metaphor_noun", "metaphor_action", "suggested_location",
        "anchor_object", "anchor_sensory", "explanation", "comparison", 
        "korean_keywords"
    }
    
    # Required fields for Stage 2
    STAGE2_REQUIRED_FIELDS = {
        "position", "term", "term_number", "tab_name", "front", "back"
    }
    
    # Valid part of speech values
    VALID_POS = {
        "noun", "verb", "adjective", "adverb", "particle",
        "determiner", "numeral", "pronoun", "interjection"
    }
    
    # Valid tab names
    VALID_TAB_NAMES = {
        "Scene", "Usage-Comparison", "Hanja", "Grammar",
        "Formal-Casual", "Example", "Cultural"
    }
    
    def validate_stage1_output(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate Stage 1 output structure
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        missing_fields = self.STAGE1_REQUIRED_FIELDS - set(data.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate field types
        if "term" in data and not isinstance(data["term"], str):
            errors.append("Field 'term' must be a string")
        
        if "pos" in data and data["pos"] not in self.VALID_POS:
            errors.append(f"Invalid part of speech: {data['pos']}")
        
        if "korean_keywords" in data:
            if not isinstance(data["korean_keywords"], list):
                errors.append("Field 'korean_keywords' must be a list")
            elif len(data["korean_keywords"]) == 0:
                errors.append("Field 'korean_keywords' cannot be empty")
        
        # Validate comparison structure
        if "comparison" in data:
            if not isinstance(data["comparison"], dict):
                errors.append("Field 'comparison' must be a dictionary")
            elif "vs" not in data["comparison"] or "nuance" not in data["comparison"]:
                errors.append("Comparison missing 'vs' or 'nuance' field")
        
        # Validate homonyms structure
        if "homonyms" in data and data["homonyms"]:
            if not isinstance(data["homonyms"], list):
                errors.append("Field 'homonyms' must be a list")
            else:
                for idx, hom in enumerate(data["homonyms"]):
                    if not isinstance(hom, dict):
                        errors.append(f"Homonym[{idx}] must be a dictionary")
                    elif "term" not in hom or "meaning" not in hom:
                        errors.append(f"Homonym[{idx}] missing 'term' or 'meaning' field")
        
        return len(errors) == 0, errors
    
    def validate_stage2_output(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate Stage 2 output structure
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        if not isinstance(data, list):
            errors.append("Stage 2 output must be a list of flashcard rows")
            return False, errors
        
        if len(data) == 0:
            errors.append("Stage 2 output cannot be empty")
            return False, errors
        
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                errors.append(f"Row[{idx}] must be a dictionary")
                continue
            
            # Check required fields
            missing_fields = self.STAGE2_REQUIRED_FIELDS - set(row.keys())
            if missing_fields:
                errors.append(f"Row[{idx}] missing required fields: {', '.join(missing_fields)}")
            
            # Validate field types
            if "position" in row:
                if not isinstance(row["position"], int) or row["position"] <= 0:
                    errors.append(f"Row[{idx}] 'position' must be a positive integer")
            
            if "term_number" in row:
                if not isinstance(row["term_number"], int) or row["term_number"] <= 0:
                    errors.append(f"Row[{idx}] 'term_number' must be a positive integer")
            
            if "tab_name" in row and row["tab_name"] not in self.VALID_TAB_NAMES:
                errors.append(f"Row[{idx}] invalid tab_name: {row['tab_name']}")
        
        return len(errors) == 0, errors


class NuanceOutputParser:
    """Parses Stage 1 (Nuance Creator) output"""
    
    def __init__(self, validator: Optional[OutputValidator] = None):
        self.validator = validator or OutputValidator()
    
    def parse(self, raw_output: str) -> Stage1Response:
        """Parse raw Stage 1 output into structured response"""
        try:
            # Extract JSON from potential markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = raw_output.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate structure
            is_valid, errors = self.validator.validate_stage1_output(data)
            if not is_valid:
                raise ValidationError(f"Invalid Stage 1 output: {'; '.join(errors)}")
            
            # Handle comparison
            comparison = Comparison(
                vs=data["comparison"]["vs"],
                nuance=data["comparison"]["nuance"]
            )
            
            homonyms = []
            if data.get("homonyms"):
                homonyms = [
                    Homonym(
                        hanja=h.get("hanja", ""),
                        reading=h.get("reading", ""),
                        meaning=h["meaning"],
                        differentiator=h.get("differentiator", "")
                    )
                    for h in data["homonyms"]
                ]
            
            # Create response object
            response = Stage1Response(
                term_number=data["term_number"],
                term=data["term"],
                ipa=data["ipa"],
                pos=data["pos"],
                primary_meaning=data["primary_meaning"],
                other_meanings=data.get("other_meanings"),
                metaphor=data["metaphor"],
                metaphor_noun=data["metaphor_noun"],
                metaphor_action=data["metaphor_action"],
                suggested_location=data["suggested_location"],
                anchor_object=data["anchor_object"],
                anchor_sensory=data["anchor_sensory"],
                explanation=data["explanation"],
                usage_context=data.get("usage_context"),
                comparison=comparison,
                homonyms=homonyms,
                korean_keywords=data["korean_keywords"]
            )
            
            return response
            
        except json.JSONDecodeError as e:
            raise ParsingError(f"Failed to parse Stage 1 JSON: {e}")
        except KeyError as e:
            raise ParsingError(f"Missing required field in Stage 1 output: {e}")
        except Exception as e:
            raise ParsingError(f"Unexpected error parsing Stage 1 output: {e}")
    
    def extract_keywords(self, response: Stage1Response) -> List[str]:
        """Extract searchable keywords from Stage 1 response"""
        keywords = []
        
        # Korean keywords
        keywords.extend(response.korean_keywords)
        
        # Term
        keywords.append(response.term)
        
        # Metaphor components
        keywords.append(response.metaphor_noun)
        keywords.append(response.metaphor_action)
        
        # Comparison terms
        keywords.append(response.comparison.vs)
        
        # Homonym terms
        for hom in response.homonyms:
            keywords.append(hom.reading)
        
        # Remove duplicates and empty strings
        keywords = list(set(k for k in keywords if k))
        
        return keywords


class FlashcardOutputParser:
    """Parses Stage 2 (Flashcard Generator) output"""
    
    def __init__(self, validator: Optional[OutputValidator] = None):
        self.validator = validator or OutputValidator()
    
    def parse(self, raw_output: str) -> Stage2Response:
        """Parse raw Stage 2 output into structured response"""
        try:
            # Extract JSON from potential markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = raw_output.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate structure
            is_valid, errors = self.validator.validate_stage2_output(data)
            if not is_valid:
                raise ValidationError(f"Invalid Stage 2 output: {'; '.join(errors)}")
            
            # Create flashcard rows
            flashcard_rows = []
            for row_data in data:
                flashcard_row = FlashcardRow(
                    position=row_data["position"],
                    term=row_data["term"],
                    term_number=row_data["term_number"],
                    tab_name=row_data["tab_name"],
                    primer=row_data.get("primer", ""),
                    front=row_data["front"],
                    back=row_data["back"],
                    tags=row_data.get("tags", ""),
                    honorific_level=row_data.get("honorific_level", "")
                )
                flashcard_rows.append(flashcard_row)
            
            # Create response
            response = Stage2Response(rows=flashcard_rows)
            
            return response
            
        except json.JSONDecodeError as e:
            raise ParsingError(f"Failed to parse Stage 2 JSON: {e}")
        except KeyError as e:
            raise ParsingError(f"Missing required field in Stage 2 output: {e}")
        except Exception as e:
            raise ParsingError(f"Unexpected error parsing Stage 2 output: {e}")
    
    def validate_tsv_format(self, response: Stage2Response) -> bool:
        """Validate that response can be converted to TSV"""
        try:
            # Test TSV conversion
            tsv_output = response.to_tsv()
            
            # Check that it has correct number of columns
            lines = tsv_output.strip().split('\n')
            if len(lines) < 2:  # Header + at least one row
                return False
            
            # Check header
            header = lines[0].split('\t')
            expected_header = [
                "position", "term", "term_number", "tab_name",
                "primer", "front", "back", "tags", "honorific_level"
            ]
            
            if header != expected_header:
                return False
            
            # Check each row has correct number of columns
            for line in lines[1:]:
                if len(line.split('\t')) != len(expected_header):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def merge_flashcards(self, responses: List[Stage2Response]) -> Stage2Response:
        """Merge multiple Stage 2 responses into one"""
        all_rows = []
        current_position = 1
        
        for response in responses:
            for row in response.rows:
                # Update position to maintain ordering
                new_row = row.model_copy()
                new_row.position = current_position
                all_rows.append(new_row)
                current_position += 1
        
        return Stage2Response(rows=all_rows)


class OutputArchiver:
    """Archives parsed outputs to database"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def archive_stage1_output(self, task_id: str, vocabulary_id: int,
                            raw_output: str, parsed_output: Stage1Response,
                            tokens_used: int, processing_time_ms: float):
        """Archive Stage 1 output for future reference"""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO processing_outputs (
                    task_id, vocabulary_id, stage, raw_output, parsed_output,
                    tokens_used, processing_time_ms, is_valid, created_at
                ) VALUES (?, ?, 1, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (
                task_id,
                vocabulary_id,
                raw_output,
                parsed_output.model_dump_json(),
                tokens_used,
                processing_time_ms
            ))
            conn.commit()
    
    def archive_stage2_output(self, task_id: str, vocabulary_id: int,
                            raw_output: str, parsed_output: Stage2Response,
                            tokens_used: int, processing_time_ms: float):
        """Archive Stage 2 output for future reference"""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO processing_outputs (
                    task_id, vocabulary_id, stage, raw_output, parsed_output,
                    tokens_used, processing_time_ms, is_valid, created_at
                ) VALUES (?, ?, 2, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (
                task_id,
                vocabulary_id,
                raw_output,
                parsed_output.model_dump_json(),
                tokens_used,
                processing_time_ms
            ))
            conn.commit()
    
    def get_archived_output(self, vocabulary_id: int, stage: int) -> Optional[Dict[str, Any]]:
        """Retrieve archived output for a vocabulary item"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM processing_outputs
                WHERE vocabulary_id = ? AND stage = ? AND is_valid = 1
                ORDER BY created_at DESC
                LIMIT 1
            """, (vocabulary_id, stage))
            
            row = cursor.fetchone()
            if row:
                return {
                    "raw_output": row["raw_output"],
                    "parsed_output": json.loads(row["parsed_output"]),
                    "tokens_used": row["tokens_used"],
                    "processing_time_ms": row["processing_time_ms"],
                    "created_at": row["created_at"]
                }
        
        return None


class OutputErrorRecovery:
    """Handles error recovery for malformed outputs"""
    
    def __init__(self):
        self.common_fixes = {
            # Common JSON errors
            r',\s*}': '}',  # Trailing comma before closing brace
            r',\s*\]': ']',  # Trailing comma before closing bracket
            r'"\s*:\s*"([^"]*)"([^,}])': r'": "\1"\2',  # Missing comma after string value
            r'}\s*{': '},{',  # Missing comma between objects
            r']\s*\[': '],[',  # Missing comma between arrays
        }
    
    def attempt_json_recovery(self, raw_output: str) -> Optional[str]:
        """Attempt to fix common JSON formatting errors"""
        fixed_output = raw_output
        
        # Apply common fixes
        for pattern, replacement in self.common_fixes.items():
            fixed_output = re.sub(pattern, replacement, fixed_output)
        
        # Try to extract JSON from markdown if present
        json_match = re.search(r'```(?:json)?\s*([{\[].*?[}\]])\s*```', fixed_output, re.DOTALL)
        if json_match:
            fixed_output = json_match.group(1)
        
        # Validate it's valid JSON
        try:
            json.loads(fixed_output)
            return fixed_output
        except json.JSONDecodeError:
            return None
    
    def extract_partial_data(self, raw_output: str, stage: int) -> Optional[Dict[str, Any]]:
        """Extract as much valid data as possible from malformed output"""
        partial_data = {}
        
        if stage == 1:
            # Try to extract Stage 1 fields using regex
            patterns = {
                "term": r'"term"\s*:\s*"([^"]+)"',
                "ipa": r'"ipa"\s*:\s*"([^"]+)"',
                "pos": r'"pos"\s*:\s*"([^"]+)"',
                "primary_meaning": r'"primary_meaning"\s*:\s*"([^"]+)"',
                "metaphor": r'"metaphor"\s*:\s*"([^"]+)"',
                "explanation": r'"explanation"\s*:\s*"([^"]+)"'
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, raw_output)
                if match:
                    partial_data[field] = match.group(1)
        
        elif stage == 2:
            # Try to extract Stage 2 rows
            row_pattern = r'\{\s*"position"\s*:\s*(\d+)[^}]+\}'
            rows = []
            
            for match in re.finditer(row_pattern, raw_output):
                row_str = match.group(0)
                try:
                    row_data = json.loads(row_str)
                    rows.append(row_data)
                except:
                    continue
            
            if rows:
                partial_data = rows
        
        return partial_data if partial_data else None