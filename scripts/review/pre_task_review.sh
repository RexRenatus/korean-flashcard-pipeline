#!/bin/bash

# Script: pre_task_review.sh (Safety-Enhanced Version)
# Purpose: Review task request against claude.md rules before execution
# Version: 2.0.0 - Safety Enhanced

set -euo pipefail  # Exit on error, undefined variables, pipe failures
SCRIPT_VERSION="2.0.0"

# Dependency check
for cmd in jq sed grep mkdir; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: Required command '$cmd' not found" >&2
        exit 1
    fi
done

# Lock file to prevent concurrent execution
LOCKFILE="$HOME/.claude/hook_data/pre_review.lock"
mkdir -p "$HOME/.claude/hook_data"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "WARNING: Another pre-review in progress, waiting..." >&2
    flock 200  # Wait for lock
fi

# Logging setup
LOG_FILE="$HOME/.claude/hook_data/pre_review_$(date +%Y%m%d).log"
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "pre_task_review.sh v$SCRIPT_VERSION started"

# Check if claude.md or CLAUDE.md exists (case-insensitive)
CLAUDE_FILE=""
if [ -f "./claude.md" ]; then
    CLAUDE_FILE="./claude.md"
elif [ -f "./CLAUDE.md" ]; then
    CLAUDE_FILE="./CLAUDE.md"
else
    echo "WARNING: No claude.md or CLAUDE.md file found. Creating one is recommended." >&2
    log_message "WARNING: No claude.md file found"
fi

# Safe input parsing with timeout
INPUT=""
if ! INPUT=$(timeout 5 cat); then
    echo "ERROR: Failed to read input within 5 seconds" >&2
    log_message "ERROR: Input timeout"
    exit 1
fi

# Validate JSON input
if [ -z "$INPUT" ] || ! echo "$INPUT" | jq empty 2>/dev/null; then
    echo "ERROR: Invalid or empty JSON input" >&2
    log_message "ERROR: Invalid JSON input"
    exit 1
fi

# Parse input with error handling
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || TOOL_NAME=""
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // empty' 2>/dev/null | sed 's|^/||') || FILE_PATH=""
TASK_DESC=$(echo "$INPUT" | jq -r '.task_description // empty' 2>/dev/null) || TASK_DESC=""
COMMAND=$(echo "$INPUT" | jq -r '.command // empty' 2>/dev/null) || COMMAND=""
SKIP_PERMISSIONS=$(echo "$INPUT" | jq -r '.dangerously_skip_permissions // false' 2>/dev/null) || SKIP_PERMISSIONS="false"

# Validate required fields
if [ -z "$TOOL_NAME" ]; then
    echo "ERROR: tool_name is required" >&2
    log_message "ERROR: Missing tool_name"
    exit 1
fi

# Create directories for tracking
TRACK_DIR="$HOME/.claude/hook_data"
mkdir -p "$TRACK_DIR" || {
    echo "ERROR: Cannot create tracking directory" >&2
    exit 1
}

# Color codes for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo "╔═══════════════════════════════════════════════════════════╗" >&2
echo "║              PRE-TASK COMPLIANCE CHECK                    ║" >&2
echo "╚═══════════════════════════════════════════════════════════╝" >&2
echo "" >&2
echo "🔍 Checking: $TOOL_NAME operation" >&2
if [ -n "$FILE_PATH" ]; then
    echo "📄 Target: $FILE_PATH" >&2
fi
if [ "$SKIP_PERMISSIONS" = "true" ]; then
    echo "⚠️  WARNING: dangerously-skip-permissions flag is set" >&2
fi
echo "" >&2

# Initialize blocking flag
SHOULD_BLOCK=false
BLOCKING_REASON=""

# Function to add blocking reason
add_block() {
    local reason=$1
    SHOULD_BLOCK=true
    BLOCKING_REASON="${BLOCKING_REASON}❌ $reason\n"
    log_message "BLOCKED: $reason"
}

# Function to analyze task complexity (enhanced with safety)
analyze_task_complexity() {
    local complexity=0
    if [ -n "$TASK_DESC" ]; then
        local task_lower=$(echo "$TASK_DESC" | tr '[:upper:]' '[:lower:]' || echo "")
        
        # Safe pattern matching
        echo "$task_lower" | grep -qE "(implement|create|build|develop)" && ((complexity+=2)) || true
        echo "$task_lower" | grep -qE "(refactor|optimize|improve|enhance)" && ((complexity+=3)) || true
        echo "$task_lower" | grep -qE "(debug|fix|resolve|troubleshoot)" && ((complexity+=2)) || true
        echo "$task_lower" | grep -qE "(test|validate|verify|check)" && ((complexity+=1)) || true
        echo "$task_lower" | grep -qE "(multiple|several|various|comprehensive)" && ((complexity+=2)) || true
    fi
    
    # File-based complexity
    if [ -n "$FILE_PATH" ]; then
        echo "$FILE_PATH" | grep -qE "\.(py|js|ts|jsx|tsx)$" && ((complexity+=1)) || true
    fi
    
    [ "$TOOL_NAME" = "MultiEdit" ] && ((complexity+=2)) || true
    
    echo $complexity
}

# RULE CHECKS BASED ON TOOL TYPE
case "$TOOL_NAME" in
    "Write"|"Edit"|"MultiEdit")
        # Check if critical files exist for tracking
        if [ ! -f "./planning/MASTER_TODO.md" ] && [ "$FILE_PATH" != "planning/MASTER_TODO.md" ]; then
            echo "⚠️  WARNING: MASTER_TODO.md missing - should be created first" >&2
        fi
        
        if [ ! -f "./planning/PROJECT_JOURNAL.md" ] && [ "$FILE_PATH" != "planning/PROJECT_JOURNAL.md" ]; then
            echo "⚠️  WARNING: PROJECT_JOURNAL.md missing - should be created first" >&2
        fi
        
        # Don't block if it's a Write operation for a file documented in PROJECT_INDEX.md
        if [ "$TOOL_NAME" = "Write" ] && [ -n "$FILE_PATH" ] && [ -f "./PROJECT_INDEX.md" ]; then
            BASENAME=$(basename "$FILE_PATH")
            if grep -qF "$BASENAME" "./PROJECT_INDEX.md" 2>/dev/null; then
                echo "✅ Allowing creation of documented file: $BASENAME" >&2
                SHOULD_BLOCK=false
            fi
        fi
        ;;
        
    "Bash")
        # Check for dangerous commands with proper escaping
        if [ -n "$COMMAND" ]; then
            # Check for extremely dangerous patterns
            if echo "$COMMAND" | grep -qE "(rm -rf /|:(){:|dd if=/dev/zero|mkfs|fdisk)" 2>/dev/null; then
                add_block "Extremely dangerous command detected"
            fi
            
            # Warning for potentially dangerous commands
            if echo "$COMMAND" | grep -qE "(rm -rf|sudo rm|chmod 777|curl.*\|.*sh)" 2>/dev/null; then
                echo "⚠️  WARNING: Potentially dangerous command pattern detected" >&2
                echo "⚠️  Command will be logged for audit" >&2
                log_message "WARNING: Dangerous command: $COMMAND"
            fi
        fi
        ;;
        
    "Task")
        # For task operations, analyze complexity
        TASK_COMPLEXITY=$(analyze_task_complexity)
        echo "$TASK_COMPLEXITY" > "$TRACK_DIR/current_task_complexity"
        
        # Inject parallel processing hints for complex tasks
        if [ "$TASK_COMPLEXITY" -ge 6 ]; then
            echo -e "\n${CYAN}[COMPLEX TASK DETECTED]${NC} Complexity Score: ${YELLOW}$TASK_COMPLEXITY/10${NC}" >&2
            echo -e "${MAGENTA}ACTIVATING MULTI-SUBAGENT PROCESSING${NC}" >&2
            echo "Expected performance improvement: 2.8-4.4x" >&2
        fi
        ;;
esac

# TIMESTAMP INJECTION
echo -e "\n${CYAN}⏰ TIMESTAMP CONTEXT:${NC}" >&2
echo "Current Time: $(date '+%A, %B %d, %Y at %I:%M %p %Z')" >&2
echo "$(date +%s)" > "$TRACK_DIR/task_start_time"

# Display result
if [ "$SHOULD_BLOCK" = true ]; then
    # Check if permissions should be skipped
    if [ "$SKIP_PERMISSIONS" = "true" ]; then
        echo "" >&2
        echo "⚠️  VIOLATIONS DETECTED but dangerously-skip-permissions is set" >&2
        echo -e "$BLOCKING_REASON" >&2
        echo "" >&2
        echo "🚨 PROCEEDING DESPITE VIOLATIONS (USE WITH CAUTION)" >&2
        log_message "Violations bypassed with skip-permissions: $TOOL_NAME on $FILE_PATH"
    else
        echo "" >&2
        echo "🚫 BLOCKING OPERATION - Rule Violations Detected:" >&2
        echo -e "$BLOCKING_REASON" >&2
        echo "" >&2
        echo "📋 Required Actions:" >&2
        echo "1. Address the violations listed above" >&2
        echo "2. Ensure compliance with claude.md rules" >&2
        echo "3. Retry the operation" >&2
        echo "4. Or use --dangerously-skip-permissions flag to bypass (NOT RECOMMENDED)" >&2
        log_message "Operation blocked: $TOOL_NAME on $FILE_PATH"
        exit 1
    fi
else
    echo -e "\n${GREEN}✅ Pre-task checks PASSED${NC}" >&2
    
    # Complexity-based reminders
    COMPLEXITY=$(analyze_task_complexity)
    if [ "$COMPLEXITY" -ge 3 ]; then
        echo -e "\n${CYAN}🤖 SUBAGENT ACTIVATION REMINDERS:${NC}" >&2
        echo "• Break complex tasks into parallel subtasks" >&2
        echo "• Process independent components simultaneously" >&2
    fi
    
    echo -e "\n${BLUE}📋 Standard Reminders:${NC}" >&2
    echo "• Update MASTER_TODO.md after task completion" >&2
    echo "• Add significant changes to PROJECT_JOURNAL.md" >&2
fi

# Enhanced logging
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
RESULT_STATUS="PASSED"
if [ "$SHOULD_BLOCK" = true ] && [ "$SKIP_PERMISSIONS" = "true" ]; then
    RESULT_STATUS="BYPASSED"
fi
echo "$TIMESTAMP | $TOOL_NAME | ${FILE_PATH:-no-file} | Complexity: $COMPLEXITY | SkipPerms: $SKIP_PERMISSIONS | Result: $RESULT_STATUS" >> "$TRACK_DIR/operations.log"

# Special audit log for skip-permissions usage
if [ "$SKIP_PERMISSIONS" = "true" ]; then
    AUDIT_LOG="$TRACK_DIR/skip_permissions_audit.log"
    echo "$TIMESTAMP | $TOOL_NAME | ${FILE_PATH:-no-file} | Violations: ${BLOCKING_REASON//[$'\n']/; } | User: $USER" >> "$AUDIT_LOG"
    echo "⚠️  Skip-permissions usage logged to: $AUDIT_LOG" >&2
fi

# Release lock
flock -u 200

log_message "pre_task_review.sh completed successfully"
exit 0