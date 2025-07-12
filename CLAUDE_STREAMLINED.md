# CLAUDE.md (Streamlined Version)

This file provides essential guidance to Claude Code when working with this repository. Most operational rules are now enforced automatically through hooks in `.claude/settings.json`.

## 🎯 Project Overview

**Project**: Korean Language Flashcard Pipeline  
**Purpose**: AI-powered flashcard generation system using OpenRouter API with Claude Sonnet 4  
**Tech Stack**: Rust (core pipeline), Python (API client & integrations)  
**Status**: Phase 6 - Production Implementation 🚧

## 📚 Quick Reference Guide

### Key Documentation
- **Project Status**: `/planning/MASTER_TODO.md` - Current tasks and progress
- **Architecture**: `/docs/architecture/` - System design documents
- **Database**: `/docs/DATABASE_SCHEMA_V2.md` - Current schema
- **API Specs**: `/docs/INGRESS_API_DOCUMENTATION.md` - API endpoints

### Project Structure
```
/src/python/flashcard_pipeline/  # Python implementation
/tests/                          # Test suites
/docs/                          # Technical documentation
/planning/                      # Project management
/migrations/                    # Database migrations
/scripts/                       # Utility scripts
/venv/                         # Python virtual environment
```

## 🔄 Current Phase: Production Implementation

**Active Work**: Phase 6.1.2 - Database Manager Integration
- Creating comprehensive test coverage
- Implementing connection pooling
- Adding retry logic and performance monitoring

## 🛠️ Development Workflow

### Virtual Environment (Automatically Enforced)
All Python commands automatically run in the virtual environment. The hooks handle activation.

### Quick Commands
```bash
# Testing
pytest tests/unit/test_database_manager.py    # Run specific test
pytest --cov=flashcard_pipeline --cov-fail-under=85  # With coverage

# Database
python scripts/migration_runner_v2.py         # Run migrations
python scripts/db_integrity_check.py          # Check database health

# Pipeline
python -m flashcard_pipeline.pipeline_cli     # Run CLI
```

## 📋 Essential Guidelines

### 1. **Testing Requirements** (Enforced by Hooks)
- All new code requires unit tests
- Integration tests for cross-component functionality
- Minimum 85% code coverage target
- Test data must be clearly marked
- Regression tests for all bug fixes

### 2. **Documentation Updates**
The hooks will remind you, but remember to:
- Update `MASTER_TODO.md` after completing tasks
- Add session summaries to `PROJECT_JOURNAL.md`
- Update `README.md` for major milestones
- Keep "Last Updated" dates current

### 3. **Code Quality Standards**
- Python: Enforced via `ruff` and `mypy` (automatic)
- Rust: `cargo check` runs automatically
- All functions need docstrings
- No hardcoded credentials (blocked by hooks)

### 4. **Git Workflow**
- Check `git status` before commits (reminder provided)
- Use descriptive commit messages
- Include Co-Authored-By attribution

## 🚨 Critical Information

### Database Schema Version
Current: v2.0 (Reorganized schema with ingress system)

### API Configuration
- Uses OpenRouter API
- Rate limiting: Implemented with circuit breaker
- Caching: Database-backed with TTL

### Security Notes
- API keys in `.env` file (never commit)
- All inputs validated before processing
- SQL injection protection via parameterized queries

## 🎯 Hook System Overview

The `.claude/settings.json` file implements intelligent automation for:

1. **Pre-execution Checks**
   - Virtual environment activation
   - Security validation
   - File existence verification
   - Credential scanning

2. **Post-execution Actions**
   - Code quality checks
   - Test reminders
   - Documentation updates
   - Coverage reporting

3. **Session Management**
   - Progress tracking
   - Cleanup operations
   - Summary generation

## 📝 What You Still Need to Do Manually

1. **Strategic Decisions**
   - Architecture choices
   - API design decisions
   - Performance optimization strategies

2. **Creative Problem Solving**
   - Complex bug investigations
   - Algorithm design
   - User experience improvements

3. **Project Planning**
   - Task prioritization
   - Milestone planning
   - Resource allocation

## 🔗 External Resources

- OpenRouter API Docs: https://openrouter.ai/docs
- SQLite Best Practices: https://sqlite.org/bestpractice.html
- Python Testing: https://docs.pytest.org/

---

**Remember**: The hooks handle most routine checks and reminders. Focus on writing quality code and making strategic decisions. The system will guide you on the operational details!