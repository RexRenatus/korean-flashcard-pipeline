# Source Code Directory

This directory contains all source code for the Korean Language Flashcard Pipeline project, organized by programming language.

## Structure

```
src/
├── python/           # Python implementation (API client, pipeline orchestration)
│   ├── flashcard_pipeline/   # Main Python package
│   └── tests/               # Python-specific unit tests
└── rust/            # Rust implementation (core processing, planned)
    ├── core/        # Core Rust library
    ├── pipeline/    # Rust pipeline binary
    └── cache/       # Caching implementation
```

## Language Distribution

### Python (`/python`)
- **Purpose**: API integration, pipeline orchestration, CLI tools
- **Key Components**:
  - OpenRouter API client
  - Database management
  - Import/export functionality
  - Web interface (planned)
  - Monitoring and health checks

### Rust (`/rust`)
- **Purpose**: High-performance core processing (planned for future phases)
- **Key Components**:
  - Vocabulary processing engine
  - Caching layer
  - Performance-critical algorithms
  - Database core operations

## Development Guidelines

1. **Language Choice**:
   - Use Python for I/O operations, API calls, and orchestration
   - Use Rust for CPU-intensive processing and performance-critical paths
   - Maintain clear interfaces between language boundaries

2. **Code Organization**:
   - Keep language-specific code in respective directories
   - Share data through well-defined APIs and database
   - Document cross-language interfaces clearly

3. **Testing**:
   - Each language has its own test structure
   - Integration tests should cover cross-language functionality
   - Maintain consistent test coverage standards

## Current Status

- ✅ **Python Implementation**: Fully functional (Phases 2-4 complete)
- 🚧 **Rust Implementation**: Planned for future optimization

## Getting Started

- For Python development: See `/src/python/README.md`
- For Rust development: See `/src/rust/README.md`