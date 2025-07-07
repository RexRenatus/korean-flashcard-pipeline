# MVP Definition

**Last Updated**: 2025-01-07

## Purpose

This document defines the Minimum Viable Product (MVP) features versus nice-to-have features based on the completed requirements questionnaire.

## MVP Features (Must Have)

### 1. Core Pipeline Functionality
- **Two-stage processing**: Stage 1 (semantic analysis) → Stage 2 (flashcard generation)
- **Batch processing**: Support for 500+ vocabulary items per batch
- **CSV input parsing**: Extract Position and Hangul columns from input files
- **TSV output generation**: Anki-compatible format with all required fields

### 2. API Integration
- **OpenRouter client**: Connect to Claude Sonnet 4 via OpenRouter API
- **Rate limiting**: Respect API limits with intelligent throttling
- **Error handling**: 3 retry attempts with exponential backoff
- **Request validation**: Ensure all API calls are properly formatted

### 3. Caching System
- **Permanent Stage 1 cache**: Store semantic analysis results indefinitely
- **Permanent Stage 2 cache**: Store generated flashcards indefinitely
- **Cache lookup**: Check cache before making API calls
- **Failed item tracking**: Quarantine items that fail after 3 attempts

### 4. Database
- **SQLite database**: All 8 tables from DATABASE_DESIGN.md
- **Connection pooling**: Efficient database access
- **Transaction management**: Ensure data consistency
- **Basic migrations**: Schema versioning and updates

### 5. CLI Interface
- **Process command**: `flashcard-cli process input.csv output.tsv`
- **Status command**: `flashcard-cli status` (show processing stats)
- **Retry command**: `flashcard-cli retry` (process failed items)
- **Progress display**: Real-time progress bar during processing

### 6. Error Management
- **Comprehensive logging**: All operations logged with appropriate levels
- **Error reports**: Generate user-friendly error summaries
- **Failed item quarantine**: Separate table for inspection
- **Partial progress saving**: Resume capability after interruption

### 7. Basic Quality Control
- **Input validation**: Verify CSV format and required columns
- **Output validation**: Ensure TSV format is correct
- **Duplicate detection**: Prevent processing same item multiple times

## Nice-to-Have Features (Phase 2+)

### 1. Advanced UI/UX
- **Web interface**: Browser-based UI for easier interaction
- **Bulk operations UI**: Manage multiple batches simultaneously
- **Analytics dashboard**: Visualize processing statistics
- **Content moderation workflow**: Review and approve generated cards

### 2. Advanced Processing
- **Batch scheduling/queuing**: Schedule processing for specific times
- **Quality scoring**: Automated quality assessment of generated cards
- **Parallel processing**: Process multiple items concurrently
- **Custom prompts**: Allow users to modify generation prompts

### 3. Integration Features
- **REST API**: Allow other tools to integrate
- **Webhook notifications**: Send updates to external systems
- **Direct Anki integration**: Create .apkg files directly
- **Export to multiple formats**: JSON, Excel, PDF

### 4. Advanced Analytics
- **Cost tracking**: Monitor API usage and costs
- **Performance metrics**: Detailed timing and efficiency stats
- **Quality metrics**: Track card quality over time
- **User activity tracking**: Who processed what and when

### 5. Multi-user Support
- **User authentication**: Login system
- **Project management**: Separate projects per user
- **Role-based access**: Different permissions for different users
- **Collaboration features**: Share vocabularies and cards

### 6. Advanced Caching
- **Cache warming**: Pre-generate common vocabulary
- **Cache export/import**: Share cache between instances
- **Selective cache clearing**: Clear specific items only
- **Cache compression**: Reduce storage requirements

## Implementation Priority

### Phase 1 (MVP) - 4-6 weeks
1. Set up project infrastructure
2. Implement database and caching
3. Build OpenRouter client with rate limiting
4. Create two-stage processing pipeline
5. Develop CLI interface
6. Add error handling and logging
7. Test with sample data

### Phase 2 (Enhanced) - 2-3 weeks
1. Add batch scheduling
2. Implement quality scoring
3. Build analytics dashboard
4. Add bulk operations

### Phase 3 (Integration) - 3-4 weeks
1. Create REST API
2. Add web interface
3. Implement export formats
4. Add webhook support

## Success Criteria for MVP

1. **Functional**: Can process 500+ vocabulary items from CSV to TSV
2. **Reliable**: Handles errors gracefully with retry logic
3. **Efficient**: Uses caching to minimize API costs
4. **Usable**: Clear CLI commands with helpful output
5. **Maintainable**: Well-documented code with tests

## Technical Decisions for MVP

1. **Rust**: Core pipeline for performance and reliability
2. **Python**: API client for easier HTTP handling
3. **SQLite**: Simple, file-based database perfect for caching
4. **CLI-first**: Focus on functionality before UI
5. **Batch processing**: Better for sporadic usage pattern

## Next Steps

With this MVP definition, we can now:
1. Create detailed system architecture (SYSTEM_DESIGN.md)
2. Define API specifications
3. Design the two-stage processing pipeline
4. Plan implementation phases