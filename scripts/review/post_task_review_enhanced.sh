#!/bin/bash

# Script: post_task_review_enhanced.sh (Production Safety Version)
# Purpose: Production-level post-task validation and compliance checking
# Version: 3.0.0 - Enhanced Safety with Security Monitoring

set -euo pipefail
SCRIPT_VERSION="3.0.0"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Check if claude.md or CLAUDE.md exists
CLAUDE_FILE=""
if [ -f "./claude.md" ]; then
    CLAUDE_FILE="./claude.md"
elif [ -f "./CLAUDE.md" ]; then
    CLAUDE_FILE="./CLAUDE.md"
else
    echo "ERROR: No claude.md or CLAUDE.md file found. Cannot verify rule compliance." >&2
    exit 2
fi

# Parse input from Claude
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // ""' | sed 's|^/||')
SKIP_PERMISSIONS=$(echo "$INPUT" | jq -r '.dangerously_skip_permissions // false' 2>/dev/null) || SKIP_PERMISSIONS="false"

# Create directories for tracking
TRACK_DIR="$HOME/.claude/hook_data"
COMPLIANCE_DIR="$TRACK_DIR/compliance"
VIOLATION_LOG="$COMPLIANCE_DIR/violations_${SESSION_ID}.log"
SECURITY_AUDIT="$TRACK_DIR/security_audit.log"
mkdir -p "$COMPLIANCE_DIR"

# Performance tracking
START_TIME_FILE="$TRACK_DIR/task_start_time"
COMPLEXITY_FILE="$TRACK_DIR/current_task_complexity"

echo -e "${CYAN}TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW${NC}" >&2
echo -e "${CYAN}Q    POST-TASK SECURITY VALIDATION & COMPLIANCE REVIEW      Q${NC}" >&2
echo -e "${CYAN}ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]${NC}" >&2
echo "" >&2

# Security post-check function
perform_security_audit() {
    local audit_passed=true
    local security_issues=""
    
    echo -e "${MAGENTA}🔒 SECURITY AUDIT:${NC}" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    
    # Check for exposed secrets in recent files
    RECENT_FILES=$(find . -type f -mmin -10 \
        -not -path "./.claude/*" \
        -not -path "./.git/*" \
        -not -name "*.log" \
        2>/dev/null | sort)
    
    for file in $RECENT_FILES; do
        if [ -f "$file" ]; then
            # Check for exposed API keys
            if grep -qE "(sk-or-v1-|OPENROUTER_API_KEY.*=.*sk-|API_KEY.*=.*[a-zA-Z0-9]{32,})" "$file" 2>/dev/null; then
                security_issues="${security_issues}❌ Exposed API key found in: $file\n"
                audit_passed=false
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] CRITICAL: Exposed API key in $file" >> "$SECURITY_AUDIT"
            fi
            
            # Check for hardcoded passwords
            if grep -qE "(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]" "$file" 2>/dev/null; then
                security_issues="${security_issues}❌ Hardcoded password found in: $file\n"
                audit_passed=false
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] CRITICAL: Hardcoded password in $file" >> "$SECURITY_AUDIT"
            fi
        fi
    done
    
    # Check for dangerous file permissions
    WORLD_WRITABLE=$(find . -type f -perm -o+w -not -path "./.git/*" 2>/dev/null || true)
    if [ -n "$WORLD_WRITABLE" ]; then
        security_issues="${security_issues}❌ World-writable files detected\n"
        audit_passed=false
    fi
    
    if [ "$audit_passed" = true ]; then
        echo -e "${GREEN}✅ Security audit PASSED${NC}" >&2
    else
        echo -e "${RED}❌ SECURITY VIOLATIONS DETECTED:${NC}" >&2
        echo -e "$security_issues" >&2
        echo "" >&2
        echo -e "${YELLOW}⚠️  IMMEDIATE ACTION REQUIRED:${NC}" >&2
        echo "1. Remove exposed secrets immediately" >&2
        echo "2. Rotate any exposed credentials" >&2
        echo "3. Use environment variables for sensitive data" >&2
    fi
    
    return $([ "$audit_passed" = true ] && echo 0 || echo 1)
}

# Initialize violation tracking
VIOLATIONS=()
WARNINGS=()
SECURITY_VIOLATIONS=()

# Function to add violation
add_violation() {
    local rule_id=$1
    local description=$2
    VIOLATIONS+=("[$rule_id] $description")
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $TOOL_NAME - [$rule_id] $description" >> "$VIOLATION_LOG"
}

# Function to add warning
add_warning() {
    local rule_id=$1
    local description=$2
    WARNINGS+=("[$rule_id] $description")
}

# Function to add security violation
add_security_violation() {
    local description=$1
    SECURITY_VIOLATIONS+=("$description")
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SECURITY - $description" >> "$SECURITY_AUDIT"
}

# Find recently modified files
RECENT_FILES=$(find . -type f -mmin -10 \
    -not -path "./.claude/*" \
    -not -path "./.git/*" \
    -not -name "*.log" \
    2>/dev/null | sort)

FILE_COUNT=$(echo -n "$RECENT_FILES" | grep -c '^' || echo "0")

# ENHANCED SECURITY AUDIT
perform_security_audit || add_security_violation "Security audit failed - see details above"

# Display compliance results
echo -e "\n${YELLOW}📊 COMPLIANCE SUMMARY:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

if [ "$SKIP_PERMISSIONS" = "true" ]; then
    echo -e "${YELLOW}⚠️  dangerously-skip-permissions flag is active${NC}" >&2
fi

# Calculate total issues
TOTAL_ISSUES=$((${#VIOLATIONS[@]} + ${#SECURITY_VIOLATIONS[@]}))

if [ $TOTAL_ISSUES -eq 0 ] && [ ${#WARNINGS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ NO VIOLATIONS DETECTED - ALL CHECKS PASSED${NC}" >&2
else
    if [ ${#SECURITY_VIOLATIONS[@]} -gt 0 ]; then
        echo -e "${RED}🚨 SECURITY VIOLATIONS: ${#SECURITY_VIOLATIONS[@]} found${NC}" >&2
        for violation in "${SECURITY_VIOLATIONS[@]}"; do
            echo "   • $violation" >&2
        done
        echo "" >&2
    fi
    
    if [ ${#VIOLATIONS[@]} -gt 0 ]; then
        if [ "$SKIP_PERMISSIONS" = "true" ]; then
            echo -e "${YELLOW}⚠️  CRITICAL VIOLATIONS: ${#VIOLATIONS[@]} found (bypassed)${NC}" >&2
        else
            echo -e "${RED}❌ CRITICAL VIOLATIONS: ${#VIOLATIONS[@]} found${NC}" >&2
        fi
        for violation in "${VIOLATIONS[@]}"; do
            echo "   • $violation" >&2
        done
        echo "" >&2
    fi
    
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNINGS: ${#WARNINGS[@]} found${NC}" >&2
        for warning in "${WARNINGS[@]}"; do
            echo "   • $warning" >&2
        done
    fi
fi

# Required actions section
echo -e "\n${YELLOW}📝 REQUIRED COMPLIANCE VERIFICATION:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

if [ ${#SECURITY_VIOLATIONS[@]} -gt 0 ]; then
    echo -e "${RED}🚨 SECURITY VIOLATIONS REQUIRE IMMEDIATE ACTION:${NC}" >&2
    echo "1. Fix all security violations listed above" >&2
    echo "2. Remove or secure any exposed credentials" >&2
    echo "3. Run security audit again to verify fixes" >&2
    echo "4. Respond with: 'SECURITY FIXED: [description of security fixes]'" >&2
elif [ ${#VIOLATIONS[@]} -gt 0 ]; then
    if [ "$SKIP_PERMISSIONS" = "true" ]; then
        echo -e "${YELLOW}⚠️  VIOLATIONS DETECTED (bypassed) - You should:${NC}" >&2
        echo "1. Be aware of the violations listed above" >&2
        echo "2. Consider fixing them when possible" >&2
        echo "3. Document why skip-permissions was necessary" >&2
        echo "4. Respond with: 'ACKNOWLEDGED: Proceeding with skip-permissions'" >&2
    else
        echo -e "${RED}⚠️  VIOLATIONS DETECTED - You must:${NC}" >&2
        echo "1. Fix the violations listed above" >&2
        echo "2. Update affected files to comply with rules" >&2
        echo "3. Respond with: 'VIOLATIONS FIXED: [description of fixes]'" >&2
        echo "4. Or use --dangerously-skip-permissions flag to bypass (NOT RECOMMENDED)" >&2
    fi
else
    echo -e "${GREEN}✓ No critical violations found - You must:${NC}" >&2
    echo "1. Review all changes for rule compliance" >&2
    echo "2. Address any warnings if applicable" >&2
    echo "3. Respond with: 'COMPLIANCE CONFIRMED: All changes follow claude.md rules'" >&2
fi

# Enhanced security reminders
echo -e "\n${RED}🔒 SECURITY BEST PRACTICES:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
echo "• NEVER commit .env files or secrets to git" >&2
echo "• Use environment variables for all sensitive data" >&2
echo "• Rotate credentials if any exposure is suspected" >&2
echo "• Enable 2FA on all developer accounts" >&2
echo "• Review security audit logs regularly" >&2

# Log skip-permissions usage
if [ "$SKIP_PERMISSIONS" = "true" ]; then
    AUDIT_LOG="$TRACK_DIR/skip_permissions_audit.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | POST-TASK | $TOOL_NAME | ${FILE_PATH:-no-file} | Violations: ${#VIOLATIONS[@]} | Warnings: ${#WARNINGS[@]} | Security: ${#SECURITY_VIOLATIONS[@]}" >> "$AUDIT_LOG"
fi

echo "" >&2
echo "This compliance check is MANDATORY and ensures project consistency." >&2

# Exit 2 to ensure Claude processes this review
exit 2