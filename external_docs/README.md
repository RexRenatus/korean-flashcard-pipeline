# External Documentation

This directory contains documentation from external sources that are relevant to the flashcard pipeline project. These are reference materials from APIs, services, and tools we integrate with.

## Purpose

Keeping local copies of external documentation helps with:
- Offline reference
- Version tracking (APIs change)
- Quick access during development
- Understanding integration points

## Structure

```
external_docs/
├── anthropic/     # Anthropic/Claude API documentation
├── openrouter/    # OpenRouter API documentation
└── README.md      # This file
```

## Documentation Sources

### Anthropic Documentation (`/anthropic`)
- Source: https://docs.anthropic.com/
- Contains: Claude API references, best practices
- Updated: As needed when API changes
- Key files: API endpoints, model information, pricing

### OpenRouter Documentation (`/openrouter`)
- Source: https://openrouter.ai/docs
- Contains: OpenRouter API integration guides
- Updated: When integration changes
- Key files: Authentication, model routing, rate limits

## Usage Guidelines

### When to Update
1. **API Changes**: When providers announce changes
2. **New Features**: When new capabilities are added
3. **Integration Issues**: When docs help solve problems
4. **Major Updates**: Before major development phases

### How to Update
1. Download or copy relevant documentation
2. Include source URL and date in the file
3. Add notes about what changed
4. Update this README with changes

### What to Include
- API endpoint documentation
- Authentication guides
- Rate limit information
- Error code references
- Best practices
- Integration examples

### What NOT to Include
- Entire websites
- Marketing materials
- Unrelated documentation
- Proprietary information
- Large media files

## File Naming Convention

```
source_topic_YYYYMMDD.md
```

Examples:
- `anthropic_api_endpoints_20240109.md`
- `openrouter_authentication_20240109.md`

## Important Notes

### Copyright
- These documents belong to their respective owners
- Used for reference only
- Not distributed with the project
- Respect terms of service

### Accuracy
- External docs may be outdated
- Always verify with official sources
- Test actual behavior
- Document discrepancies

### Security
- Don't store API keys or secrets
- Remove any example credentials
- Sanitize personal information
- Keep security guides private

## Quick Reference

### Key Integration Points

#### OpenRouter
- Base URL: `https://openrouter.ai/api/v1`
- Auth: Bearer token in header
- Models: Access to multiple AI models
- Rate limits: Vary by plan

#### Anthropic (via OpenRouter)
- Model: Claude 3 Sonnet/Opus
- Context: 200k tokens
- Best for: Complex language tasks
- Pricing: Per token

## Maintenance

### Regular Tasks
- Check for API updates monthly
- Remove outdated documentation
- Verify links still work
- Update integration code as needed

### Version Tracking
Keep notes on significant changes:
```markdown
## Change Log

### 2024-01-09
- Updated OpenRouter rate limits
- Added new Claude 3 Opus documentation

### 2023-12-15
- Initial documentation import
- Added authentication guides
```

## Finding Information

### Common Lookups
1. **Rate Limits**: Check `openrouter/rate_limits_*.md`
2. **Error Codes**: See `*/errors_*.md`
3. **Authentication**: Look in `*/auth_*.md`
4. **Endpoints**: Find in `*/api_reference_*.md`

### Search Tips
- Use grep for quick searches
- Check file dates for latest info
- Cross-reference with code usage
- Verify against official docs

## Contributing

When adding external documentation:
1. Ensure it's necessary for development
2. Include source attribution
3. Add entry to this README
4. Keep files organized
5. Remove when no longer needed

## Legal Notice

All external documentation remains the property of its respective owners and is used here for development reference only. This project does not claim ownership of any external documentation.