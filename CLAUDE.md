# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 IMPORTANT: Automated Rule Enforcement Active

**Most rules in this file are now automatically enforced through hooks in `.claude/settings.json`**
- Virtual environment activation is automatic
- Security checks prevent dangerous operations  
- Documentation reminders are provided
- Test coverage is monitored
- Code quality is validated

**For day-to-day work, refer to `CLAUDE_STREAMLINED.md` for essential guidance without the rule details.**

## 🎯 Project Overview

**Project**: Korean Language Flashcard Pipeline  
**Purpose**: AI-powered flashcard generation system using OpenRouter API with Claude Sonnet 4 for creating nuanced Korean language learning materials  
**Status**: 🚧 Phase 1 - Design & Architecture (Active)  
**Tech Stack**: Rust (core pipeline), Python (API client & integrations)

## 📚 CRITICAL DOCUMENTATION PATTERN

<critical-documentation-pattern>
  <rule>ALWAYS ADD IMPORTANT DOCS HERE! When you create or discover:</rule>
  <action type="architecture">Architecture diagrams → Add reference path here</action>
  <action type="database">Database schemas → Add reference path here</action>
  <action type="problem">Problem solutions → Add reference path here</action>
  <action type="setup">Setup guides → Add reference path here</action>
  <reason>This prevents context loss! Update this file IMMEDIATELY when creating important docs.</reason>
</critical-documentation-pattern>

## 🗺️ Key Documentation References

### Project Overview
- **README**: `/README.md` 📖 - Project overview and quick start guide
- **API Architecture**: `/API_ARCHITECTURE.md` 🏗️ - System architecture and API design
- **Database Schema**: `/DATABASE_SCHEMA.md` 🗄️ - SQLite database design

### Planning & Architecture
- **Project Index**: `/PROJECT_INDEX.md` 📑 - Complete file map
- **Master Todo List**: `/planning/MASTER_TODO.md` ✅ - Task tracking
- **Phase Roadmap**: `/planning/PHASE_ROADMAP.md` 🗺️ - Implementation phases
- **Architecture Decisions**: `/planning/ARCHITECTURE_DECISIONS.md` 🏛️ - Key choices

### Phase 1 - Design & Architecture (Active)
- **System Design**: `/Phase1_Design/SYSTEM_DESIGN.md` 🔧 - Core architecture
- **API Specifications**: `/Phase1_Design/API_SPECIFICATIONS.md` 📋 - API endpoints and contracts
- **Database Design**: `/Phase1_Design/DATABASE_DESIGN.md` 🗄️ - Detailed schema design
- **Integration Design**: `/Phase1_Design/INTEGRATION_DESIGN.md` 🔌 - OpenRouter integration
- **Pipeline Design**: `/Phase1_Design/PIPELINE_DESIGN.md` 🔄 - Two-stage processing flow

### Project Management
- **Master Todo**: `/planning/MASTER_TODO.md` ✅ - Always keep updated!
- **Project Journal**: `/planning/PROJECT_JOURNAL.md` 📖 - Step-by-step history
- **Phase Roadmap**: `/planning/PHASE_ROADMAP.md` 🗺️ - Implementation plan
- **Change Log**: `/CHANGELOG.md` 📝 - Project change history

## 🛠️ Development Guidelines

### Core Principles

<core-principles>
  <principle id="1" name="Pseudocode First">Complete ALL design before Notion implementation</principle>
  <principle id="2" name="Modular Documentation">Use hub-and-spoke pattern, not monolithic files</principle>
  <principle id="3" name="Phase Gates">Complete each phase fully before moving to next</principle>
  <principle id="4" name="Test Everything">Each component must have validation criteria</principle>
</core-principles>

### Documentation Rules

<documentation-rules>
  <rule priority="normal">Update PROJECT_INDEX.md when adding new files</rule>
  <rule priority="normal">Add references to this file for critical docs</rule>
  <rule priority="normal">Use descriptive file names with CAPS for visibility</rule>
  <rule priority="normal">Include "Last Updated" dates on all docs</rule>
  <rule priority="critical">Update MASTER_TODO.md after completing ANY task</rule>
  <rule priority="critical">Add entries to PROJECT_JOURNAL.md for significant progress</rule>
  <rule priority="normal">Create flowcharts for complex processes using Mermaid syntax</rule>
  <rule priority="mandatory">
    Add "Session Summary" to PROJECT_JOURNAL.md at end of each work session including:
    - What was accomplished
    - Key metrics (files created, time spent, etc.)
    - Where to continue next session
    - Specific next steps with references
  </rule>
</documentation-rules>

### Project Structure
```
/Phase1_Design/        # Architecture & design docs
/Phase2_Core/          # Rust core implementation
/Phase3_API/           # Python API client
/Phase4_Pipeline/      # Integration & pipeline
/Phase5_Testing/       # Testing & validation
/src/                  # Source code (Rust & Python)
/tests/                # Test suites
/docs/                 # Technical documentation
/planning/             # Project management
/migrations/           # Database migrations
```

## 🔄 Current Phase Status

**Phase 1: Design & Architecture** ✅ COMPLETE
**Phase 2: Core Implementation (Rust)** ✅ COMPLETE
**Phase 3: API Client (Python)** ✅ COMPLETE
**Phase 4: Pipeline Integration** ✅ COMPLETE
**Phase 5: Testing & Validation** ✅ COMPLETE
**Phase 6: Production Implementation** ✅ COMPLETE

**Project Status: PRODUCTION READY (v1.0.0)**

### Final Test Results:
- ✅ Phase 1 Tests: 100% pass rate (67/67 tests)
- ✅ Phase 2 Tests: 100% pass rate (85/85 tests)
- ✅ Integration Testing: Complete
- ✅ Performance Testing: Complete
- ✅ End-to-End Testing: Complete
- ✅ Overall Test Coverage: 90%+

**All phases complete. The project is ready for production deployment.**

## 🚀 Quick Commands

```bash
# Rust development
cargo build                    # Build Rust components
cargo test                     # Run Rust tests
cargo run --bin pipeline       # Run the pipeline

# Python development
python -m venv venv           # Create virtual environment
source venv/bin/activate      # Activate venv (Linux/Mac)
pip install -r requirements.txt # Install dependencies
python -m pytest              # Run Python tests

# Database operations
sqlite3 pipeline.db           # Access database
python scripts/migrate.py     # Run migrations

# Project management
cat planning/MASTER_TODO.md   # Check current progress
cat planning/PHASE_ROADMAP.md # Review phase roadmap
```

---

## 📐 Master Rules Reference

**This section defines mandatory operating principles for all AI instances working on this project. It ensures consistent behaviour, robust execution, and secure collaboration across all tasks and phases.**

<master-rules>
  <rule-set name="Documentation Standards">
    <rule id="doc-1" priority="critical">All rules must be enclosed in XML format</rule>
    <rule id="doc-2" priority="critical">Update MASTER_TODO.md after ANY task completion</rule>
    <rule id="doc-3" priority="critical">Add PROJECT_JOURNAL.md entries for significant progress</rule>
    <rule id="doc-4" priority="mandatory">Create session summaries at end of each work session</rule>
    <rule id="doc-5" priority="normal">Use Mermaid syntax for flowcharts</rule>
    <rule id="doc-6" priority="critical">Documentation must be synchronized with code changes—no outdated references</rule>
    <rule id="doc-7" priority="normal">Markdown files must use consistent heading hierarchies and section formats</rule>
    <rule id="doc-8" priority="critical">Code snippets in documentation must be executable, tested, and reflect real use cases</rule>
    <rule id="doc-9" priority="mandatory">Each doc must clearly outline: purpose, usage, parameters, and examples</rule>
    <rule id="doc-10" priority="normal">Technical terms must be explained inline or linked to a canonical definition</rule>
    <rule id="doc-11" priority="mandatory">Maintain CHANGELOG.md separately from CLAUDE.md to keep file sizes manageable</rule>
  </rule-set>
  
  <rule-set name="Development Process">
    <rule id="dev-1" priority="critical">Complete pseudocode before implementation</rule>
    <rule id="dev-2" priority="critical">Pass phase gates before proceeding</rule>
    <rule id="dev-3" priority="normal">Test every component thoroughly</rule>
    <rule id="dev-4" priority="normal">Document limitations discovered</rule>
    <rule id="dev-5" priority="critical">All scripts must implement structured error handling with specific failure modes</rule>
    <rule id="dev-6" priority="mandatory">Every function must include a concise, purpose-driven docstring</rule>
    <rule id="dev-7" priority="critical">Scripts must verify preconditions before executing critical or irreversible operations</rule>
    <rule id="dev-8" priority="mandatory">Long-running operations must implement timeout and cancellation mechanisms</rule>
    <rule id="dev-9" priority="critical">When implementing Notion databases, prefer formulas over rollups when possible for reliability</rule>
    <rule id="dev-10" priority="mandatory">Use formula-based approaches for calculations that can be self-contained</rule>
    <rule id="dev-11" priority="critical">Document formula alternatives when Notion limitations require workarounds</rule>
  </rule-set>
  
  <rule-set name="File Management">
    <rule id="file-1" priority="normal">Update PROJECT_INDEX.md when adding files</rule>
    <rule id="file-2" priority="normal">Use CAPS for important file names</rule>
    <rule id="file-3" priority="normal">Include "Last Updated" dates</rule>
    <rule id="file-4" priority="critical">Reference critical docs in CLAUDE.md</rule>
    <rule id="file-5" priority="critical">File and path operations must verify existence and permissions before granting access</rule>
  </rule-set>

  <rule-set name="Task Management">
    <rule id="task-1" priority="critical">Tasks must be clear, specific, and actionable—avoid ambiguity</rule>
    <rule id="task-2" priority="mandatory">Every task must be assigned a responsible agent, explicitly tagged</rule>
    <rule id="task-3" priority="mandatory">Complex tasks must be broken into atomic, trackable subtasks</rule>
    <rule id="task-4" priority="critical">No task may conflict with or bypass existing validated system behaviour</rule>
    <rule id="task-5" priority="critical">Security-related tasks must undergo mandatory review by a designated reviewer agent</rule>
    <rule id="task-6" priority="mandatory">Agents must update task status and outcomes in the shared task file</rule>
    <rule id="task-7" priority="critical">Dependencies between tasks must be explicitly declared</rule>
    <rule id="task-8" priority="mandatory">Agents must escalate ambiguous, contradictory, or unscoped tasks for clarification</rule>
  </rule-set>

  <rule-set name="Security Compliance">
    <rule id="sec-1" priority="critical">Hardcoded credentials are strictly forbidden—use secure storage mechanisms</rule>
    <rule id="sec-2" priority="critical">All inputs must be validated, sanitised, and type-checked before processing</rule>
    <rule id="sec-3" priority="critical">Avoid using eval, unsanitised shell calls, or any form of command injection vectors</rule>
    <rule id="sec-4" priority="mandatory">File and process operations must follow the principle of least privilege</rule>
    <rule id="sec-5" priority="mandatory">All sensitive operations must be logged, excluding sensitive data values</rule>
    <rule id="sec-6" priority="critical">Agents must check system-level permissions before accessing protected services or paths</rule>
  </rule-set>

  <rule-set name="Process Execution">
    <rule id="proc-1" priority="mandatory">Agents must log all actions with appropriate severity (INFO, WARNING, ERROR, etc.)</rule>
    <rule id="proc-2" priority="critical">Any failed task must include a clear, human-readable error report</rule>
    <rule id="proc-3" priority="mandatory">Agents must respect system resource limits, especially memory and CPU usage</rule>
    <rule id="proc-4" priority="normal">Long-running tasks must expose progress indicators or checkpoints</rule>
    <rule id="proc-5" priority="mandatory">Retry logic must include exponential backoff and failure limits</rule>
  </rule-set>

  <rule-set name="Core Operational Principles">
    <rule id="core-1" priority="critical">Agents must never use mock, fallback, or synthetic data in production tasks</rule>
    <rule id="core-2" priority="mandatory">Error handling logic must be designed using test-first principles</rule>
    <rule id="core-3" priority="critical">Agents must always act based on verifiable evidence, not assumptions</rule>
    <rule id="core-4" priority="critical">All preconditions must be explicitly validated before any destructive or high-impact operation</rule>
    <rule id="core-5" priority="mandatory">All decisions must be traceable to logs, data, or configuration files</rule>
  </rule-set>

  <rule-set name="Design Philosophy">
    <rule id="design-1" priority="mandatory" principle="KISS">Solutions must be straightforward and easy to understand</rule>
    <rule id="design-2" priority="mandatory" principle="KISS">Avoid over-engineering or unnecessary abstraction</rule>
    <rule id="design-3" priority="critical" principle="KISS">Prioritise code readability and maintainability</rule>
    <rule id="design-4" priority="mandatory" principle="YAGNI">Do not add speculative features or future-proofing unless explicitly required</rule>
    <rule id="design-5" priority="mandatory" principle="YAGNI">Focus only on immediate requirements and deliverables</rule>
    <rule id="design-6" priority="normal" principle="YAGNI">Minimise code bloat and long-term technical debt</rule>
    <rule id="design-7" priority="critical" principle="SRP">Single Responsibility—each module or function should do one thing only</rule>
    <rule id="design-8" priority="mandatory" principle="OCP">Open-Closed—software entities should be open for extension but closed for modification</rule>
    <rule id="design-9" priority="mandatory" principle="LSP">Liskov Substitution—derived classes must be substitutable for their base types</rule>
    <rule id="design-10" priority="normal" principle="ISP">Interface Segregation—prefer many specific interfaces over one general-purpose interface</rule>
    <rule id="design-11" priority="mandatory" principle="DIP">Dependency Inversion—depend on abstractions, not concrete implementations</rule>
  </rule-set>

  <rule-set name="System Extension">
    <rule id="ext-1" priority="critical">All new agents must conform to existing interface, logging, and task structures</rule>
    <rule id="ext-2" priority="mandatory">Utility functions must be unit tested and peer reviewed before shared use</rule>
    <rule id="ext-3" priority="critical">All configuration changes must be reflected in the system manifest with version stamps</rule>
    <rule id="ext-4" priority="mandatory">New features must maintain backward compatibility unless justified and documented</rule>
    <rule id="ext-5" priority="normal">All changes must include a performance impact assessment</rule>
  </rule-set>

  <rule-set name="Quality Assurance">
    <rule id="qa-1" priority="critical">A reviewer agent must review all changes involving security, system config, or agent roles</rule>
    <rule id="qa-2" priority="mandatory">Documentation must be proofread for clarity, consistency, and technical correctness</rule>
    <rule id="qa-3" priority="mandatory">User-facing output (logs, messages, errors) must be clear, non-technical, and actionable</rule>
    <rule id="qa-4" priority="normal">All error messages should suggest remediation paths or diagnostic steps</rule>
    <rule id="qa-5" priority="critical">All major updates must include a rollback plan or safe revert mechanism</rule>
  </rule-set>

  <rule-set name="Testing and Simulation">
    <rule id="test-1" priority="critical">All new logic must include unit and integration tests</rule>
    <rule id="test-2" priority="critical">Simulated or test data must be clearly marked and never promoted to production</rule>
    <rule id="test-3" priority="mandatory">All tests must pass in continuous integration pipelines before deployment</rule>
    <rule id="test-4" priority="normal">Code coverage should exceed defined thresholds (e.g. 85%)</rule>
    <rule id="test-5" priority="mandatory">Regression tests must be defined and executed for all high-impact updates</rule>
    <rule id="test-6" priority="normal">Agents must log test outcomes in separate test logs, not production logs</rule>
  </rule-set>

  <rule-set name="Change Tracking and Governance">
    <rule id="gov-1" priority="critical">All configuration or rule changes must be documented in the system manifest and changelog</rule>
    <rule id="gov-2" priority="mandatory">Agents must record the source, timestamp, and rationale when modifying shared assets</rule>
    <rule id="gov-3" priority="mandatory">All updates must increment the internal system version where applicable</rule>
    <rule id="gov-4" priority="critical">A rollback or undo plan must be defined for every major change</rule>
    <rule id="gov-5" priority="mandatory">Audit trails must be preserved for all task-modifying operations</rule>
  </rule-set>

  <rule-set name="Cognitive Process and Structured Thinking">
    <rule id="think-1" priority="mandatory">Use XML tags to structure complex problem-solving and decision-making processes</rule>
    <rule id="think-2" priority="mandatory">Use &lt;thinking&gt; tags to explore different approaches and viewpoints before responding</rule>
    <rule id="think-3" priority="mandatory">Use &lt;step&gt; tags to break down solutions with a 20 step budget (request more if needed)</rule>
    <rule id="think-4" priority="mandatory">Add &lt;count&gt; tags after each step to track remaining budget</rule>
    <rule id="think-5" priority="critical">Use &lt;reflection&gt; tags to evaluate progress and maintain self-critical analysis</rule>
    <rule id="think-6" priority="mandatory">Rate solution quality with &lt;reward&gt; tags (0.0-1.0 scale)</rule>
    <rule id="think-7" priority="critical">Reward score interpretation: ≥0.8 continue approach, 0.5-0.7 minor adjustments, &lt;0.5 try new approach</rule>
    <rule id="think-8" priority="mandatory">Show all work and calculations explicitly within the structured format</rule>
    <rule id="think-9" priority="mandatory">Explore multiple solutions when possible before settling on final approach</rule>
    <rule id="think-10" priority="critical">Summarize final answer in &lt;answer&gt; tags with clear, actionable conclusions</rule>
    <rule id="think-11" priority="mandatory">End with final reflection and reward score to assess solution quality</rule>
    <rule id="think-12" priority="critical">Adjust strategy based on reward scores and intermediate results throughout the process</rule>
  </rule-set>

  <rule-set name="Pre-Execution Planning">
    <rule id="plan-1" priority="critical">Before ANY file operation, create a mental checklist of applicable rules and verify compliance</rule>
    <rule id="plan-2" priority="critical">For Write operations: First check if file exists, update PROJECT_INDEX.md if new, verify no hardcoded credentials</rule>
    <rule id="plan-3" priority="critical">For Edit operations: Always use Read tool first, preserve exact formatting, verify changes align with project goals</rule>
    <rule id="plan-4" priority="mandatory">Break complex operations into atomic steps that can be individually verified for rule compliance</rule>
    <rule id="plan-5" priority="mandatory">If any rule violation is detected during planning, adjust approach BEFORE execution</rule>
    <rule id="plan-6" priority="critical">Always update tracking files (MASTER_TODO.md, PROJECT_JOURNAL.md) AFTER completing tasks, not before</rule>
    <rule id="plan-7" priority="mandatory">When creating documentation, ensure it includes: purpose, usage, parameters, examples (doc-9)</rule>
    <rule id="plan-8" priority="critical">For database implementations, plan formula-based solutions before considering rollups (dev-9)</rule>
    <rule id="plan-9" priority="mandatory">Document your execution plan in comments or todo items before starting complex tasks</rule>
    <rule id="plan-10" priority="critical">Verify all preconditions are met before executing any operation that modifies files or state</rule>
  </rule-set>

  <rule-set name="Backward Compatibility and Issue Resolution">
    <rule id="compat-1" priority="critical">When discovering missing components in later phases, immediately create a fix document explaining what was missed and why</rule>
    <rule id="compat-2" priority="critical">Update ALL relevant previous phase documentation to include the missing components</rule>
    <rule id="compat-3" priority="mandatory">Create a dedicated FIX or PATCH file that clearly explains: problem identified, solution steps, verification process</rule>
    <rule id="compat-4" priority="critical">Update original implementation guides to prevent future users from encountering the same issue</rule>
    <rule id="compat-5" priority="mandatory">Add warnings or update sections to existing guides highlighting the discovered requirements</rule>
    <rule id="compat-6" priority="critical">Verify that all phases remain compatible after making retroactive changes</rule>
    <rule id="compat-7" priority="mandatory">Document in PROJECT_JOURNAL.md any backward compatibility fixes applied</rule>
    <rule id="compat-8" priority="critical">When relations or dependencies are discovered between phases, update both phases' documentation</rule>
    <rule id="compat-9" priority="mandatory">Create a "Lessons Learned" section in relevant documents to prevent similar oversights</rule>
    <rule id="compat-10" priority="critical">Always test the fix with fresh implementation to ensure it resolves the issue</rule>
  </rule-set>

  <rule-set name="Git and GitHub Operations">
    <rule id="git-1" priority="critical">When pushing to GitHub fails with SSH authentication errors, use GitHub CLI with token authentication as fallback</rule>
    <rule id="git-2" priority="mandatory">For SSH key issues, first test connection with: ssh -T git@github.com</rule>
    <rule id="git-3" priority="critical">If deploy key errors occur, use: gh auth token | git push https://oauth2:$(gh auth token)@github.com/owner/repo.git branch</rule>
    <rule id="git-4" priority="mandatory">Always create repositories using gh CLI when available: gh repo create name --public --source=. --remote=origin</rule>
    <rule id="git-5" priority="normal">Set git identity locally if global config not available: git config user.email and git config user.name</rule>
    <rule id="git-6" priority="critical">Never store credentials in code or commits - use environment variables or secure authentication methods</rule>
    <rule id="git-7" priority="mandatory">Always check git status before committing to ensure correct files are staged</rule>
    <rule id="git-8" priority="critical">Use descriptive commit messages following project conventions with Co-Authored-By attribution</rule>
    <rule id="git-9" priority="mandatory">When remote already exists, remove it first: git remote remove origin before adding new remote</rule>
    <rule id="git-10" priority="normal">Document any Git/GitHub setup issues and solutions in project documentation for future reference</rule>
  </rule-set>

  <rule-set name="README Maintenance">
    <rule id="readme-1" priority="critical">Update README.md whenever completing a major phase or milestone</rule>
    <rule id="readme-2" priority="critical">Keep "Current Status" section accurate with phase progress and completion percentages</rule>
    <rule id="readme-3" priority="mandatory">Update "Known Limitations" when discovering new Notion constraints or workarounds</rule>
    <rule id="readme-4" priority="critical">Ensure "Quick Start" instructions remain accurate and tested with each major change</rule>
    <rule id="readme-5" priority="mandatory">Update "Project Structure" when adding new directories or reorganizing files</rule>
    <rule id="readme-6" priority="critical">Keep "Database Overview" synchronized with actual implementation status</rule>
    <rule id="readme-7" priority="mandatory">Add new features to "Key Features" section when implementing significant functionality</rule>
    <rule id="readme-8" priority="normal">Update version badges and status indicators to reflect current state</rule>
    <rule id="readme-9" priority="critical">Ensure all internal links in README remain valid after file moves or renames</rule>
    <rule id="readme-10" priority="mandatory">Add troubleshooting items when users report common issues</rule>
  </rule-set>

  <rule-set name="Efficient Subagent Utilization">
    <rule id="subagent-1" priority="critical">When facing multiple independent tasks, ALWAYS launch concurrent subagents to maximize efficiency</rule>
    <rule id="subagent-2" priority="critical">For file searches spanning multiple directories, use separate subagents to search in parallel</rule>
    <rule id="subagent-3" priority="mandatory">When analyzing different components or modules, assign each to a dedicated subagent</rule>
    <rule id="subagent-4" priority="critical">For test fixing across multiple test files, launch parallel subagents for each file</rule>
    <rule id="subagent-5" priority="mandatory">Document gathering tasks must use subagents to read multiple files concurrently</rule>
    <rule id="subagent-6" priority="critical">Each subagent must have a clear, specific, and bounded task description</rule>
    <rule id="subagent-7" priority="mandatory">Subagent tasks must include expected output format and success criteria</rule>
    <rule id="subagent-8" priority="critical">Never use subagents for tasks requiring sequential operations or shared state</rule>
    <rule id="subagent-9" priority="mandatory">Aggregate and synthesize subagent results before presenting to user</rule>
    <rule id="subagent-10" priority="critical">For research tasks, use subagents to explore different aspects simultaneously</rule>
    <rule id="subagent-11" priority="mandatory">When fixing similar issues across multiple files, create a template fix for subagents</rule>
    <rule id="subagent-12" priority="critical">Monitor subagent progress and reassign tasks if any subagent fails</rule>
    <rule id="subagent-13" priority="mandatory">Use subagents for parallel validation and testing of independent components</rule>
    <rule id="subagent-14" priority="critical">Batch similar operations together for subagent processing</rule>
    <rule id="subagent-15" priority="mandatory">Document subagent usage patterns in PROJECT_JOURNAL.md for future reference</rule>
  </rule-set>

  <rule-set name="Subagent Task Patterns">
    <rule id="pattern-1" priority="critical">File Search Pattern: Use subagents to search for patterns/keywords across different directories</rule>
    <rule id="pattern-2" priority="critical">Test Fix Pattern: Assign each failing test class to a separate subagent for parallel fixing</rule>
    <rule id="pattern-3" priority="mandatory">Documentation Update Pattern: Use subagents to update related docs simultaneously</rule>
    <rule id="pattern-4" priority="critical">Code Analysis Pattern: Analyze different modules/packages with dedicated subagents</rule>
    <rule id="pattern-5" priority="mandatory">Dependency Check Pattern: Verify dependencies across multiple files using parallel subagents</rule>
    <rule id="pattern-6" priority="critical">Refactoring Pattern: Apply similar refactoring across multiple files with subagents</rule>
    <rule id="pattern-7" priority="mandatory">Validation Pattern: Run different validation checks concurrently with subagents</rule>
    <rule id="pattern-8" priority="critical">Data Collection Pattern: Gather metrics/stats from multiple sources in parallel</rule>
    <rule id="pattern-9" priority="mandatory">Error Investigation Pattern: Investigate different error types with specialized subagents</rule>
    <rule id="pattern-10" priority="critical">Performance Analysis Pattern: Profile different components simultaneously</rule>
  </rule-set>
</master-rules>

---

## 🔧 Automated Hook System

**As of 2025-01-09, most rules are enforced automatically via `.claude/settings.json` hooks:**

### What's Automated:
1. **Virtual Environment**: Python commands auto-activate venv
2. **Security**: Blocks hardcoded credentials and dangerous commands
3. **Testing**: Enforces test creation, coverage targets, and best practices
4. **Documentation**: Reminds about updates to tracking files
5. **Code Quality**: Auto-runs linters and type checkers
6. **Git Operations**: Status checks and commit reminders
7. **Session Management**: Cleanup and summary generation

### What's NOT Automated:
1. Strategic thinking and architecture decisions
2. Complex problem-solving approaches
3. Creative solutions and optimizations
4. Business logic implementation
5. User experience design

### Testing Rules Now Enforced:
- **test-1**: New code requires tests (reminder on file creation)
- **test-2**: Test data validation (checks during test execution)
- **test-3**: CI pipeline integration (test must pass)
- **test-4**: Coverage targets (85% minimum reminder)
- **test-5**: Regression tests for bug fixes
- **test-6**: Separate test logs (handled automatically)

**For streamlined daily use, see `CLAUDE_STREAMLINED.md`**

---

## 🔄 Phase Continuation System

**As of 2025-01-09, intelligent phase continuation is automated via hooks:**

### Automatic Features:
1. **Session Start**: Shows current phase status and next priority tasks
2. **Task Tracking**: Monitors MASTER_TODO.md for uncompleted tasks
3. **Context Restoration**: Displays where last session ended from PROJECT_JOURNAL.md
4. **Priority Suggestions**: Recommends next task based on dependencies
5. **Progress Reports**: Comprehensive status overview at session start
6. **State Persistence**: Saves session state for cross-session continuity

### How It Works:
- **Start Hook**: Runs `phase_continuation_manager.py report` to show current status
- **Continue Hook**: Restores session state and suggests next actions
- **Stop Hook**: Saves current task and next steps for future sessions

### Manual Commands:
```bash
# Get full continuation report
python scripts/phase_continuation_manager.py report

# Check current status
python scripts/phase_continuation_manager.py status

# Get next task suggestion
python scripts/phase_continuation_manager.py suggest

# Save session state
python scripts/phase_continuation_manager.py save "current task" "next step 1" "next step 2"

# Load previous session state
python scripts/phase_continuation_manager.py load
```

---

**Remember**: The hooks handle routine enforcement. Focus on quality code and strategic decisions!