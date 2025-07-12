"""Utility functions for the flashcard pipeline"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import unicodedata

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename for safe filesystem usage.
    
    Args:
        filename: The filename to sanitize
        max_length: Maximum length for the filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Normalize unicode
    filename = unicodedata.normalize('NFKC', filename)
    
    # Trim whitespace
    filename = filename.strip()
    
    # Ensure not empty
    if not filename:
        filename = "unnamed"
    
    # Truncate if too long
    if len(filename) > max_length:
        base, ext = os.path.splitext(filename)
        if ext:
            base = base[:max_length - len(ext)]
            filename = base + ext
        else:
            filename = filename[:max_length]
    
    return filename


def generate_hash(content: Union[str, Dict[str, Any]], algorithm: str = "sha256") -> str:
    """
    Generate a hash from content.
    
    Args:
        content: String or dictionary to hash
        algorithm: Hash algorithm to use
        
    Returns:
        Hex digest of the hash
    """
    if isinstance(content, dict):
        # Sort for consistent hashing
        content = json.dumps(content, sort_keys=True)
    
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode('utf-8'))
    return hasher.hexdigest()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    truncate_at = max_length - len(suffix)
    return text[:truncate_at] + suffix


def parse_korean_pronunciation(text: str) -> Tuple[str, Optional[str]]:
    """
    Parse Korean text with pronunciation guide.
    
    Args:
        text: Text potentially containing Korean and pronunciation
        
    Returns:
        Tuple of (korean_text, pronunciation)
    """
    # Pattern for text[pronunciation]
    pattern = r'([가-힣]+)\[([a-zA-Z\.\-\s]+)\]'
    match = re.match(pattern, text)
    
    if match:
        return match.group(1), match.group(2)
    
    # Check if it's just Korean text
    if re.match(r'^[가-힣]+$', text):
        return text, None
    
    return text, None


def extract_tags_from_text(text: str) -> List[str]:
    """
    Extract hashtag-style tags from text.
    
    Args:
        text: Text containing potential tags
        
    Returns:
        List of extracted tags
    """
    # Find #tag patterns
    tags = re.findall(r'#(\w+)', text)
    
    # Also look for tag: or tags: patterns
    tag_line = re.search(r'(?:tag|tags):\s*(.+)$', text, re.IGNORECASE | re.MULTILINE)
    if tag_line:
        # Split by common delimiters
        additional_tags = re.split(r'[,;|\s]+', tag_line.group(1))
        tags.extend([t.strip() for t in additional_tags if t.strip()])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    return unique_tags


def format_timestamp(
    dt: Optional[datetime] = None,
    format_string: str = "%Y%m%d_%H%M%S"
) -> str:
    """
    Format a datetime as a string.
    
    Args:
        dt: Datetime to format (defaults to now)
        format_string: strftime format string
        
    Returns:
        Formatted timestamp
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_string)


def parse_difficulty(text: str) -> Optional[str]:
    """
    Parse difficulty level from text.
    
    Args:
        text: Text containing difficulty information
        
    Returns:
        Normalized difficulty level or None
    """
    text = text.lower().strip()
    
    # Map common variations
    difficulty_map = {
        "beginner": "beginner",
        "easy": "beginner",
        "basic": "beginner",
        "novice": "beginner",
        "elementary": "beginner",
        
        "intermediate": "intermediate",
        "medium": "intermediate",
        "moderate": "intermediate",
        "mid": "intermediate",
        
        "advanced": "advanced",
        "hard": "advanced",
        "difficult": "advanced",
        "high": "advanced",
        
        "expert": "expert",
        "master": "expert",
        "professional": "expert",
        "native": "expert",
    }
    
    return difficulty_map.get(text)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    # Rough estimation: ~4 characters per token for English
    # ~2-3 characters per token for Korean
    
    # Count Korean characters
    korean_chars = len(re.findall(r'[가-힣]', text))
    other_chars = len(text) - korean_chars
    
    # Estimate tokens
    korean_tokens = korean_chars / 2.5
    other_tokens = other_chars / 4
    
    return int(korean_tokens + other_tokens)


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks.
    
    Args:
        items: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i:i + chunk_size])
    return chunks


def merge_dictionaries(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge multiple dictionaries.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    
    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dictionaries(result[key], value)
            else:
                result[key] = value
    
    return result


def create_progress_bar(
    current: int,
    total: int,
    width: int = 50,
    filled_char: str = "█",
    empty_char: str = "░"
) -> str:
    """
    Create a text progress bar.
    
    Args:
        current: Current progress
        total: Total items
        width: Width of progress bar
        filled_char: Character for filled portion
        empty_char: Character for empty portion
        
    Returns:
        Progress bar string
    """
    if total == 0:
        percent = 0
    else:
        percent = current / total
    
    filled_width = int(width * percent)
    empty_width = width - filled_width
    
    bar = filled_char * filled_width + empty_char * empty_width
    return f"[{bar}] {percent:6.1%} ({current}/{total})"


def validate_korean_term(term: str) -> bool:
    """
    Validate if a term contains Korean characters.
    
    Args:
        term: Term to validate
        
    Returns:
        True if valid Korean term
    """
    # Must contain at least one Korean character
    return bool(re.search(r'[가-힣]', term))


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove space before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    # Add space after punctuation if missing
    text = re.sub(r'([.,!?;:])([^ ])', r'\1 \2', text)
    
    return text.strip()


def safe_json_loads(
    text: str,
    default: Any = None,
    strict: bool = False
) -> Any:
    """
    Safely parse JSON with fallback.
    
    Args:
        text: JSON text to parse
        default: Default value if parsing fails
        strict: Whether to raise exception on failure
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        if strict:
            raise
        logger.warning(f"Failed to parse JSON: {e}")
        return default


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get information about a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file information
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {"exists": False, "path": str(file_path)}
    
    stat = file_path.stat()
    
    return {
        "exists": True,
        "path": str(file_path),
        "name": file_path.name,
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "created": datetime.fromtimestamp(stat.st_ctime),
        "is_file": file_path.is_file(),
        "is_dir": file_path.is_dir(),
        "suffix": file_path.suffix,
    }


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, name: str = "Operation", logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        self.logger.info(f"{self.name} took {duration:.2f} seconds")
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


# Decorator for retry logic
def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,)
):
    """
    Decorator to retry function on exception.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}"
                    )
                    
                    import time
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        
        return wrapper
    return decorator