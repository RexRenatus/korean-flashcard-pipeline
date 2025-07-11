# 🇰🇷 Korean Language Flashcard Pipeline

<div align="center">
  
  [![Build Status](https://img.shields.io/badge/Build-Production_Ready-green?style=for-the-badge)](https://github.com/RexRenatus/korean-flashcard-pipeline)
  [![Rust](https://img.shields.io/badge/Rust-1.75+-orange?style=for-the-badge&logo=rust)](https://www.rust-lang.org/)
  [![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
  [![CLI](https://img.shields.io/badge/CLI-Enhanced_v2-purple?style=for-the-badge)](./docs/user/CLI_GUIDE.md)
  
  [![Portfolio](https://img.shields.io/badge/Portfolio-RexRenatus-black?style=for-the-badge&logo=github)](https://rexrenatus.github.io/RexRenatus.io/)
  [![Instagram](https://img.shields.io/badge/Instagram-@devi.nws-E4405F?style=for-the-badge&logo=instagram)](https://www.instagram.com/devi.nws/)
  [![GitHub](https://img.shields.io/badge/GitHub-Project-181717?style=for-the-badge&logo=github)](https://github.com/RexRenatus/korean-flashcard-pipeline)
  
  <h3>AI-Powered Flashcard Generation System for Korean Language Learning</h3>
  
  > "Transforming vocabulary lists into nuanced, context-rich flashcards  
  > through the power of Claude Sonnet 4 and intelligent caching"
  
</div>

## 🎯 Overview

This project implements a sophisticated two-stage AI pipeline that transforms Korean vocabulary items into comprehensive Anki-compatible flashcards. With a powerful CLI featuring 40+ commands, concurrent processing, and extensive automation capabilities, it's designed for both casual learners and power users.

## 🚀 Current Status

**Version**: 2.0.0 (Post-Refactoring)  
**Status**: Production Ready with Clean Architecture ✅  
**Last Updated**: July 12, 2025

### 🎉 Recent Achievements (2025-07 Refactoring)
- ✅ **55% code reduction** through intelligent consolidation
- ✅ **Modular architecture** with 7 clean packages
- ✅ **Scripts reorganized** from 40+ files to 20 organized tools
- ✅ **Zero breaking changes** - All functionality preserved
- ✅ **Protected cli_v2.py** - Critical vocabulary generation unchanged
- ✅ **Enhanced monitoring** - Live dashboard and health checks
- ✅ **7 export formats** - TSV, CSV, JSON, Anki, Markdown, HTML, PDF
- ✅ **Code consolidation completed** - Database managers, rate limiters, circuit breakers unified
- ✅ **Documentation reorganized** - Structured into logical subdirectories

See [docs/refactoring/REFACTORING_COMPLETE.md](./docs/refactoring/REFACTORING_COMPLETE.md) for full details.

## ✨ Key Features

### 🚀 Core Capabilities
- **Two-Stage AI Processing**: Semantic analysis → Flashcard generation
- **Concurrent Processing**: Up to 50x faster with parallel API calls
- **Permanent Caching**: Never repeat the same API call twice
- **Professional CLI**: 40+ commands with rich terminal UI
- **Multiple Export Formats**: TSV, JSON, Anki, PDF
- **Real-time Monitoring**: Live dashboard for processing operations
- **Automation Ready**: Watch mode, scheduling, and integrations

### 💡 Advanced Features
- **Configuration System**: YAML files + environment variables
- **Plugin Architecture**: Extend functionality with custom plugins
- **Error Recovery**: Comprehensive error handling with suggestions
- **Security Auditing**: Built-in security checks and optimization
- **Interactive Mode**: REPL for exploratory usage
- **Third-party Integrations**: Notion, Anki-Connect, Google Sheets

## 🛠️ Technology Stack

### Core Technologies
- **Rust**: High-performance data processing and orchestration
- **Python**: Enhanced CLI, API client, and integrations
- **SQLite**: Persistent caching and queue management
- **PyO3**: Rust-Python interoperability

### Key Libraries
- **CLI**: typer, rich, click
- **Async**: httpx, asyncio, aiofiles
- **Data**: pydantic, pyyaml, pandas
- **Monitoring**: watchdog, schedule

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/RexRenatus/korean-flashcard-pipeline.git
cd korean-flashcard-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Build Rust components (optional)
cargo build --release
```

### 2. Configuration

```bash
# Initialize configuration
python -m flashcard_pipeline init

# Set your API key
export OPENROUTER_API_KEY="your-api-key-here"
# Or add to .env file
```

### 3. Basic Usage

```bash
# Process vocabulary with default settings
python -m flashcard_pipeline process input.csv

# Process with concurrent requests (faster)
python -m flashcard_pipeline process input.csv --concurrent 20

# Process first 100 words
python -m flashcard_pipeline process input.csv --limit 100 --output korean_flashcards.tsv
```

## 📚 Documentation

- **[CLI User Guide](./docs/user/CLI_GUIDE.md)** - Comprehensive guide to all CLI features
- **[Quick Start Tutorial](./docs/user/QUICK_START.md)** - Get started in 5 minutes
- **[API Documentation](./docs/api/README.md)** - API specifications and contracts
- **[Architecture Overview](./docs/architecture/README.md)** - System design and architecture
- **[Developer Guide](./docs/developer/README.md)** - Contributing and development

## 📝 Cache Format Examples

The pipeline uses a sophisticated caching system to avoid repeating expensive API calls. Cache files are stored in JSON format with complete processing results:

### Stage 2 Cache Structure
```json
{
  "vocabulary_item": {
    "position": 714,
    "term": "문을",
    "type": "noun",
    "nuance_level": null
  },
  "stage1_result": {
    "term_number": 714,
    "term": "문을[mu.nɯl]",
    "ipa": "[mu.nɯl]",
    "pos": "noun",
    "primary_meaning": "door (with object particle 을)",
    "other_meanings": "gate, entrance, family lineage, academic field",
    "metaphor": "A heavy wooden barrier that swings open with a satisfying creak",
    "comparison": {
      "vs": "창문[tʃʰaŋ.mun] (window)",
      "nuance": "문 is for passage through; 창문 is for looking through and light"
    },
    "homonyms": [
      {
        "hanja": "門",
        "reading": "문[mun]",
        "meaning": "door, gate, entrance",
        "differentiator": "most common meaning - physical door"
      }
    ]
  },
  "response": {
    "rows": [
      {
        "position": 1,
        "term": "문을[mu.nɯl]",
        "term_number": 714,
        "tab_name": "Scene",
        "front": "Stepping through another portal, you enter the old traditional house entrance. What single architectural feature demands your full attention?",
        "back": "A heavy wooden barrier stands before you, its weathered surface marked by decades of use while brass hinges gleam in filtered sunlight...",
        "tags": "term:문을,pos:noun,card:Scene,concept:metaphor,metaphor:wooden_barrier"
      }
    ]
  },
  "tokens": 17661,
  "cached_at": "2025-07-10T23:48:49.019829"
}
```

### Cache Benefits
- **Permanent Storage**: Never lose expensive AI-generated content
- **Token Tracking**: Monitor API usage and costs
- **Resume Capability**: Restart processing from where you left off
- **Cache Hit Rate**: Typically 60-80% on repeated vocabularies
- **Content Integrity**: Complete stage1 + stage2 results preserved

## 🎮 CLI Overview

The enhanced CLI provides a professional command-line experience:

```bash
# Core Commands
flashcard-pipeline init                    # Initialize configuration
flashcard-pipeline process input.csv       # Process vocabulary
flashcard-pipeline config --list           # View configuration

# Import/Export
flashcard-pipeline import csv data.csv     # Import vocabulary
flashcard-pipeline export anki output.apkg # Export to Anki

# Database Operations
flashcard-pipeline db migrate              # Run migrations
flashcard-pipeline db stats                # View statistics

# Monitoring & Analysis
flashcard-pipeline monitor                 # Live dashboard
flashcard-pipeline cache stats             # Cache statistics
flashcard-pipeline test connection         # Test API connection

# Automation
flashcard-pipeline watch ./input           # Watch for new files
flashcard-pipeline schedule "0 9 * * *"    # Schedule processing

# Advanced
flashcard-pipeline interactive             # REPL mode
flashcard-pipeline audit                   # Security audit
flashcard-pipeline optimize                # Performance tuning
```

## 📊 Performance

- **Sequential Processing**: ~1-2 items/second
- **Concurrent Processing**: Up to 50 items/second (with 50 workers)
- **Cache Hit Rate**: Typically 60-80% on repeated vocabularies
- **Memory Usage**: <200MB for 10,000 items
- **Database Size**: ~1MB per 1,000 cached items

## 🔧 Configuration

Create `.flashcard-config.yml` for custom settings:

```yaml
api:
  provider: openrouter
  model: anthropic/claude-3.5-sonnet
  timeout: 30

processing:
  max_concurrent: 20
  batch_size: 100
  rate_limit:
    requests_per_minute: 60
    tokens_per_minute: 90000

cache:
  enabled: true
  path: .cache/flashcards
  ttl_days: 30

output:
  default_format: tsv
  anki:
    deck_name: "Korean Vocabulary"
    tags: ["korean", "ai-generated"]
```

## 🧪 Testing

The project includes comprehensive test coverage across all phases:

- **Phase 1 Tests**: ✅ 100% pass rate (67/67 tests)
- **Phase 2 Tests**: ✅ 100% pass rate (85/85 tests)
- **Overall Test Coverage**: 90%+

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flashcard_pipeline

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run phase-specific tests
python tests/unit/phase1/run_phase1_tests.py
python tests/unit/phase2/run_phase2_tests.py
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Run linting
ruff check .
black --check .

# Run type checking
mypy src/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenRouter** for providing access to Claude Sonnet 4
- **Anthropic** for Claude's exceptional language understanding
- **Rich** and **Typer** for the beautiful CLI experience
- The Korean language learning community for inspiration

## 📞 Support

- **Documentation**: [Full documentation](./docs/)
- **Issues**: [GitHub Issues](https://github.com/RexRenatus/korean-flashcard-pipeline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RexRenatus/korean-flashcard-pipeline/discussions)
- **Portfolio**: [RexRenatus.io](https://rexrenatus.github.io/RexRenatus.io/)
- **Instagram**: [@devi.nws](https://www.instagram.com/devi.nws/)

---

<div align="center">
  Made with ❤️ for Korean language learners everywhere
  
  <br><br>
  
  **"In the beginning, a thought begat a question,  
  a question begat an idea,  
  an idea begat a theory,  
  and the theory begat the obsession"**
  
  Built with 💜 in the pursuit of infinite knowledge
</div>