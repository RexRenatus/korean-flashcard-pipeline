# Korean Flashcard Pipeline 🇰🇷

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Rust 1.75+](https://img.shields.io/badge/rust-1.75+-orange.svg)](https://www.rust-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](tests/)

An enterprise-grade AI-powered system for generating nuanced Korean language flashcards using Claude Sonnet 4 via OpenRouter API. Features a robust two-stage processing pipeline with comprehensive error handling, caching, and monitoring.

## 🚀 Features

- **Two-Stage AI Processing**: Initial generation followed by refinement for high-quality flashcards
- **Enterprise Architecture**: Circuit breakers, rate limiting, distributed caching
- **Comprehensive Monitoring**: OpenTelemetry integration with detailed metrics
- **Flexible Export**: Multiple formats (Anki, CSV, JSON, Markdown)
- **Production Ready**: Docker support, database migrations, comprehensive testing
- **Modern CLI**: Rich interactive interface with progress tracking

## 📋 Requirements

- Python 3.11+
- Rust 1.75+
- SQLite 3.35+
- Docker (optional, for containerized deployment)
- OpenRouter API key

## 🛠️ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/korean-flashcard-pipeline.git
cd korean-flashcard-pipeline
```

### 2. Set Up Environment

```bash
# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 3. Configure API Access

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenRouter API key
OPENROUTER_API_KEY=your_api_key_here
```

### 4. Initialize Database

```bash
# Run database migrations
python scripts/run_migrations.py
```

### 5. Run the Pipeline

```bash
# Process a vocabulary file
python -m flashcard_pipeline.cli process input.csv --output output.tsv

# Or use the modern CLI
python -m flashcard_pipeline.cli.main --help
```

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and run all services
docker-compose up -d

# Process vocabulary
docker-compose run pipeline process /data/input.csv
```

### Using Standalone Docker

```bash
# Build image
docker build -t korean-flashcard-pipeline .

# Run container
docker run -v $(pwd)/data:/data \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  korean-flashcard-pipeline process /data/input.csv
```

## 📁 Project Structure

```
korean-flashcard-pipeline/
├── src/                      # Source code
│   ├── python/              # Python API client and utilities
│   └── rust/                # Rust core pipeline (future)
├── tests/                   # Test suites
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── performance/        # Performance benchmarks
├── scripts/                 # Utility scripts
│   ├── docker/             # Docker-related scripts
│   ├── data_prep/          # Data preparation tools
│   └── automation/         # CI/CD and automation
├── docker/                  # Docker configuration
│   ├── Dockerfile          # Main application image
│   └── compose/            # Docker Compose files
├── docs/                    # Documentation
│   ├── technical/          # Technical guides
│   ├── api/                # API documentation
│   └── deployment/         # Deployment guides
├── data/                    # Data directory
│   ├── reference/          # Reference data (HSK lists, etc.)
│   ├── test/               # Test fixtures
│   └── cache/              # Cache storage
└── migrations/              # Database migrations
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `DATABASE_URL` | SQLite database path | `sqlite:///pipeline.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CACHE_TTL` | Cache TTL in seconds | `3600` |
| `MAX_RETRIES` | API retry attempts | `3` |
| `RATE_LIMIT` | Requests per minute | `60` |

### Configuration File

Create `config.yaml` for advanced settings:

```yaml
api:
  timeout: 30
  max_concurrent: 5

cache:
  backend: sqlite
  ttl: 3600

monitoring:
  enable_telemetry: true
  export_interval: 60
```

## 📊 Monitoring

### OpenTelemetry Integration

The pipeline includes comprehensive monitoring:

```python
# Enable monitoring
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=flashcard-pipeline
```

### Available Metrics

- API request latency
- Cache hit/miss rates
- Processing throughput
- Error rates by type
- Resource utilization

## 🧪 Testing

### Run All Tests

```bash
# Python tests
pytest

# Rust tests
cargo test

# With coverage
pytest --cov=flashcard_pipeline --cov-report=html
```

### Test Categories

- **Unit Tests**: Component-level testing
- **Integration Tests**: End-to-end workflows
- **Performance Tests**: Load and stress testing
- **Contract Tests**: API compatibility

## 📚 API Documentation

### CLI Commands

```bash
# Process vocabulary
flashcard-cli process <input> [options]

# Check system health
flashcard-cli health

# Export flashcards
flashcard-cli export <format> <input> <output>

# View statistics
flashcard-cli stats
```

### Python API

```python
from flashcard_pipeline import Pipeline, Config

# Initialize pipeline
config = Config.from_env()
pipeline = Pipeline(config)

# Process vocabulary
results = await pipeline.process_file("input.csv")

# Export results
pipeline.export(results, format="anki", output="deck.apkg")
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run linters
ruff check .
mypy src/

# Format code
black src/ tests/
```

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🔒 Security

See [SECURITY.md](SECURITY.md) for security policies and reporting vulnerabilities.

## 📈 Performance

- Processes 1000 words in ~5 minutes
- 90%+ cache hit rate after warm-up
- Handles 60 requests/minute per API key
- Automatic retry with exponential backoff
- Circuit breaker prevents cascade failures

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure `OPENROUTER_API_KEY` is set correctly
2. **Database Locked**: Check for multiple processes accessing SQLite
3. **Rate Limits**: Reduce concurrency or add more API keys
4. **Memory Issues**: Adjust batch sizes in configuration

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
flashcard-cli process input.csv -vvv
```

## 📞 Support

- Issues: [GitHub Issues](https://github.com/yourusername/korean-flashcard-pipeline/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/korean-flashcard-pipeline/discussions)
- Email: support@example.com

---

Made with ❤️ for Korean language learners