# 🏗️ Architecture Documentation

This section contains detailed documentation about the system architecture, design decisions, and technical specifications of the Korean Flashcard Pipeline.

## 📑 Documents

### Core Architecture
- **[API Architecture](./API_ARCHITECTURE.md)** - Overall system architecture and API design principles
- **[Database Schema](./DATABASE_SCHEMA.md)** - SQLite database design and relationships
- **[CLI Architecture](./CLI_ARCHITECTURE.md)** - Command-line interface design and structure

### Design Documents
- **[System Design](../../Phase1_Design/SYSTEM_DESIGN.md)** - Original system design document
- **[API Specifications](../../Phase1_Design/API_SPECIFICATIONS.md)** - Detailed API specifications
- **[Integration Design](../../Phase1_Design/INTEGRATION_DESIGN.md)** - Rust-Python integration architecture
- **[Pipeline Design](../../Phase1_Design/PIPELINE_DESIGN.md)** - Two-stage processing pipeline design

## 🎯 Key Architecture Principles

### 1. **Two-Stage Processing**
- Stage 1: Semantic analysis and context extraction
- Stage 2: Flashcard generation with educational formatting
- Permanent caching between stages

### 2. **Modular Design**
- Clear separation between Rust core and Python API layer
- Plugin architecture for extensibility
- Microservice-ready design

### 3. **Performance First**
- Rust for high-performance data processing
- Concurrent processing with order preservation
- Efficient caching strategies

### 4. **Reliability**
- Comprehensive error handling
- Resume capability for interrupted batches
- Circuit breaker pattern for API calls

## 🔧 Technology Stack

### Core Technologies
| Component | Technology | Purpose |
|-----------|------------|---------|
| Core Engine | Rust | High-performance processing |
| API Client | Python | OpenRouter integration |
| Database | SQLite | Caching and persistence |
| CLI | Python (Typer) | User interface |
| Bridge | PyO3 | Rust-Python interop |

### Key Libraries
- **Rust**: tokio (async), sqlx (database), serde (serialization)
- **Python**: httpx (HTTP), pydantic (validation), rich (UI)

## 📊 System Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CLI Layer     │────▶│  Core Pipeline  │────▶│   API Layer     │
│   (Python)      │     │    (Rust)       │     │   (Python)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       ▼                        │
         │              ┌─────────────────┐              │
         └─────────────▶│    Database     │◀─────────────┘
                        │    (SQLite)     │
                        └─────────────────┘
```

## 🗄️ Database Architecture

### Core Tables
1. **vocabulary_items** - Source vocabulary storage
2. **stage1_cache** - Semantic analysis cache
3. **stage2_cache** - Flashcard generation cache
4. **flashcards** - Final flashcard storage
5. **processing_batches** - Batch tracking

### Performance Optimizations
- WAL mode for concurrent access
- Strategic indexes on frequently queried columns
- Prepared statements for common operations
- Connection pooling

## 🔌 Integration Points

### API Integration
- OpenRouter for Claude Sonnet 4 access
- RESTful internal APIs
- Plugin system for extensions

### Data Flow
1. CSV input → Vocabulary parsing
2. Vocabulary → Stage 1 (Semantic analysis)
3. Stage 1 → Stage 2 (Flashcard generation)
4. Stage 2 → Export (TSV/Anki/etc.)

## 🛡️ Security Considerations

- No hardcoded credentials
- Environment-based configuration
- Input validation at all boundaries
- Secure error handling

## 📈 Scalability

### Current Limits
- Single-node processing
- SQLite database (suitable for <100GB)
- Memory-bound for very large batches

### Future Scaling Options
- Distributed processing support
- PostgreSQL migration path
- Cloud storage integration
- Horizontal scaling via queue distribution

## 🔍 Related Documentation

- [Implementation Details](../implementation/)
- [API Documentation](../api/)
- [Database Design Details](../../Phase1_Design/DATABASE_DESIGN.md)
- [Architecture Decisions](../../planning/ARCHITECTURE_DECISIONS.md)