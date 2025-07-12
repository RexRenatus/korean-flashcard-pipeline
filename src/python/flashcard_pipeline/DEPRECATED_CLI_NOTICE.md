# CLI Deprecation Notice

## Overview
As part of the codebase refactoring, we have consolidated the multiple CLI implementations into a unified interface.

## Status of CLI Files

### ✅ Protected (DO NOT MODIFY)
- **`cli_v2.py`** - The main, feature-complete CLI implementation
  - Status: ACTIVE and PROTECTED
  - Contains all 5 phases of functionality
  - This file works perfectly and must not be modified

### 📦 Consolidated
- **`cli_unified.py`** - NEW unified entry point
  - Combines cli_v2 functionality with enhanced ingress features
  - Provides migration path from deprecated CLIs
  - Recommended for new usage

### ⚠️ Deprecated (To be removed in future release)
- **`pipeline_cli.py`** - Original basic CLI
  - Status: DEPRECATED
  - All functionality available in cli_v2.py
  - Use `cli_unified.py` or `cli_v2.py` instead

- **`cli_enhanced.py`** - Enhanced ingress CLI
  - Status: PARTIALLY DEPRECATED
  - Unique ingress features moved to `cli/ingress_enhanced.py`
  - Available through `cli_unified.py` as `ingress-plus` commands

## Migration Guide

### From pipeline_cli.py
```bash
# Old
python -m flashcard_pipeline.pipeline_cli process input.csv

# New (using unified CLI)
python -m flashcard_pipeline.cli_unified process input.csv

# Or use cli_v2 directly
python -m flashcard_pipeline.cli_v2 process input.csv
```

### From cli_enhanced.py
```bash
# Old
python -m flashcard_pipeline.cli_enhanced ingress import vocab.csv

# New (using unified CLI)
python -m flashcard_pipeline.cli_unified ingress-plus import vocab.csv

# Or use cli_v2's import functionality
python -m flashcard_pipeline.cli_v2 process vocab.csv
```

## Recommendation
1. For new code, use `cli_unified.py` as the entry point
2. For existing scripts using `cli_v2.py`, no changes needed - it remains unchanged
3. Update any scripts using `pipeline_cli.py` or `cli_enhanced.py` to use the new unified interface

## Timeline
- Deprecated CLIs will be removed in version 2.0.0
- `cli_v2.py` will remain protected and unchanged
- `cli_unified.py` will become the primary entry point