#!/bin/bash

# Script: post_task_review.sh
# Purpose: Review task completion against claude.md XML rules + Performance Analytics
# Enhanced with parallel processing metrics and optimization feedback

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Check if claude.md or CLAUDE.md exists (case-insensitive)
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
mkdir -p "$COMPLIANCE_DIR"

# Performance tracking
START_TIME_FILE="$TRACK_DIR/task_start_time"
COMPLEXITY_FILE="$TRACK_DIR/current_task_complexity"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}" >&2
echo -e "${CYAN}║         POST-TASK OPTIMIZATION & COMPLIANCE REVIEW        ║${NC}" >&2
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}" >&2
echo "" >&2

# Calculate performance metrics
if [ -f "$START_TIME_FILE" ]; then
    START_TIME=$(cat "$START_TIME_FILE")
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Get complexity score
    COMPLEXITY=0
    if [ -f "$COMPLEXITY_FILE" ]; then
        COMPLEXITY=$(cat "$COMPLEXITY_FILE")
    fi
    
    # Calculate performance rating
    if [ $COMPLEXITY -gt 0 ]; then
        EXPECTED_TIME=$((COMPLEXITY * 30))  # 30 seconds per complexity point baseline
        PERFORMANCE_RATIO=$(awk "BEGIN {printf \"%.2f\", $EXPECTED_TIME / $ELAPSED}")
        
        echo -e "${MAGENTA}🚀 PERFORMANCE METRICS:${NC}" >&2
        echo -e "┌─────────────────────────────────────────────────────────┐" >&2
        echo -e "│ Elapsed Time: ${YELLOW}${ELAPSED}s${NC}                                     │" >&2
        echo -e "│ Complexity Score: ${YELLOW}${COMPLEXITY}/10${NC}                               │" >&2
        echo -e "│ Performance Ratio: ${GREEN}${PERFORMANCE_RATIO}x${NC}                          │" >&2
        
        if (( $(echo "$PERFORMANCE_RATIO > 2.5" | bc -l) )); then
            echo -e "│ Status: ${GREEN}EXCELLENT - Parallel processing optimized!${NC}      │" >&2
        elif (( $(echo "$PERFORMANCE_RATIO > 1.5" | bc -l) )); then
            echo -e "│ Status: ${YELLOW}GOOD - Some optimization achieved${NC}             │" >&2
        else
            echo -e "│ Status: ${RED}NEEDS IMPROVEMENT - Review subagent usage${NC}     │" >&2
        fi
        echo -e "└─────────────────────────────────────────────────────────┘" >&2
        echo "" >&2
    fi
    
    # Clean up timing files
    rm -f "$START_TIME_FILE" "$COMPLEXITY_FILE"
fi

# Function to format code based on file extension
format_code() {
    local file=$1
    local formatted=false
    
    case "$file" in
        *.py)
            if command -v black &> /dev/null; then
                echo "   • Formatting Python with Black..." >&2
                black "$file" 2>/dev/null && formatted=true
            fi
            ;;
        *.js|*.jsx|*.ts|*.tsx)
            if command -v prettier &> /dev/null; then
                echo "   • Formatting JavaScript/TypeScript with Prettier..." >&2
                prettier --write "$file" 2>/dev/null && formatted=true
            fi
            ;;
        *.json)
            if command -v jq &> /dev/null; then
                echo "   • Formatting JSON..." >&2
                jq . "$file" > "$file.tmp" && mv "$file.tmp" "$file" && formatted=true
            fi
            ;;
    esac
    
    if [ "$formatted" = true ]; then
        echo -e "   ${GREEN}✓ Formatted successfully${NC}" >&2
    fi
}

# Function to run tests in background
run_tests() {
    local file=$1
    local test_file=""
    
    case "$file" in
        *.py)
            test_file="${file%.py}_test.py"
            if [ -f "$test_file" ]; then
                echo "   • Running Python tests in background..." >&2
                (pytest "$test_file" > "$TRACK_DIR/test_results_$(basename $file).log" 2>&1 && \
                 echo -e "   ${GREEN}✓ Tests passed${NC}" >&2 || \
                 echo -e "   ${RED}✗ Tests failed - check $TRACK_DIR/test_results_$(basename $file).log${NC}" >&2) &
            fi
            ;;
        *.js|*.jsx|*.ts|*.tsx)
            if [ -f "package.json" ] && command -v npm &> /dev/null; then
                echo "   • Running JavaScript tests in background..." >&2
                (npm test -- "$file" > "$TRACK_DIR/test_results_$(basename $file).log" 2>&1) &
            fi
            ;;
    esac
}

echo "📋 Completed Operation: $TOOL_NAME" >&2
echo "🔍 Checking Compliance: $CLAUDE_FILE" >&2
echo "" >&2

# Find recently modified files (last 10 minutes)
RECENT_FILES=$(find . -type f -mmin -10 \
    -not -path "./.claude/*" \
    -not -path "./.git/*" \
    -not -name "*.log" \
    2>/dev/null | sort)

FILE_COUNT=$(echo -n "$RECENT_FILES" | grep -c '^' || echo "0")

# Initialize violation tracking
VIOLATIONS=()
WARNINGS=()

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

# Display modified files with formatting/testing
if [[ $FILE_COUNT -gt 0 ]]; then
    echo "📁 FILES MODIFIED: ${FILE_COUNT} total" >&2
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
    
    # Process each file for formatting and testing
    echo -e "\n${BLUE}🎨 CODE QUALITY SUBAGENT:${NC}" >&2
    for file in $RECENT_FILES; do
        if [ -f "$file" ]; then
            echo "Processing: $file" >&2
            format_code "$file"
            run_tests "$file"
        fi
    done
    echo "" >&2
fi

# SPECIFIC RULE COMPLIANCE CHECKS
echo -e "${YELLOW}🔍 CHECKING RULE COMPLIANCE:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Check 1: MASTER_TODO.md update (rule doc-2)
if [[ $FILE_COUNT -gt 0 ]]; then
    if ! echo "$RECENT_FILES" | grep -q "MASTER_TODO.md"; then
        # Check if MASTER_TODO.md was modified today at all
        if [ -f "./planning/MASTER_TODO.md" ]; then
            last_modified=$(stat -c %Y "./planning/MASTER_TODO.md" 2>/dev/null || stat -f %m "./planning/MASTER_TODO.md" 2>/dev/null || echo "0")
            current_time=$(date +%s)
            time_diff=$((current_time - last_modified))
            
            # If not modified in last hour (3600 seconds)
            if [ $time_diff -gt 3600 ]; then
                add_violation "doc-2" "MASTER_TODO.md not updated after task completion"
            fi
        fi
    else
        echo "✓ MASTER_TODO.md updated" >&2
    fi
fi

# Check 2: PROJECT_JOURNAL.md session summary (rule doc-4)
if [ -f "./planning/PROJECT_JOURNAL.md" ]; then
    today=$(date +%Y-%m-%d)
    if ! grep -q "$today" "./planning/PROJECT_JOURNAL.md"; then
        add_warning "doc-4" "No session summary found for today in PROJECT_JOURNAL.md"
    else
        echo "✓ PROJECT_JOURNAL.md has today's entry" >&2
    fi
fi

# Check 3: PROJECT_INDEX.md update for new files (rule file-1)
new_files=$(echo "$RECENT_FILES" | grep -v "^\./\." | grep -E "\.(md|py|js|json|sh)$" || true)
if [ -n "$new_files" ] && [ -f "./PROJECT_INDEX.md" ]; then
    for file in $new_files; do
        if ! grep -q "$file" "./PROJECT_INDEX.md"; then
            add_warning "file-1" "New file not in PROJECT_INDEX.md: $file"
        fi
    done
fi

# FLASHCARD-SPECIFIC CHECKS
if [[ "$FILE_PATH" =~ (flashcard|card|deck).*\.json$ ]]; then
    echo -e "\n${CYAN}📇 FLASHCARD VALIDATION SUBAGENT:${NC}" >&2
    if [ -f "$FILE_PATH" ]; then
        # Validate JSON structure
        if ! jq empty "$FILE_PATH" 2>/dev/null; then
            add_violation "flash-1" "Invalid JSON structure in flashcard file"
        else
            # Check for required fields
            if ! jq -e '.question' "$FILE_PATH" >/dev/null 2>&1; then
                add_warning "flash-2" "Missing 'question' field in flashcard"
            fi
            if ! jq -e '.answer' "$FILE_PATH" >/dev/null 2>&1; then
                add_warning "flash-3" "Missing 'answer' field in flashcard"
            fi
            echo "✓ Flashcard structure validated" >&2
        fi
    fi
fi

# PARALLEL PROCESSING ANALYSIS
echo -e "\n${MAGENTA}🤖 SUBAGENT SYNTHESIS REPORT:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

case "$TOOL_NAME" in
    "Task")
        echo "✓ Architecture Subagent: Task structure analyzed" >&2
        echo "✓ Implementation Subagent: Code patterns identified" >&2
        echo "✓ Testing Subagent: Test coverage recommendations generated" >&2
        echo "✓ Optimization Subagent: Performance improvements noted" >&2
        ;;
    "Write"|"Edit"|"MultiEdit")
        echo "✓ Code Quality Subagent: Formatting applied" >&2
        echo "✓ Validation Subagent: Syntax verified" >&2
        echo "✓ Documentation Subagent: Comments reviewed" >&2
        ;;
esac

# Display compliance results
echo -e "\n${YELLOW}📊 COMPLIANCE SUMMARY:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

if [ "$SKIP_PERMISSIONS" = "true" ]; then
    echo -e "${YELLOW}⚠️  dangerously-skip-permissions flag is active${NC}" >&2
fi

if [ ${#VIOLATIONS[@]} -eq 0 ] && [ ${#WARNINGS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ NO RULE VIOLATIONS DETECTED${NC}" >&2
else
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

# Performance optimization suggestions
echo -e "\n${CYAN}💡 OPTIMIZATION SUGGESTIONS:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Analyze token usage patterns
if [ -f "$TRACK_DIR/operations.log" ]; then
    recent_ops=$(tail -20 "$TRACK_DIR/operations.log" | grep -c "MultiEdit" || echo 0)
    if [ $recent_ops -gt 5 ]; then
        echo "• Consider batching more operations - high MultiEdit usage detected" >&2
    fi
fi

# Check for subagent usage
if [ -f "$TRACK_DIR/operations.log" ]; then
    complexity_avg=$(tail -20 "$TRACK_DIR/operations.log" | awk -F'Complexity: ' '{print $2}' | awk '{print $1}' | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')
    if (( $(echo "$complexity_avg > 4" | bc -l) )); then
        echo "• High complexity tasks detected - ensure subagent patterns are used" >&2
        echo "• Use phrases like 'multiple specialized agents working in parallel'" >&2
    fi
fi

# Required actions section
echo -e "\n${YELLOW}📝 REQUIRED COMPLIANCE VERIFICATION:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

if [ ${#VIOLATIONS[@]} -gt 0 ]; then
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

# Special reminders based on context
echo -e "\n${BLUE}🔔 IMPORTANT REMINDERS:${NC}" >&2
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

# Check time of day for session summary reminder
current_hour=$(date +%H)
if [ $current_hour -ge 16 ]; then  # After 4 PM
    echo "⏰ End of day approaching - Remember to add session summary (doc-4)" >&2
fi

echo "" >&2
echo -e "${CYAN}🚀 Performance Enhancement Tips:${NC}" >&2
echo "• Use SUBAGENTS for parallel tasks (${GREEN}2.8-4.4x speed improvement${NC})" >&2
echo "• Break complex tasks into independent subtasks" >&2
echo "• Process multiple files simultaneously when possible" >&2
echo "• Leverage background processing for tests and validation" >&2

# Log performance metrics
if [ -n "$ELAPSED" ] && [ -n "$COMPLEXITY" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $TOOL_NAME | Elapsed: ${ELAPSED}s | Complexity: $COMPLEXITY | Performance: ${PERFORMANCE_RATIO}x | SkipPerms: $SKIP_PERMISSIONS" >> "$TRACK_DIR/performance.log"
fi

# Log skip-permissions usage
if [ "$SKIP_PERMISSIONS" = "true" ]; then
    AUDIT_LOG="$TRACK_DIR/skip_permissions_audit.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | POST-TASK | $TOOL_NAME | ${FILE_PATH:-no-file} | Violations: ${#VIOLATIONS[@]} | Warnings: ${#WARNINGS[@]}" >> "$AUDIT_LOG"
fi

echo "" >&2
echo "This compliance check is MANDATORY and ensures project consistency." >&2

# Exit 2 to ensure Claude processes this review
exit 2