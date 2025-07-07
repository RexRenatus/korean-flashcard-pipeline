# Change Log

**Last Updated**: 2025-01-07

This document tracks all significant changes to the Korean Language Flashcard Pipeline project.

## [Current] - 2025-01-07

### Added
- New "Cognitive Process and Structured Thinking" rule set (think-1 through think-12)
  - Mandates XML-formatted thinking for complex problem-solving
  - Introduces step-by-step breakdown with 20-step budget
  - Implements reward-based quality assessment (0.0-1.0 scale)
  - Requires reflection and strategy adjustment based on intermediate results

### Changed
- Separated change log from CLAUDE.md into dedicated CHANGELOG.md file
- Added new documentation rule (doc-11) for maintaining separate change logs

## [Project Pivot] - 2025-01-07

### Changed
- **Project Pivot**: Transformed from Notion Learning System to Korean Language Flashcard Pipeline
- Updated project overview for AI-powered flashcard generation
- Modified project structure for Rust/Python implementation
- Updated documentation references for API and database schemas
- Adjusted phase definitions for technical implementation
- Added development commands for Rust and Python workflows
- Maintained all Master Rules Reference sections intact

## [Initial Rules] - 2025-01-05

### Added
- **Pre-Execution Planning rule set** (plan-1 through plan-10)
  - Ensures rule compliance verification before any file operation
  - Emphasizes planning and precondition validation
  - Promotes atomic, trackable task breakdown
  
- **Backward Compatibility and Issue Resolution rule set** (compat-1 through compat-10)
  - Ensures proper handling when missing components are discovered in later phases
  - Mandates updating all previous documentation to prevent future issues
  - Creates systematic approach for retroactive fixes
  - Example: Missing relations between Goals↔Actions and Subjects↔Sessions discovered in Phase 3
  
- **Git and GitHub Operations rule set** (git-1 through git-10)
  - Provides fallback strategies for SSH authentication issues
  - Documents GitHub CLI token authentication method for push operations
  - Ensures proper repository creation and remote management
  - Example: Used gh auth token method when deploy key authentication failed
  
- **README Maintenance rule set** (readme-1 through readme-10)
  - Ensures README.md stays current with project status
  - Mandates updates for phase completions and new features
  - Maintains accuracy of quick start guides and troubleshooting
  - Validates internal links and project structure documentation

## [Foundation] - 2025-01-04

### Added
- Initial CLAUDE.md created with comprehensive rule sets
- **Implemented XML formatting for all rules**
- Added Master Rules Reference section with:
  - Documentation Standards
  - Development Process
  - File Management
  - Task Management
  - Security Compliance
  - Process Execution
  - Core Operational Principles
  - Design Philosophy (KISS, YAGNI, SOLID)
  - System Extension
  - Quality Assurance
  - Testing & Simulation
  - Change Tracking & Governance

### Established
- Modular documentation pattern
- Project structure and guidelines
- Critical documentation section
- Change tracking system
- Comprehensive AI operating principles:
  - Code Quality Standards (error handling, docstrings, preconditions)
  - Documentation Protocols (synchronization, consistency, executability)
  - Task Management Rules (clarity, assignment, dependencies)
  - Security Compliance Guidelines (no hardcoded credentials, input validation)
  - Process Execution Requirements (logging, resource limits, retry logic)
  - Core Operational Principles (evidence-based decisions, traceability)
  - Design Philosophy (KISS, YAGNI, SOLID principles)
  - System Extension Guidelines (compatibility, testing, versioning)
  - Quality Assurance Procedures (review requirements, user clarity)
  - Testing & Simulation Rules (coverage, CI/CD, regression tests)
  - Change Tracking & Governance (audit trails, rollback plans)

## Version Format

This project uses date-based versioning:
- Major changes: New dated entry with descriptive header
- Minor changes: Listed under the current date
- All changes include clear descriptions of what was modified

## Categories

- **Added**: New features or documentation
- **Changed**: Updates to existing functionality
- **Deprecated**: Features marked for removal
- **Removed**: Features that have been removed
- **Fixed**: Bug fixes
- **Security**: Security-related changes