# Claude Code Review Scripts

## Overview

These scripts provide production-level pre-task and post-task compliance checking for Claude Code operations. They ensure that all operations follow the rules defined in `claude.md` or `CLAUDE.md` with enhanced safety features.

## Scripts

### Standard Scripts

#### pre_task_review.sh
Runs before task execution to check:
- Rule compliance based on tool type
- Dangerous command patterns
- Task complexity analysis
- Required file tracking (MASTER_TODO.md, PROJECT_JOURNAL.md)

#### post_task_review.sh
Runs after task completion to verify:
- Rule compliance verification
- File modification tracking
- Code formatting (if formatters available)
- Test execution (if tests available)
- Performance metrics collection

### Enhanced Safety Scripts (Production Level)

#### pre_task_review_enhanced.sh
Advanced pre-task safety checking with:
- **Hard blocks** that cannot be bypassed even with skip-permissions
- Protected directory lists (/, /home, /etc, etc.)
- Sensitive file pattern detection (*.env, *.key, etc.)
- Blacklisted commands (fork bombs, filesystem destruction)
- API key exposure prevention
- Enhanced security logging
- Concurrent execution prevention with file locking

#### post_task_review_enhanced.sh
Comprehensive post-task validation with:
- Security audit for exposed secrets
- File permission checks
- Sensitive data exposure detection
- Enhanced compliance tracking
- Security violation logging
- Real-time performance metrics
- Automated code quality checks

## dangerously-skip-permissions Flag

Both scripts support a `dangerously_skip_permissions` flag that allows bypassing certain permission checks. This should be used with extreme caution.

### How it works

When the flag is set to `true` in the input JSON:
```json
{
  "tool_name": "Bash",
  "command": "some_command",
  "dangerously_skip_permissions": true
}
```

The scripts will:
1. Still detect and report violations
2. Log the skip-permissions usage to an audit file
3. Allow the operation to proceed despite violations
4. Show warnings that the flag is active

### Audit Trail

All skip-permissions usage is logged to:
- `$HOME/.claude/hook_data/skip_permissions_audit.log`

The audit log includes:
- Timestamp
- Tool name
- File path (if applicable)
- Violations that were bypassed
- User who invoked the operation

### When to use

The `dangerously-skip-permissions` flag should only be used when:
1. You understand the risks of bypassing safety checks
2. The operation is necessary and safe despite triggering violations
3. You have documented why the bypass is needed
4. You accept responsibility for any consequences

### Testing

Use the included `test_skip_permissions.sh` script to verify the flag handling:
```bash
./test_skip_permissions.sh
```

## Configuration

The scripts use these environment variables:
- `HOME`: User home directory for storing logs and tracking data
- `USER`: Current username for audit logging

## Logging

All operations are logged to:
- `$HOME/.claude/hook_data/operations.log` - General operations log
- `$HOME/.claude/hook_data/performance.log` - Performance metrics
- `$HOME/.claude/hook_data/pre_review_*.log` - Daily pre-review logs
- `$HOME/.claude/hook_data/compliance/violations_*.log` - Violation logs by session

## Exit Codes

- `0`: Success (pre_task_review.sh when checks pass)
- `1`: Failure (pre_task_review.sh when violations block operation)
- `2`: Review required (post_task_review.sh always exits with 2)

## Dependencies

- `jq`: JSON parsing
- `sed`: Text processing
- `grep`: Pattern matching
- `mkdir`: Directory creation
- `flock`: Lock file handling

Optional for enhanced features:
- `black`: Python formatting
- `prettier`: JavaScript/TypeScript formatting
- `pytest`: Python testing
- `npm`: JavaScript testing

## Enhanced Safety Features

### Security Violations That Cannot Be Bypassed

The enhanced scripts include **hard blocks** that will prevent operations even with `dangerously-skip-permissions`:

1. **Protected Directory Destruction**
   - Cannot delete system directories (/, /home, /etc, /usr, etc.)
   - Cannot delete project-critical directories (.git, node_modules, venv)

2. **API Key Protection**
   - Cannot expose API keys from .env files
   - Cannot send environment variables over network
   - Cannot log sensitive credentials

3. **Blacklisted Commands**
   - Fork bombs: `:(){:|:&};:`
   - Filesystem destruction: `rm -rf /`
   - Disk operations: `dd if=/dev/zero`, `mkfs`, `fdisk`
   - Direct device writes: `> /dev/sda`

### Build Automation Features

The project now includes automated build capabilities:

#### auto_build.sh
Complete build automation script that:
- Checks system dependencies
- Sets up Python virtual environment
- Installs all dependencies (Python & Rust)
- Runs code formatters
- Executes linters with auto-fix
- Runs full test suite
- Generates build reports

Run with: `./scripts/auto_build.sh`

#### Enhanced Hook Configuration
The `.claude/settings.json` can be configured to:
- Auto-install dependencies when changed
- Run linters on file save
- Execute tests in background
- Provide build status updates
- Clean up temporary files on session end

## Security Considerations

1. The scripts validate JSON input to prevent injection attacks
2. File paths are sanitized and validated
3. Command patterns are checked against blacklists
4. All operations are logged for audit purposes
5. Security violations are logged separately
6. Concurrent execution is prevented with file locks
7. Sensitive file access is monitored and logged

## Testing

### Test Enhanced Safety
Run the comprehensive safety test:
```bash
./scripts/review/test_enhanced_safety.sh
```

This tests:
- Hard blocks for protected directories
- API key exposure prevention
- Blacklisted command blocking
- Skip-permissions functionality
- Security audit features

## Best Practices

1. **Always use enhanced scripts for production**
2. Never use `dangerously-skip-permissions` without valid reason
3. Review security audit logs regularly: `~/.claude/hook_data/security_audit.log`
4. Monitor skip-permissions usage: `~/.claude/hook_data/skip_permissions_audit.log`
5. Keep protected lists updated in scripts
6. Run build automation regularly to catch issues early
7. Document any security exceptions needed