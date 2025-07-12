# MCP Ref Documentation Search Hooks

This directory contains hooks that integrate the MCP Ref documentation search tool into the Claude Code workflow, providing intelligent keyword-based documentation searches during development.

## Overview

The MCP Ref hooks automatically:
- Extract keywords from code context
- Search relevant documentation before operations
- Provide error solutions from documentation
- Cache results for performance
- Suggest fixes based on documentation

## Components

### 1. `mcp_ref_hooks.json`
Main configuration file defining:
- Keyword extraction strategies
- Search strategies for different contexts
- Hook integration points
- Cache configuration
- Performance settings

### 2. `pre_tool_documentation.py`
Runs before tool execution to:
- Extract keywords from file paths and operations
- Generate context-aware search queries
- Search and cache documentation
- Store results for other hooks

### 3. `error_documentation.py`
Analyzes errors to:
- Extract keywords from error messages and stack traces
- Search for error solutions
- Suggest fixes based on patterns
- Provide documentation links

### 4. `mcp_ref_wrapper.py`
Direct interface to MCP Ref tool for:
- Programmatic documentation searches
- URL content fetching
- Keyword extraction from code
- Command-line usage

### 5. `integrate_mcp_hooks.py`
Integration script to:
- Add MCP hooks to main settings.json
- Configure hook priorities
- Set up debugging options

## Usage

### Automatic Hook Activation

The hooks activate automatically during:
- **Pre-Tool**: Before Write, Edit, Task operations
- **Error**: When errors occur
- **Post-Read**: After reading files
- **Debug**: During debugging sessions

### Manual Command Line Usage

```bash
# Search documentation
python scripts/mcp_ref_hooks/mcp_ref_wrapper.py search "How to implement rate limiting" "rate,limit,api,python" public

# Search error solutions
python scripts/mcp_ref_hooks/mcp_ref_wrapper.py error "ModuleNotFoundError" "No module named 'anthropic'"

# Fetch URL content
python scripts/mcp_ref_hooks/mcp_ref_wrapper.py url "https://docs.anthropic.com/api/rate-limits"
```

### Integration with Existing Hooks

To integrate MCP hooks into your settings:

```bash
cd /mnt/c/Users/JackTheRipper/Desktop/"(00) ClaudeCode"/Anthropic_Flashcards
source venv/bin/activate
python scripts/mcp_ref_hooks/integrate_mcp_hooks.py
```

## Keyword Extraction Strategies

### Code Context
- Import statements
- Class and function names  
- Variable types
- API references
- Error keywords

### Documentation Context
- Headings and sections
- Code block languages
- Technical terms
- API method names

### Error Context
- Exception types
- Module names
- Function names in stack trace
- Error message keywords

## Search Strategies

### 1. Code Documentation
- Triggers on import/module errors
- Searches public API docs
- Focuses on usage examples

### 2. Error Resolution
- Triggers on exceptions
- Searches for solutions
- Provides fix suggestions

### 3. Best Practices
- Triggers on design patterns
- Searches guidelines
- Focuses on recommendations

### 4. Internal Codebase
- Triggers on project modules
- Searches private docs
- Focuses on implementation

## Cache Management

Documentation results are cached in `.claude/mcp_ref_cache/`:
- TTL: 24 hours
- Max size: 100MB
- Compression enabled
- Key strategy: Query + keywords hash

## Performance Optimization

- Parallel searches (max 3 concurrent)
- 30-second timeout per search
- Retry with exponential backoff
- Background caching

## Debugging

Enable debug logging:
```bash
export MCP_REF_DEBUG=true
```

View logs:
```bash
tail -f .claude/logs/mcp_ref_hooks.log
```

## Examples

### Example 1: Pre-Write Documentation
When creating a new API client:
```
[MCP REF] Extracting keywords: ['api', 'client', 'python', 'initialization']
[MCP REF] Query: Creating new .py file best practices for api client
[MCP REF] Found 3 relevant documents
```

### Example 2: Error Solution
When encountering an import error:
```
[MCP REF ERROR] Analyzing error: ModuleNotFoundError
[MCP REF ERROR] Keywords: ['ModuleNotFoundError', 'anthropic', 'import']
[MCP REF ERROR] Found 2 potential fixes:
  1. Install missing module
     Command: pip install anthropic
     Confidence: 90%
```

### Example 3: API Validation
When using an API:
```
[MCP REF] Validating API usage against documentation
[MCP REF] Checking: APIClient.initialize() parameters
[MCP REF] Documentation confirms correct usage
```

## Troubleshooting

### Hooks Not Activating
1. Check hooks are enabled in settings.json
2. Verify virtual environment is activated
3. Check file permissions on scripts

### Search Failures
1. Check network connectivity
2. Verify MCP tool availability
3. Review error logs

### Cache Issues
1. Clear cache: `rm -rf .claude/mcp_ref_cache`
2. Check disk space
3. Verify write permissions

## Future Enhancements

- [ ] Integration with more MCP tools
- [ ] Machine learning for keyword relevance
- [ ] Multi-language documentation support
- [ ] Offline documentation cache
- [ ] Custom documentation sources
- [ ] Interactive documentation browser
- [ ] Documentation quality scoring
- [ ] Auto-generate documentation from code

Last Updated: 2025-01-10