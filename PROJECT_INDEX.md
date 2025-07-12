# PROJECT INDEX 📑

**Last Updated**: 2025-01-12 (Post-Reorganization for GitHub Deployment)

## Purpose

This document provides a complete map of all files and directories in the Korean Language Flashcard Pipeline project, now reorganized for production deployment.

## 🔄 Recent Update
The project structure has been reorganized for GitHub deployment with proper directory structure, standard project files, and consolidated components.

## 🏗️ Reorganized Project Structure

```
korean-flashcard-pipeline/
├── .claude/                             # Claude Code configuration
│   ├── settings.json                   # Automated hook system ✅
│   ├── settings_enhanced.json          # Enhanced settings reference ✅
│   └── mcp_ref_hooks.json              # MCP Ref documentation search configuration ✅
├── .github/                             # GitHub configuration
│   └── workflows/                       # GitHub Actions workflows
│       └── ci.yml                      # CI/CD pipeline ✅
├── .env.example                         # Environment variables template
├── .env.test                            # Test environment variables ✅
├── .gitignore                           # Git ignore patterns ✅
├── .coverage                            # Test coverage data (generated)
├── .pytest_cache/                       # Pytest cache (generated)
├── CHANGELOG.md                         # Project change history ✅
├── CLAUDE.md                           # AI guidance and rules (with hooks) ✅
├── CLAUDE_STREAMLINED.md               # Simplified daily reference guide ✅
├── COMPREHENSIVE_TESTING_PLAN.md        # 5-phase testing strategy ✅
├── PHASE2_TEST_FIX_PLAN.md             # Phase 2 test fix breakdown by component ✅
├── PHASE_3_4_IMPLEMENTATION_PLAN.md    # API Client and Pipeline Integration plan ✅
├── Cargo.toml                          # Rust workspace configuration ✅
├── Makefile                            # Build and test automation ✅
├── PROJECT_INDEX.md                    # This file - project map ✅
├── README.md                           # Project overview ✅
├── VERSION.txt                         # Application version ✅
├── PRODUCTION_CHECKLIST.md             # Production deployment checklist ✅
├── pytest.ini                          # Pytest configuration ✅
├── pyproject.toml                      # Python project configuration
├── requirements.txt                    # Python dependencies
├── Dockerfile                          # Docker container definition ✅
├── docker-compose.yml                  # Development Docker Compose ✅
├── docker-compose.production.yml       # Production Docker Compose ✅
├── .env.production                     # Production environment template ✅
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
├── coverage/                           # Test coverage reports ✅
│   ├── htmlcov_root/                  # Root coverage HTML reports
│   └── htmlcov_python/                # Python coverage HTML reports
│
├── external_docs/                      # External documentation ✅
│   ├── anthropic/                     # Anthropic API documentation
│   └── openrouter/                    # OpenRouter API documentation
│
├── test_outputs/                       # Test output files ✅
│   └── output_*.tsv                   # Generated test TSV files
│
├── docs/                               # Technical documentation
│   ├── README.md                       # Documentation overview ✅
│   ├── TEST_COVERAGE.md                # Test coverage report ✅
│   ├── MIGRATION_GUIDE.md              # Database migration guide ✅
│   ├── DATABASE_REORGANIZATION_SUMMARY.md # DB reorganization summary ✅
│   ├── IMPLEMENTATION_ROADMAP.md       # 30-day implementation plan ✅
│   ├── DATABASE_SCHEMA_V2.md           # New database schema ✅
│   ├── NUANCE_CREATOR_OUTPUT_SPEC.md   # Stage 1 output specification ✅
│   ├── FLASHCARD_OUTPUT_SPEC.md        # Stage 2 output specification ✅
│   ├── PROMPT_ENHANCEMENT_SYSTEM.md    # Prompt enhancement documentation ✅
│   ├── DATABASE_RATE_LIMITER.md        # Database rate limiter documentation ✅
│   ├── DATABASE_CIRCUIT_BREAKER.md     # Database circuit breaker documentation ✅
│
├── examples/                           # Example usage scripts
│   ├── pipeline_usage.py               # Example of using sequential and concurrent pipelines ✅
│   ├── processing_optimizer_example.py # Example of using ProcessingOptimizer ✅
│   ├── database_rate_limiter_usage.py  # Example of using DatabaseRateLimiter ✅
│   ├── database_circuit_breaker_usage.py # Example of using DatabaseCircuitBreaker ✅
│   ├── user/                           # User documentation
│   │   └── CLI_GUIDE.md                # Comprehensive CLI user guide ✅
│   ├── architecture/                   # Architecture documentation
│   │   ├── README.md                   # Architecture overview ✅
│   │   ├── API_ARCHITECTURE.md         # API design (moved) ✅
│   │   ├── DATABASE_SCHEMA.md          # Database schema (moved) ✅
│   │   ├── CLI_ARCHITECTURE.md         # CLI architecture (moved) ✅
│   │   ├── GUI_ARCHITECTURE.md         # GUI architecture design ✅
│   │   └── INGRESS_TOLL_DESIGN.md      # Ingress toll system design ✅
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
│   ├── 002_add_ingress_tables.sql      # Ingress system tables ✅
│   ├── 003_database_reorganization_phase1.sql # Normalized schema ✅
│   ├── 004_database_reorganization_phase2.sql # Indexes and views ✅
│   ├── 005_database_reorganization_phase3_data_migration.sql # Data migration ✅
│   ├── 006_stage_output_schema_update.sql # Stage output support ✅
│   ├── 007_add_api_usage_tracking.sql   # API usage tracking tables ✅
│   └── 008_add_circuit_breaker_tracking.sql # Circuit breaker persistence ✅
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
│   ├── run_migrations.py               # Database migration runner ✅
│   ├── migration_runner_v2.py          # Enhanced migration runner with backup ✅
│   ├── automated_backup.py             # Automated database backup script ✅
│   ├── db_integrity_check.py           # Database integrity checker ✅
│   ├── enhance_prompt.py               # Prompt enhancement system ✅
│   ├── enhance_prompt_wrapper.sh       # Hook wrapper for prompt enhancement ✅
│   ├── test_prompt_enhancement.py      # Test script for enhancement system ✅
│   ├── phase_continuation_manager.py   # Phase continuation tracking system ✅
│   ├── health_check.py                 # System health check endpoint ✅
│   ├── deploy.sh                       # Production deployment script ✅
│   ├── backup.sh                       # Automated backup script ✅
│   ├── review/                         # Code review scripts
│   │   ├── pre_task_review.sh          # Pre-task review script ✅
│   │   └── post_task_review.sh         # Post-task review script ✅
│   └── mcp_ref_hooks/                  # MCP Ref documentation search hooks ✅
│       ├── README.md                   # MCP hooks documentation ✅
│       ├── pre_tool_documentation.py   # Pre-tool documentation search ✅
│       ├── error_documentation.py      # Error solution search ✅
│       ├── mcp_ref_wrapper.py          # Direct MCP Ref interface ✅
│       └── integrate_mcp_hooks.py      # Hook integration script ✅
│
├── src/                                # Source code
│   ├── python/                         # Python implementation
│   │   └── flashcard_pipeline/         # Main Python package ✅
│   │       ├── __init__.py             # Package initialization ✅
│   │       ├── __main__.py             # Package entry point ✅
│   │       ├── models.py               # Pydantic models ✅
│   │       ├── exceptions.py           # Custom exceptions ✅
│   │       ├── api_client.py           # OpenRouter API client ✅
│   │       ├── rate_limiter.py         # Rate limiting with database tracking ✅
│   │       ├── cache.py                # Cache service ✅
│   │       ├── circuit_breaker.py      # Circuit breaker pattern ✅
│   │       ├── cli.py                  # CLI interface with typer ✅
│   │       ├── pipeline.py             # Pipeline orchestrator exports ✅
│   │       ├── cli_v2.py               # Enhanced CLI v2 - All 5 phases implemented ✅
│   │       ├── ipc_server.py           # IPC server for Electron communication ✅
│   │       ├── utils.py                # Utility functions (logging, etc.) ✅
│   │       ├── processing_optimizer.py  # Concurrent processing with checkpoints and metrics ✅
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
├── electron-app/                       # Electron desktop application 🚧
│   ├── package.json                    # Node.js project configuration ✅
│   ├── tsconfig.json                   # TypeScript configuration ✅
│   ├── jest.config.js                  # Jest testing configuration ✅
│   ├── vite.config.ts                  # Vite build configuration ✅
│   ├── .eslintrc.json                  # ESLint configuration ✅
│   ├── .prettierrc                     # Prettier configuration ✅
│   ├── .gitignore                      # Git ignore patterns ✅
│   ├── __mocks__/                      # Jest mock files ✅
│   │   ├── styleMock.js                # CSS mock ✅
│   │   └── fileMock.js                 # File mock ✅
│   ├── src/                            # Source code
│   │   ├── main/                       # Electron main process
│   │   │   └── services/               # Backend services
│   │   │       ├── IPCBridge.ts        # Python IPC communication ✅
│   │   │       └── PythonService.ts    # Python API wrapper ✅
│   │   ├── renderer/                   # React application 🚧
│   │   ├── preload/                    # Preload scripts 🚧
│   │   └── shared/                     # Shared code
│   │       └── types.ts                # TypeScript types ✅
│   ├── tests/                          # Test files
│   │   ├── setupTests.ts               # Jest setup and global mocks ✅
│   │   ├── mocks/                      # Mock files
│   │   │   └── fileMock.js             # Static asset mock ✅
│   │   ├── unit/                       # Unit tests
│   │   │   ├── main/                   # Main process tests
│   │   │   │   ├── electron.test.ts    # Electron main process tests ✅
│   │   │   │   └── ipc-handlers.test.ts # IPC handler tests ✅
│   │   │   ├── renderer/               # Renderer process tests
│   │   │   │   ├── App.test.tsx        # App component tests ✅
│   │   │   │   ├── components/         # Component tests
│   │   │   │   │   └── FileUpload.test.tsx # FileUpload component tests ✅
│   │   │   │   └── hooks/              # Custom hook tests
│   │   │   │       └── useSettings.test.ts # Settings hook tests ✅
│   │   │   └── services/               # Service tests
│   │   │       ├── IPCBridge.test.ts   # IPC Bridge tests ✅
│   │   │       └── PythonService.test.ts # Python Service tests ✅
│   │   ├── integration/                # Integration tests
│   │   │   ├── process-vocabulary.test.ts # Vocabulary processing tests ✅
│   │   │   └── database.test.ts        # Database integration tests ✅
│   │   ├── fixtures/                   # Test fixtures
│   │   │   ├── test-data/              # Test data files
│   │   │   │   └── sample-vocabulary.csv # Sample vocabulary CSV ✅
│   │   │   └── mock-api-responses.ts   # Mock API response data ✅
│   │   └── e2e/                        # End-to-end tests 🚧
│   └── assets/                         # Application assets 🚧
│
└── tests/                              # Test suites
    ├── README.md                       # Test suite documentation ✅
    ├── conftest.py                     # Shared pytest fixtures ✅
    ├── test_simple.py                  # Simple sanity test ✅
    ├── test_pipeline_integration.py    # Phase 4 pipeline integration tests ✅
    ├── run_phase1_tests.py             # Phase 1 test runner ✅
    ├── run_phase2_tests.py             # Phase 2 test runner ✅
    ├── unit/                           # Unit tests
    │   ├── test_database_manager.py     # DatabaseManager comprehensive tests ✅
    │   ├── test_database_connection_pool.py # Connection pooling tests ✅
    │   ├── test_database_performance_monitoring.py # Performance monitoring tests ✅
    │   ├── test_processing_optimizer.py  # ProcessingOptimizer unit tests ✅
    │   ├── phase1/                     # Phase 1: Foundation Testing ✅
    │   │   ├── test_models_validation.py # Model validation tests ✅
    │   │   ├── test_configuration.py    # Configuration tests ✅
    │   │   └── test_error_handling.py   # Error handling tests ✅
    │   ├── phase2/                     # Phase 2: Component Testing ✅
    │   │   ├── test_cache_service.py    # Cache service tests ✅
    │   │   ├── test_rate_limiter.py     # Rate limiter tests ✅
    │   │   ├── test_circuit_breaker.py  # Circuit breaker tests ✅
    │   │   ├── test_api_client_mock.py  # Mocked API client tests ✅
    │   │   └── test_database_rate_limiter.py # Database rate limiter tests ✅
    │   ├── phase3/                     # Phase 3: Integration Testing 🔄
    │   └── phase4/                     # Phase 4: Performance Testing 🔄
    ├── e2e/                            # End-to-end tests (Phase 5) 🔄
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
    │   ├── test_concurrent_processing.py # Concurrent processing tests ✅
    │   └── test_output_parsers.py      # Output parser tests (Stage 1 & 2) ✅
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