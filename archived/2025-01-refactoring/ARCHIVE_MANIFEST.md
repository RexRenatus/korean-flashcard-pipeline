# Archive Manifest - 2025-01 Refactoring

This directory contains files that were consolidated during the January 2025 codebase refactoring.

## Archive Date: 2025-01-11

## Archived Files and Their Replacements

### API Client Consolidation
- **Archived**: `api_client.py`, `api_client_enhanced.py`
- **Replaced by**: `api/client.py`
- **Features preserved**: All features combined with dual-mode architecture

### Cache Service Consolidation
- **Archived**: `cache.py`, `cache_v2.py`
- **Replaced by**: `cache/service.py`
- **Features preserved**: All caching functionality with compression and TTL

### Ingress Service Consolidation
- **Archived**: `ingress.py`, `ingress_v2.py`, `ingress_service_enhanced.py`
- **Replaced by**: `services/ingress.py`
- **Features preserved**: All import modes, validation, and batch management

### Pipeline Consolidation
- **Archived**: `pipeline.py`, `pipeline_orchestrator.py`
- **Replaced by**: `pipeline/orchestrator.py`
- **Features preserved**: All processing modes with improved architecture

### CLI Consolidation
- **Archived**: `pipeline_cli.py`, `cli_enhanced.py`
- **Replaced by**: `cli_unified.py` (wraps protected `cli_v2.py`)
- **Features preserved**: All CLI functionality, enhanced ingress moved to `cli/ingress_enhanced.py`

### Output Parser Consolidation
- **Note**: `output_parser.py` and `output_parsers.py` were already removed
- **Replaced by**: `parsers/output.py`

## Important Notes

1. **cli_v2.py is PROTECTED** - This file was NOT modified or archived as it works perfectly for vocabulary generation
2. All archived files are kept for reference - do not delete
3. The new modular structure maintains backward compatibility
4. Import statements in existing code may need updates

## Migration Instructions

See `/REFACTORING_SUMMARY.md` for detailed migration instructions.