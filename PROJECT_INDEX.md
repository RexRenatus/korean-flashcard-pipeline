# Project Index

**Last Updated**: 2025-01-07

## Purpose

This document provides a complete map of all files and directories in the Korean Language Flashcard Pipeline project.

## Directory Structure

```
korean-flashcard-pipeline/
├── .env.example                         # Environment variables template
├── .gitignore                           # Git ignore patterns
├── API_ARCHITECTURE.md                  # API design and architecture
├── CHANGELOG.md                         # Project change history
├── CLAUDE.md                           # AI guidance and rules
├── Cargo.toml                          # Rust workspace configuration
├── DATABASE_SCHEMA.md                  # SQLite database schema
├── PROJECT_INDEX.md                    # This file - project map
├── README.md                           # Project overview
├── pyproject.toml                      # Python project configuration
├── requirements.txt                    # Python dependencies
│
├── Phase1_Design/                      # Design documentation
│   ├── DATABASE_DESIGN.md             # Detailed database design ✅
│   ├── SYSTEM_DESIGN.md               # System architecture ✅
│   ├── API_SPECIFICATIONS.md          # API contracts and formats ✅
│   ├── INTEGRATION_DESIGN.md          # Rust-Python integration ✅
│   └── PIPELINE_DESIGN.md             # Two-stage processing flow ✅
│
├── docs/                               # Technical documentation
│
├── migrations/                         # Database migrations
│   └── 001_initial_schema.sql          # Initial database schema ✅
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
│
├── src/                                # Source code
│   ├── python/                         # Python implementation
│   │   └── flashcard_pipeline/         # Main Python package (pending)
│   │
│   └── rust/                           # Rust implementation
│       ├── cache/                      # Cache module
│       │   └── Cargo.toml             # Cache crate config
│       ├── core/                       # Core types and traits
│       │   └── Cargo.toml             # Core crate config
│       └── pipeline/                   # Pipeline orchestration
│           └── Cargo.toml             # Pipeline crate config
│
└── tests/                              # Test suites
    ├── python/                         # Python tests
    └── rust/                           # Rust tests
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