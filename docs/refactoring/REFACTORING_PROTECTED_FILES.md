# Protected Files During Refactoring

This document lists files and functionality that must be preserved during the refactoring process.

## Protected Scripts

### 1. CLI v2 Tool (CRITICAL - DO NOT MODIFY)
- **File**: `src/python/flashcard_pipeline/cli_v2.py`
- **Reason**: This is the script that generates the vocabulary output files, including `vocabulary_1000_processed.tsv`
- **Protection Level**: FULL - No modifications allowed
- **Dependencies**: Must ensure all its imports remain functional

### 2. Core Processing Pipeline
- **Files**: Any files imported by cli_v2.py that are essential for processing
- **Protection Level**: INTERFACE - Internal refactoring allowed but public APIs must remain stable

## Protected Output Format
- The TSV output format with columns: position, term, term_number, tab_name, primer, front, back, tags, honorific_level
- Must maintain exact same output structure

## Protected Workflows
1. The ability to run: `flashcard-pipeline process input.csv -o output.tsv`
2. All command-line arguments and options currently supported by cli_v2.py
3. The concurrent processing capability
4. The caching mechanism (can be improved but not broken)

## Files We Can Safely Refactor
- `cli.py` (old version)
- `cli_enhanced.py` (can merge features into new structure)
- Duplicate cache implementations
- Duplicate ingress services
- Standalone scripts (after verifying they're not critical)

Last Updated: 2025-01-11