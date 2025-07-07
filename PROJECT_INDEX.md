# Project Index

**Last Updated**: 2025-01-07

## Purpose

This document provides a complete map of all files and directories in the Korean Language Flashcard Pipeline project.

## Directory Structure

```
korean-flashcard-pipeline/
├── .github/                             # GitHub configuration
│   └── workflows/                       # GitHub Actions workflows
│       └── ci.yml                      # CI/CD pipeline ✅
├── .env.example                         # Environment variables template
├── .env.test                            # Test environment variables ✅
├── .gitignore                           # Git ignore patterns ✅
├── .coverage                            # Test coverage data (generated)
├── .pytest_cache/                       # Pytest cache (generated)
├── CHANGELOG.md                         # Project change history ✅
├── CLAUDE.md                           # AI guidance and rules ✅
├── Cargo.toml                          # Rust workspace configuration ✅
├── Makefile                            # Build and test automation ✅
├── PROJECT_INDEX.md                    # This file - project map ✅
├── README.md                           # Project overview ✅
├── pytest.ini                          # Pytest configuration ✅
├── pyproject.toml                      # Python project configuration
├── requirements.txt                    # Python dependencies
├── run_tests.sh                        # Test runner script ✅
├── run_tests_mock.py                   # Mock test runner script ✅
├── test_5_words.csv                    # Test CSV file with 5 Korean words ✅
├── test_concurrent_simple.py           # Simple concurrent processing test ✅
├── test_output.tsv                     # Test output TSV file (generated) ✅
├── test_pipeline.db                    # Test database ✅
├── venv/                               # Python virtual environment (not tracked)
│   └── (auto-generated packages)       # pip installed dependencies
│
├── Phase1_Design/                      # Design documentation
│   ├── DATABASE_DESIGN.md             # Detailed database design ✅
│   ├── SYSTEM_DESIGN.md               # System architecture ✅
│   ├── API_SPECIFICATIONS.md          # API contracts and formats ✅
│   ├── INTEGRATION_DESIGN.md          # Rust-Python integration ✅
│   └── PIPELINE_DESIGN.md             # Two-stage processing flow ✅
│
├── docs/                               # Technical documentation
│   ├── README.md                       # Documentation overview ✅
│   ├── TEST_COVERAGE.md                # Test coverage report ✅
│   ├── user/                           # User documentation
│   │   └── CLI_GUIDE.md                # Comprehensive CLI user guide ✅
│   ├── architecture/                   # Architecture documentation
│   │   ├── README.md                   # Architecture overview ✅
│   │   ├── API_ARCHITECTURE.md         # API design (moved) ✅
│   │   ├── DATABASE_SCHEMA.md          # Database schema (moved) ✅
│   │   └── CLI_ARCHITECTURE.md         # CLI architecture (moved) ✅
│   ├── implementation/                 # Implementation documentation
│   │   ├── README.md                   # Implementation overview ✅
│   │   ├── CLI_IMPLEMENTATION_PLAN.md  # CLI implementation (moved) ✅
│   │   ├── CONCURRENT_PROCESSING_ARCHITECTURE.md # Concurrent design (moved) ✅
│   │   └── CONCURRENT_IMPLEMENTATION_PLAN.md # Concurrent plan (moved) ✅
│   ├── api/                            # API documentation 📝
│   └── developer/                      # Developer documentation 📝
│
├── htmlcov/                            # Coverage HTML reports (generated)
│
├── migrations/                         # Database migrations
│   ├── 001_initial_schema.sql          # Initial database schema ✅
│   ├── 002_concurrent_processing.sql   # Concurrent processing support ✅
│   └── 003_flashcards_tables.sql       # Flashcards and batches tables ✅
│
├── planning/                           # Project management
│   ├── MASTER_TODO.md                 # Task tracking ✅
│   ├── PROJECT_JOURNAL.md             # Development history ✅
│   ├── PROJECT_REQUIREMENTS_QUESTIONNAIRE.md # Requirements gathering ✅
│   ├── MVP_DEFINITION.md              # MVP vs nice-to-have features ✅
│   ├── PHASE_ROADMAP.md               # Implementation phases ✅
│   └── ARCHITECTURE_DECISIONS.md      # Key technical decisions ✅
│
├── scripts/                            # Utility scripts
│   ├── setup_test_env.py               # Test environment setup script ✅
│   └── run_migrations.py               # Database migration runner ✅
│
├── src/                                # Source code
│   ├── python/                         # Python implementation
│   │   └── flashcard_pipeline/         # Main Python package ✅
│   │       ├── __init__.py             # Package initialization ✅
│   │       ├── __main__.py             # Package entry point ✅
│   │       ├── models.py               # Pydantic models ✅
│   │       ├── exceptions.py           # Custom exceptions ✅
│   │       ├── api_client.py           # OpenRouter API client ✅
│   │       ├── rate_limiter.py         # Rate limiting logic ✅
│   │       ├── cache.py                # Cache service ✅
│   │       ├── circuit_breaker.py      # Circuit breaker pattern ✅
│   │       ├── cli.py                  # CLI interface with typer ✅
│   │       ├── cli_v2.py               # Enhanced CLI v2 - All 5 phases implemented ✅
│   │       ├── cli/                    # Enhanced CLI module 🚧
│   │       │   ├── __init__.py         # CLI module initialization ✅
│   │       │   ├── base.py             # Base CLI classes ✅
│   │       │   ├── config.py           # Configuration system ✅
│   │       │   ├── errors.py           # CLI error handling ✅
│   │       │   ├── utils.py            # CLI utilities ✅
│   │       │   ├── commands/           # CLI commands 🚧
│   │       │   ├── plugins/            # Plugin system 🚧
│   │       │   └── integrations/       # Third-party integrations 🚧
│   │       └── concurrent/             # Concurrent processing module ✅
│   │           ├── __init__.py         # Module initialization ✅
│   │           ├── ordered_collector.py # Ordered results collector ✅
│   │           ├── distributed_rate_limiter.py # Thread-safe rate limiter ✅
│   │           ├── progress_tracker.py  # Concurrent progress tracking ✅
│   │           ├── orchestrator.py      # Concurrent pipeline orchestrator ✅
│   │           ├── batch_writer.py      # Ordered batch database writer ✅
│   │           └── monitoring.py        # Performance monitoring ✅
│   │
│   └── rust/                           # Rust implementation
│       ├── cache/                      # Cache module
│       │   └── Cargo.toml             # Cache crate config
│       ├── core/                       # Core types and traits ✅
│       │   ├── Cargo.toml             # Core crate config ✅
│       │   ├── src/                   # Core source files
│       │   │   ├── lib.rs             # Core library root ✅
│       │   │   ├── models/            # Domain models ✅
│       │   │   ├── database/          # Database layer ✅
│       │   │   ├── cache_manager.rs   # Cache management ✅
│       │   │   ├── traits.rs          # Repository traits ✅
│       │   │   ├── logging.rs         # Logging utilities ✅
│       │   │   └── python_interop.rs  # PyO3 bindings ✅
│       │   └── tests/                 # Core unit tests
│       │       └── mod.rs             # Test module definition ✅
│       └── pipeline/                   # Pipeline orchestration
│           ├── Cargo.toml             # Pipeline crate config ✅
│           └── src/                   # Pipeline source files
│               ├── lib.rs             # Pipeline library root ✅
│               ├── errors.rs          # Pipeline error types ✅
│               ├── python_bridge.rs   # Python integration ✅
│               ├── batch_processor.rs # Batch processing logic ✅
│               ├── export.rs          # TSV/CSV export functionality ✅
│               ├── monitoring.rs      # Metrics and health checks ✅
│               ├── pipeline.rs        # Main pipeline orchestration ✅
│               ├── cli.rs             # Command-line interface ✅
│               └── main.rs            # Binary entry point ✅
│
└── tests/                              # Test suites
    ├── data/                           # Test data directory ✅
    │   ├── input/                      # Test input files ✅
    │   ├── output/                     # Test output files ✅
    │   ├── mock_api_responses.json     # Mock API responses ✅
    │   └── test_vocabulary.csv         # Test vocabulary data ✅
    ├── fixtures/                       # Test data files
    │   └── sample_vocabulary.csv       # Sample CSV for testing ✅
    ├── integration/                    # Integration tests
    │   ├── test_end_to_end.py          # End-to-end pipeline tests ✅
    │   ├── test_full_pipeline.py       # Comprehensive pipeline tests ✅
    │   └── test_concurrent_pipeline.py # Concurrent pipeline tests ✅
    ├── python/                         # Python tests
    │   ├── test_models.py              # Model unit tests ✅
    │   ├── test_api_client.py          # API client tests ✅
    │   ├── test_rate_limiter.py        # Rate limiter tests ✅
    │   ├── test_cache_service.py       # Cache service tests ✅
    │   ├── test_circuit_breaker.py     # Circuit breaker tests ✅
    │   └── test_concurrent_processing.py # Concurrent processing tests ✅
    └── rust/                           # Rust tests
        ├── test_models.rs              # Model unit tests ✅
        ├── test_cache_manager.rs       # Cache manager tests ✅
        ├── test_database_repositories.rs # Database repository tests ✅
        └── test_python_bridge.rs       # Python-Rust bridge tests ✅
```

## Key Files

### Configuration Files
- **Cargo.toml**: Root Rust workspace configuration
- **pyproject.toml**: Python project metadata and tool configuration
- **requirements.txt**: Python package dependencies
- **.gitignore**: Git ignore patterns

### Documentation
- **README.md**: Project overview and quick start guide
- **CLAUDE.md**: AI assistant guidance with comprehensive rule sets
- **CHANGELOG.md**: Track all project changes
- **API_ARCHITECTURE.md**: System architecture and API design
- **DATABASE_SCHEMA.md**: Original SQLite schema documentation
- **Phase1_Design/DATABASE_DESIGN.md**: Reorganized database design following SOLID principles

### Planning (To Be Created)
- **planning/MASTER_TODO.md**: Central task tracking
- **planning/PROJECT_JOURNAL.md**: Development history
- **planning/PHASE_ROADMAP.md**: Implementation phases
- **planning/ARCHITECTURE_DECISIONS.md**: ADR format decisions

### Source Code Structure

#### Rust Crates
1. **flashcard-core**: Core domain types and traits
2. **flashcard-pipeline**: Pipeline orchestration logic
3. **flashcard-cache**: Caching layer implementation

#### Python Packages
1. **flashcard_pipeline**: Main Python package containing:
   - API client for OpenRouter
   - CLI interface
   - Integration utilities

## Status Legend

- ✅ Complete
- 🚧 In Progress
- ⏳ Pending
- 🔄 Needs Update

## Update Requirements

Per CLAUDE.md rule file-1: This file must be updated whenever new files are added to the project.