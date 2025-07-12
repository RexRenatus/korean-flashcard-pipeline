#!/bin/bash

# Test script for dangerously-skip-permissions flag
echo "Testing pre_task_review.sh and post_task_review.sh with skip-permissions flag"
echo "============================================================================"

# Test 1: Pre-task review without skip-permissions
echo -e "\nTest 1: Pre-task review WITHOUT skip-permissions (should block dangerous command)"
echo '{"tool_name": "Bash", "command": "rm -rf /tmp/test", "dangerously_skip_permissions": false}' | ./pre_task_review.sh
echo "Exit code: $?"

# Test 2: Pre-task review with skip-permissions
echo -e "\nTest 2: Pre-task review WITH skip-permissions (should allow dangerous command)"
echo '{"tool_name": "Bash", "command": "rm -rf /tmp/test", "dangerously_skip_permissions": true}' | ./pre_task_review.sh
echo "Exit code: $?"

# Test 3: Post-task review without skip-permissions
echo -e "\nTest 3: Post-task review WITHOUT skip-permissions"
echo '{"tool_name": "Write", "file_path": "test.txt", "session_id": "test123", "dangerously_skip_permissions": false}' | ./post_task_review.sh
echo "Exit code: $?"

# Test 4: Post-task review with skip-permissions
echo -e "\nTest 4: Post-task review WITH skip-permissions"
echo '{"tool_name": "Write", "file_path": "test.txt", "session_id": "test123", "dangerously_skip_permissions": true}' | ./post_task_review.sh
echo "Exit code: $?"

# Check audit logs
echo -e "\nChecking audit logs:"
AUDIT_LOG="$HOME/.claude/hook_data/skip_permissions_audit.log"
if [ -f "$AUDIT_LOG" ]; then
    echo "Skip-permissions audit log contents:"
    tail -5 "$AUDIT_LOG"
else
    echo "No audit log found (this is expected if skip-permissions wasn't used)"
fi