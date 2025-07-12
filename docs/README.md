# 📚 Korean Flashcard Pipeline Documentation

Welcome to the comprehensive documentation for the Korean Flashcard Pipeline project. This documentation is organized into several sections to help you find what you need quickly.

## 📖 Documentation Structure

### [User Documentation](./user/)
For end users of the flashcard pipeline:
- **[CLI User Guide](./user/CLI_GUIDE.md)** - Complete guide to all CLI commands and features
- **[Quick Start Guide](./user/QUICK_START.md)** - Get up and running in 5 minutes
- **[FAQ](./user/FAQ.md)** - Frequently asked questions

### [Architecture Documentation](./architecture/)
System design and technical architecture:
- **[API Architecture](./architecture/API_ARCHITECTURE.md)** - System architecture and API design
- **[Database Schema](./architecture/DATABASE_SCHEMA.md)** - SQLite database design
- **[CLI Architecture](./architecture/CLI_ARCHITECTURE.md)** - CLI design principles and structure
- **[System Overview](./architecture/SYSTEM_OVERVIEW.md)** - High-level system architecture

### [Implementation Documentation](./implementation/)
Detailed implementation guides and plans:
- **[CLI Implementation Plan](./implementation/CLI_IMPLEMENTATION_PLAN.md)** - 5-phase CLI implementation
- **[Concurrent Processing Architecture](./implementation/CONCURRENT_PROCESSING_ARCHITECTURE.md)** - Concurrent processing design
- **[Concurrent Implementation Plan](./implementation/CONCURRENT_IMPLEMENTATION_PLAN.md)** - Step-by-step concurrent implementation

### [API Documentation](./api/)
API specifications and integration guides:
- **[OpenRouter Integration](./api/OPENROUTER.md)** - OpenRouter API integration
- **[REST API](./api/REST_API.md)** - Internal REST API documentation
- **[Plugin API](./api/PLUGIN_API.md)** - Plugin development API

### [Developer Documentation](./developer/)
For contributors and developers:
- **[Contributing Guide](./developer/CONTRIBUTING.md)** - How to contribute
- **[Development Setup](./developer/SETUP.md)** - Setting up development environment
- **[Testing Guide](./developer/TESTING.md)** - Running and writing tests
- **[Code Style](./developer/CODE_STYLE.md)** - Code style guidelines

## 🗺️ Quick Navigation

### Getting Started
1. [Installation Guide](./user/QUICK_START.md#installation)
2. [First Time Setup](./user/QUICK_START.md#first-time-setup)
3. [Basic Usage](./user/CLI_GUIDE.md#basic-usage)

### Common Tasks
- [Processing Korean Vocabulary](./user/CLI_GUIDE.md#process)
- [Configuring the Pipeline](./user/CLI_GUIDE.md#configuration)
- [Monitoring Performance](./user/CLI_GUIDE.md#monitoring--analytics)
- [Troubleshooting Issues](./user/CLI_GUIDE.md#troubleshooting)

### Advanced Topics
- [Concurrent Processing](./implementation/CONCURRENT_PROCESSING_ARCHITECTURE.md)
- [Plugin Development](./api/PLUGIN_API.md)
- [Database Optimization](./architecture/DATABASE_SCHEMA.md#optimization)
- [Custom Integrations](./developer/INTEGRATIONS.md)

## 🔄 Recent Updates - 2025-01 Refactoring

The codebase has undergone a comprehensive refactoring achieving:
- **55% code reduction** through intelligent consolidation
- **Modular architecture** with clear separation of concerns
- **Protected cli_v2.py** - The main vocabulary generation script remains unchanged
- **Zero breaking changes** - All existing functionality preserved

See [REFACTORING_COMPLETE.md](../REFACTORING_COMPLETE.md) for details.

## 📋 Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| CLI User Guide | ✅ Complete | 2025-01-07 |
| API Architecture | ✅ Complete | 2025-01-07 |
| Database Schema | ✅ Complete | 2025-01-07 |
| CLI Implementation | ✅ Complete | 2025-01-07 |
| Concurrent Processing | ✅ Complete | 2025-01-07 |
| Refactoring Report | ✅ Complete | 2025-01-11 |
| Scripts Consolidation | ✅ Complete | 2025-01-11 |
| Quick Start Guide | 🚧 In Progress | - |
| Plugin API | 📝 Planned | - |
| Developer Guide | 📝 Planned | - |

## 🔍 Finding Information

### Search by Topic
- **CLI Commands**: See [CLI User Guide](./user/CLI_GUIDE.md)
- **Configuration**: See [Configuration Section](./user/CLI_GUIDE.md#configuration)
- **Architecture**: See [Architecture Docs](./architecture/)
- **Implementation Details**: See [Implementation Docs](./implementation/)

### Search by Task
- **"How do I..."**: Check [User Documentation](./user/)
- **"How does it work..."**: Check [Architecture Documentation](./architecture/)
- **"How was it built..."**: Check [Implementation Documentation](./implementation/)
- **"How can I extend..."**: Check [Developer Documentation](./developer/)

## 📝 Contributing to Documentation

We welcome documentation improvements! Please:
1. Follow the existing format and style
2. Update the table of contents when adding sections
3. Include examples where appropriate
4. Keep language clear and concise

See [Contributing Guide](./developer/CONTRIBUTING.md) for more details.

## 🆘 Need Help?

- Check the [FAQ](./user/FAQ.md) first
- Browse the [CLI User Guide](./user/CLI_GUIDE.md)
- Search existing [GitHub Issues](https://github.com/RexRenatus/korean-flashcard-pipeline/issues)
- Ask in [Discussions](https://github.com/RexRenatus/korean-flashcard-pipeline/discussions)
- Visit our [Portfolio](https://rexrenatus.github.io/RexRenatus.io/)
- Follow on [Instagram](https://www.instagram.com/devi.nws/)

---

*This documentation is part of the Korean Flashcard Pipeline project. For the latest updates, visit the [GitHub repository](https://github.com/RexRenatus/korean-flashcard-pipeline).*