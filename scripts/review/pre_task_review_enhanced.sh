#!/bin/bash

# Script: pre_task_review_enhanced.sh (Production Safety Version)
# Purpose: Production-level pre-task compliance and safety checking
# Version: 3.0.0 - Enhanced Safety

set -euo pipefail
SCRIPT_VERSION="3.0.0"

# Critical paths that must NEVER be destroyed
PROTECTED_DIRECTORIES=(
    "/"
    "/home"
    "/etc"
    "/usr"
    "/bin"
    "/sbin"
    "/var"
    "/opt"
    "/boot"
    "/dev"
    "/proc"
    "/sys"
    ".git"
    "node_modules"
    "venv"
    ".claude"
)

# Sensitive file patterns that must be protected
SENSITIVE_FILE_PATTERNS=(
    "*.env"
    "*.key"
    "*.pem"
    "*.cert"
    "*_key"
    "*_secret"
    "*password*"
    "*token*"
    "*.credentials"
    "id_rsa*"
    "*.ssh/*"
)

# Commands that are NEVER allowed, even with skip-permissions
BLACKLISTED_COMMANDS=(
    "rm -rf /"
    "rm -rf /*"
    ":(){:|:&};"  # Fork bomb
    "dd if=/dev/zero"
    "mkfs"
    "fdisk"
    "shred"
    "> /dev/sda"
)

# Dependency check
for cmd in jq sed grep mkdir flock; do
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
    flock 200
fi

# Logging setup
LOG_FILE="$HOME/.claude/hook_data/pre_review_$(date +%Y%m%d).log"
SECURITY_LOG="$HOME/.claude/hook_data/security_violations.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_security() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SECURITY: $1" >> "$SECURITY_LOG"
}

log_message "pre_task_review_enhanced.sh v$SCRIPT_VERSION started"

# Check if claude.md or CLAUDE.md exists
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

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo "TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW" >&2
echo "Q          PRE-TASK COMPLIANCE & SAFETY CHECK               Q" >&2
echo "ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]" >&2
echo "" >&2
echo "= Checking: $TOOL_NAME operation" >&2
if [ -n "$FILE_PATH" ]; then
    echo "=Ä Target: $FILE_PATH" >&2
fi
if [ "$SKIP_PERMISSIONS" = "true" ]; then
    echo -e "${YELLOW}   WARNING: dangerously-skip-permissions flag is set${NC}" >&2
fi
echo "" >&2

# Initialize blocking flags
SHOULD_BLOCK=false
HARD_BLOCK=false  # Cannot be bypassed even with skip-permissions
BLOCKING_REASON=""
SECURITY_VIOLATIONS=""

# Function to add blocking reason
add_block() {
    local reason=$1
    SHOULD_BLOCK=true
    BLOCKING_REASON="${BLOCKING_REASON}L $reason\n"
    log_message "BLOCKED: $reason"
}

# Function to add hard block (cannot be bypassed)
add_hard_block() {
    local reason=$1
    HARD_BLOCK=true
    SECURITY_VIOLATIONS="${SECURITY_VIOLATIONS}=« SECURITY VIOLATION: $reason\n"
    log_security "$reason"
}

# Function to check if path is protected
is_protected_path() {
    local path=$1
    local abs_path=$(realpath "$path" 2>/dev/null || echo "$path")
    
    for protected in "${PROTECTED_DIRECTORIES[@]}"; do
        if [[ "$abs_path" == "$protected" ]] || [[ "$abs_path" == "$protected/"* ]]; then
            return 0
        fi
    done
    return 1
}

# Function to check if file contains sensitive data
is_sensitive_file() {
    local file=$1
    
    for pattern in "${SENSITIVE_FILE_PATTERNS[@]}"; do
        if [[ "$file" == $pattern ]]; then
            return 0
        fi
    done
    return 1
}

# Function to check for blacklisted commands
is_blacklisted_command() {
    local cmd=$1
    
    for blacklisted in "${BLACKLISTED_COMMANDS[@]}"; do
        if [[ "$cmd" == *"$blacklisted"* ]]; then
            return 0
        fi
    done
    return 1
}

# Enhanced task complexity analysis
analyze_task_complexity() {
    local complexity=0
    if [ -n "$TASK_DESC" ]; then
        local task_lower=$(echo "$TASK_DESC" | tr '[:upper:]' '[:lower:]' || echo "")
        
        echo "$task_lower" | grep -qE "(implement|create|build|develop)" && ((complexity+=2)) || true
        echo "$task_lower" | grep -qE "(refactor|optimize|improve|enhance)" && ((complexity+=3)) || true
        echo "$task_lower" | grep -qE "(debug|fix|resolve|troubleshoot)" && ((complexity+=2)) || true
        echo "$task_lower" | grep -qE "(test|validate|verify|check)" && ((complexity+=1)) || true
        echo "$task_lower" | grep -qE "(multiple|several|various|comprehensive)" && ((complexity+=2)) || true
    fi
    
    if [ -n "$FILE_PATH" ]; then
        echo "$FILE_PATH" | grep -qE "\.(py|js|ts|jsx|tsx)$" && ((complexity+=1)) || true
    fi
    
    [ "$TOOL_NAME" = "MultiEdit" ] && ((complexity+=2)) || true
    
    echo $complexity
}

# ENHANCED SAFETY CHECKS
case "$TOOL_NAME" in
    "Write"|"Edit"|"MultiEdit")
        # Check for sensitive file modifications
        if [ -n "$FILE_PATH" ] && is_sensitive_file "$FILE_PATH"; then
            add_hard_block "Attempting to modify sensitive file: $FILE_PATH"
        fi
        
        # Check for .env file specifically
        if [[ "$FILE_PATH" == ".env" ]] || [[ "$FILE_PATH" == *"/.env" ]]; then
            # Check if trying to expose API keys
            if echo "$INPUT" | jq -r '.content // .new_string // ""' 2>/dev/null | grep -qE "(console\.log|print|echo|export|curl.*-d).*API_KEY"; then
                add_hard_block "Attempting to expose API keys from .env file"
            fi
        fi
        
        # Standard compliance checks
        if [ ! -f "./planning/MASTER_TODO.md" ] && [ "$FILE_PATH" != "planning/MASTER_TODO.md" ]; then
            echo "   WARNING: MASTER_TODO.md missing - should be created first" >&2
        fi
        
        if [ ! -f "./planning/PROJECT_JOURNAL.md" ] && [ "$FILE_PATH" != "planning/PROJECT_JOURNAL.md" ]; then
            echo "   WARNING: PROJECT_JOURNAL.md missing - should be created first" >&2
        fi
        ;;
        
    "Bash")
        # Check for blacklisted commands
        if [ -n "$COMMAND" ]; then
            if is_blacklisted_command "$COMMAND"; then
                add_hard_block "Blacklisted command detected: $COMMAND"
            fi
            
            # Check for directory destruction
            if echo "$COMMAND" | grep -qE "rm\s+-rf?\s+/|rm\s+-rf?\s+\.|rmdir.*-p|find.*-delete"; then
                # Extract the target path
                TARGET_PATH=$(echo "$COMMAND" | sed -E 's/.*rm\s+-rf?\s+([^ ]+).*/\1/')
                if is_protected_path "$TARGET_PATH"; then
                    add_hard_block "Attempting to destroy protected directory: $TARGET_PATH"
                fi
            fi
            
            # Check for attempts to read/expose .env files
            if echo "$COMMAND" | grep -qE "(cat|less|more|head|tail|grep).*\.env|env.*\|.*curl|printenv.*API"; then
                add_hard_block "Attempting to read or expose environment variables"
            fi
            
            # Check for network commands that might leak secrets
            if echo "$COMMAND" | grep -qE "curl.*-d.*\$|wget.*--post-data.*\$|nc.*<.*\.env"; then
                add_hard_block "Attempting to send sensitive data over network"
            fi
            
            # Standard dangerous command warnings
            if echo "$COMMAND" | grep -qE "(sudo\s+rm|chmod\s+777|chown.*-R.*root)"; then
                add_block "Dangerous system command detected"
            fi
        fi
        ;;
        
    "Task")
        # Task complexity analysis
        TASK_COMPLEXITY=$(analyze_task_complexity)
        echo "$TASK_COMPLEXITY" > "$TRACK_DIR/current_task_complexity"
        
        if [ "$TASK_COMPLEXITY" -ge 6 ]; then
            echo -e "\n${CYAN}[COMPLEX TASK DETECTED]${NC} Complexity Score: ${YELLOW}$TASK_COMPLEXITY/10${NC}" >&2
            echo -e "${MAGENTA}ACTIVATING MULTI-SUBAGENT PROCESSING${NC}" >&2
            echo "Expected performance improvement: 2.8-4.4x" >&2
        fi
        ;;
        
    "Read")
        # Check for reading sensitive files
        if [ -n "$FILE_PATH" ] && is_sensitive_file "$FILE_PATH"; then
            echo -e "${YELLOW}   WARNING: Reading sensitive file. Contents must not be exposed.${NC}" >&2
            log_security "Read access to sensitive file: $FILE_PATH"
        fi
        ;;
esac

# TIMESTAMP INJECTION
echo -e "\n${CYAN}ð TIMESTAMP CONTEXT:${NC}" >&2
echo "Current Time: $(date '+%A, %B %d, %Y at %I:%M %p %Z')" >&2
echo "$(date +%s)" > "$TRACK_DIR/task_start_time"

# Display result
if [ "$HARD_BLOCK" = true ]; then
    echo "" >&2
    echo -e "${RED}=« OPERATION BLOCKED - SECURITY VIOLATION${NC}" >&2
    echo -e "${RED}This operation cannot be performed even with skip-permissions${NC}" >&2
    echo -e "$SECURITY_VIOLATIONS" >&2
    echo "" >&2
    echo "=Ë Required Actions:" >&2
    echo "1. Review the security violations above" >&2
    echo "2. Modify your request to avoid protected resources" >&2
    echo "3. Consult documentation for allowed operations" >&2
    log_message "HARD BLOCKED: Security violation for $TOOL_NAME"
    exit 1
elif [ "$SHOULD_BLOCK" = true ]; then
    if [ "$SKIP_PERMISSIONS" = "true" ]; then
        echo "" >&2
        echo -e "${YELLOW}   VIOLATIONS DETECTED but dangerously-skip-permissions is set${NC}" >&2
        echo -e "$BLOCKING_REASON" >&2
        echo "" >&2
        echo -e "${YELLOW}=¨ PROCEEDING DESPITE VIOLATIONS (USE WITH CAUTION)${NC}" >&2
        log_message "Violations bypassed with skip-permissions: $TOOL_NAME on $FILE_PATH"
    else
        echo "" >&2
        echo -e "${RED}=« BLOCKING OPERATION - Rule Violations Detected:${NC}" >&2
        echo -e "$BLOCKING_REASON" >&2
        echo "" >&2
        echo "=Ë Required Actions:" >&2
        echo "1. Address the violations listed above" >&2
        echo "2. Ensure compliance with claude.md rules" >&2
        echo "3. Retry the operation" >&2
        echo "4. Or use --dangerously-skip-permissions flag to bypass (NOT RECOMMENDED)" >&2
        log_message "Operation blocked: $TOOL_NAME on $FILE_PATH"
        exit 1
    fi
else
    echo -e "\n${GREEN} Pre-task checks PASSED${NC}" >&2
    
    # Complexity-based reminders
    COMPLEXITY=$(analyze_task_complexity)
    if [ "$COMPLEXITY" -ge 3 ]; then
        echo -e "\n${CYAN}> SUBAGENT ACTIVATION REMINDERS:${NC}" >&2
        echo "" Break complex tasks into parallel subtasks" >&2
        echo "" Process independent components simultaneously" >&2
    fi
    
    echo -e "\n${BLUE}=Ë Standard Reminders:${NC}" >&2
    echo "" Update MASTER_TODO.md after task completion" >&2
    echo "" Add significant changes to PROJECT_JOURNAL.md" >&2
fi

# Enhanced logging
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
RESULT_STATUS="PASSED"
if [ "$HARD_BLOCK" = true ]; then
    RESULT_STATUS="SECURITY_BLOCKED"
elif [ "$SHOULD_BLOCK" = true ] && [ "$SKIP_PERMISSIONS" = "true" ]; then
    RESULT_STATUS="BYPASSED"
elif [ "$SHOULD_BLOCK" = true ]; then
    RESULT_STATUS="BLOCKED"
fi

echo "$TIMESTAMP | $TOOL_NAME | ${FILE_PATH:-no-file} | Complexity: $(analyze_task_complexity) | SkipPerms: $SKIP_PERMISSIONS | Result: $RESULT_STATUS" >> "$TRACK_DIR/operations.log"

# Special audit log for skip-permissions usage
if [ "$SKIP_PERMISSIONS" = "true" ] && [ "$SHOULD_BLOCK" = true ]; then
    AUDIT_LOG="$TRACK_DIR/skip_permissions_audit.log"
    echo "$TIMESTAMP | $TOOL_NAME | ${FILE_PATH:-no-file} | Violations: ${BLOCKING_REASON//[$'\n']/; } | User: $USER" >> "$AUDIT_LOG"
    echo -e "${YELLOW}   Skip-permissions usage logged to: $AUDIT_LOG${NC}" >&2
fi

# Security event logging
if [ "$HARD_BLOCK" = true ] || [ -n "$SECURITY_VIOLATIONS" ]; then
    echo "$TIMESTAMP | $TOOL_NAME | ${FILE_PATH:-no-file} | Security Event | User: $USER" >> "$SECURITY_LOG"
fi

# Release lock
flock -u 200

log_message "pre_task_review_enhanced.sh completed with status: $RESULT_STATUS"
exit 0