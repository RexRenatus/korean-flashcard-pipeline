"""Application-wide constants and configuration values"""

# API Configuration
DEFAULT_API_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0
MAX_CONCURRENT_REQUESTS = 5

# Cache Configuration
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_CACHE_DIR = ".cache"
MAX_CACHE_SIZE = 1000  # Maximum number of cached items

# Rate Limiting
DEFAULT_RATE_LIMIT = 100  # requests per minute
DEFAULT_BURST_SIZE = 20

# Circuit Breaker
DEFAULT_ERROR_THRESHOLD = 5
DEFAULT_RECOVERY_TIMEOUT = 60  # seconds
DEFAULT_HALF_OPEN_REQUESTS = 3

# File Processing
DEFAULT_BATCH_SIZE = 10
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
SUPPORTED_INPUT_FORMATS = [".csv", ".tsv", ".txt"]
SUPPORTED_OUTPUT_FORMATS = [".tsv", ".csv", ".json", ".anki", ".pdf", ".md", ".html"]

# Output Formatting
DEFAULT_OUTPUT_FORMAT = "tsv"
DEFAULT_DELIMITER = "\t"
CSV_DELIMITER = ","

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Database
DEFAULT_DB_PATH = "pipeline.db"
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30

# Processing
DEFAULT_PROCESSING_MODE = "sequential"
PROCESSING_MODES = ["sequential", "concurrent", "batch"]

# Prompts
MAX_PROMPT_LENGTH = 4000
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

# Version
VERSION = "2.0.0"  # Updated for refactored version