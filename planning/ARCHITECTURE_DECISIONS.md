# Architecture Decisions

**Last Updated**: 2025-01-07

## Purpose

This document records all significant architectural decisions made during the Korean Language Flashcard Pipeline project. Each decision is documented in Architecture Decision Record (ADR) format to capture the context, alternatives considered, and rationale.

## ADR Template

```markdown
## ADR-XXX: [Decision Title]

**Status**: [Proposed | Accepted | Deprecated | Superseded]  
**Date**: YYYY-MM-DD  
**Deciders**: [List of people involved]  

### Context
[What is the issue that we're seeing that is motivating this decision?]

### Decision
[What is the change that we're proposing and/or doing?]

### Alternatives Considered
1. **Option A**: [Description]
   - Pros: [List]
   - Cons: [List]
2. **Option B**: [Description]
   - Pros: [List]
   - Cons: [List]

### Consequences
[What becomes easier or more difficult because of this change?]
```

---

## ADR-001: Use Rust for Core Pipeline with Python for API Integration

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Development team based on requirements analysis  

### Context
We need a high-performance processing pipeline that can handle 500+ vocabulary items efficiently while integrating with the OpenRouter API. The system requires both performance for data processing and flexibility for API integration.

### Decision
Use Rust for the core pipeline (data processing, caching, orchestration) and Python for API integration (OpenRouter client, rate limiting).

### Alternatives Considered
1. **Pure Python Implementation**
   - Pros: Single language, easier development, rich ecosystem
   - Cons: Slower performance, GIL limitations, higher memory usage

2. **Pure Rust Implementation**
   - Pros: Maximum performance, single binary, type safety
   - Cons: Limited HTTP client options, harder API integration, longer development time

3. **Go Implementation**
   - Pros: Good performance, built-in concurrency, simple deployment
   - Cons: Less ecosystem support, team unfamiliarity, garbage collection pauses

### Consequences
- **Positive**: Optimal performance for data processing, mature API libraries in Python
- **Negative**: Complexity of cross-language integration, two runtime environments
- **Mitigation**: Use PyO3 for seamless integration, single binary deployment

---

## ADR-002: Embed Python Using PyO3 Instead of IPC

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Architecture team  

### Context
The Rust core needs to communicate with Python API client. We need a reliable, performant way to bridge these languages.

### Decision
Embed Python interpreter directly in Rust using PyO3, allowing direct function calls and shared memory.

### Alternatives Considered
1. **JSON-RPC over Unix Sockets**
   - Pros: Language agnostic, clear boundaries, easier testing
   - Cons: Serialization overhead, complex process management, IPC complexity

2. **REST API Communication**
   - Pros: Standard HTTP, easy debugging, microservice pattern
   - Cons: Network overhead, requires service management, complex deployment

3. **gRPC Communication**
   - Pros: Efficient binary protocol, schema validation, streaming support
   - Cons: Additional complexity, protobuf overhead, learning curve

### Consequences
- **Positive**: Direct function calls, shared memory, single process deployment
- **Negative**: Python GIL constraints, complex error handling, version coupling
- **Mitigation**: Careful GIL management, comprehensive error translation

---

## ADR-003: Use SQLite for Local Caching

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on caching requirements and deployment simplicity  

### Context
We need persistent caching for API responses to minimize costs and improve performance. The cache must handle 1000s of entries efficiently.

### Decision
Use SQLite with memory-mapped I/O for all caching needs, with separate tables for Stage 1 and Stage 2 results.

### Alternatives Considered
1. **Redis**
   - Pros: Fast, built for caching, TTL support, distributed capable
   - Cons: Separate service, memory requirements, deployment complexity

2. **File-based Cache**
   - Pros: Simple, no dependencies, easy debugging
   - Cons: File system limitations, no queries, manual cleanup

3. **RocksDB**
   - Pros: Embedded, high performance, compression
   - Cons: Complex API, overkill for our needs, larger binary

### Consequences
- **Positive**: Zero deployment overhead, SQL queries, ACID compliance, portable
- **Negative**: Single-node only, no built-in TTL, file locking concerns
- **Mitigation**: Implement manual TTL if needed, use WAL mode for concurrency

---

## ADR-004: Permanent Cache Strategy (No TTL)

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on user requirements for cost optimization  

### Context
API calls are expensive ($0.15 per 1000 tokens). Users want to minimize costs by never repeating the same API call.

### Decision
Implement permanent caching with no automatic expiration. Cache invalidation only happens through explicit user action.

### Alternatives Considered
1. **30-day TTL**
   - Pros: Fresh data, automatic cleanup, prevents stale results
   - Cons: Unnecessary API costs, user specifically wants permanent cache

2. **Content-based Invalidation**
   - Pros: Smart updates, fresh when needed
   - Cons: Complex implementation, still causes API calls

3. **Manual Versioning**
   - Pros: User control, explicit updates
   - Cons: Requires user awareness, version management

### Consequences
- **Positive**: Maximum cost savings, predictable behavior, simple implementation
- **Negative**: Potential stale data, manual cleanup needed, growing database
- **Mitigation**: Provide cache statistics, easy cache clearing commands

---

## ADR-005: TSV Output Format for Anki

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on Anki import requirements  

### Context
Generated flashcards need to be imported into Anki. We need a format that preserves all metadata and supports Anki's features.

### Decision
Use TSV (Tab-Separated Values) format with specific column structure matching Anki's import expectations.

### Alternatives Considered
1. **Anki Package Format (.apkg)**
   - Pros: Direct import, includes media, preserves all settings
   - Cons: Complex format, requires Anki libraries, binary format

2. **JSON Export**
   - Pros: Structured data, extensible, machine readable
   - Cons: Requires conversion tool, not native Anki format

3. **CSV Format**
   - Pros: Standard format, Excel compatible
   - Cons: Comma escaping issues, less reliable parsing

### Consequences
- **Positive**: Native Anki support, simple format, human readable
- **Negative**: No media support, limited formatting, character escaping needed
- **Mitigation**: Careful escaping, clear documentation, import templates

---

## ADR-006: Two-Stage Pipeline Architecture

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on API design and separation of concerns  

### Context
The flashcard generation requires two distinct AI operations: semantic analysis and card generation. These have different inputs/outputs and caching needs.

### Decision
Implement a two-stage pipeline where each stage can be cached independently and has its own retry logic.

### Alternatives Considered
1. **Single API Call**
   - Pros: Simpler implementation, one round trip
   - Cons: Can't cache stages separately, all-or-nothing processing

2. **Multi-Stage Pipeline (3+ stages)**
   - Pros: More granular control, specialized processing
   - Cons: Over-engineering, more API calls, complex orchestration

3. **Parallel Processing**
   - Pros: Faster for independent operations
   - Cons: Stages are dependent, can't parallelize

### Consequences
- **Positive**: Independent caching, granular retry, clear separation
- **Negative**: Two API calls per item, more complex orchestration
- **Mitigation**: Efficient caching, batch processing optimization

---

## ADR-007: Batch Processing Over Streaming

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on user's sporadic usage pattern  

### Context
User processes vocabulary in batches of 500+ items occasionally, not continuous streams.

### Decision
Optimize for batch processing with progress tracking rather than streaming/real-time processing.

### Alternatives Considered
1. **Streaming Pipeline**
   - Pros: Lower memory usage, real-time results
   - Cons: Complex implementation, not needed for use case

2. **Queue-based Processing**
   - Pros: Scalable, resilient, distributed capable
   - Cons: Over-engineering, deployment complexity

3. **Hybrid Approach**
   - Pros: Flexible, handles both patterns
   - Cons: Complex code, maintenance burden

### Consequences
- **Positive**: Simpler implementation, better progress tracking, checkpoint support
- **Negative**: Higher memory usage during processing, not suitable for continuous flow
- **Mitigation**: Chunked processing, memory limits, clear documentation

---

## ADR-008: CLI Interface as Primary UI

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: MVP scope decision  

### Context
Users need a way to interact with the pipeline. We need to balance functionality with development time.

### Decision
Implement a command-line interface (CLI) as the primary user interface for the MVP.

### Alternatives Considered
1. **Web UI**
   - Pros: Better UX, visual progress, remote access
   - Cons: Significant development time, deployment complexity

2. **Desktop GUI**
   - Pros: Native feel, file dialogs, rich interactions
   - Cons: Platform-specific, complex packaging

3. **API-only**
   - Pros: Maximum flexibility, integration-ready
   - Cons: No direct user interface, requires client development

### Consequences
- **Positive**: Fast development, scriptable, no deployment overhead
- **Negative**: Less user-friendly, terminal requirement, limited visualizations
- **Mitigation**: Clear help text, progress bars, colored output

---

## ADR-009: Use OpenRouter Presets for Consistency

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on user's API examples  

### Context
OpenRouter offers both raw model access and curated presets. User provided specific preset names in requirements.

### Decision
Use OpenRouter's presets (@preset/nuance-creator, @preset/nuance-flashcard-generator) exclusively.

### Alternatives Considered
1. **Direct Model Access**
   - Pros: More control, custom prompts, flexibility
   - Cons: Inconsistent results, more complexity, prompt engineering

2. **Custom Fine-tuned Model**
   - Pros: Optimized for task, consistent results
   - Cons: High cost, training time, maintenance

3. **Multiple Model Options**
   - Pros: User choice, fallback options
   - Cons: Testing complexity, inconsistent output formats

### Consequences
- **Positive**: Consistent results, no prompt engineering, maintained by OpenRouter
- **Negative**: Less control, preset dependency, potential preset changes
- **Mitigation**: Version documentation, output validation, preset monitoring

---

## ADR-010: Error Quarantine System

**Status**: Accepted  
**Date**: 2025-01-07  
**Deciders**: Based on need for resilient batch processing  

### Context
In batches of 500+ items, some may fail due to API errors, rate limits, or data issues. We need a way to handle failures without stopping the entire batch.

### Decision
Implement a quarantine system where failed items are isolated after max retries, allowing the batch to complete.

### Alternatives Considered
1. **Fail Fast**
   - Pros: Simple, immediate feedback
   - Cons: One failure stops everything, poor user experience

2. **Infinite Retry**
   - Pros: Eventually succeeds
   - Cons: Can hang forever, wastes API calls

3. **Skip Silently**
   - Pros: Always completes
   - Cons: Data loss, user unaware of failures

### Consequences
- **Positive**: Resilient processing, clear failure reporting, can retry quarantined items
- **Negative**: Partial results, requires failure handling, complex state management
- **Mitigation**: Clear reporting, easy re-processing, failure analysis tools

---

## Decision Log

| ADR | Decision | Status | Date |
|-----|----------|--------|------|
| 001 | Rust + Python Architecture | Accepted | 2025-01-07 |
| 002 | PyO3 Embedding | Accepted | 2025-01-07 |
| 003 | SQLite Caching | Accepted | 2025-01-07 |
| 004 | Permanent Cache | Accepted | 2025-01-07 |
| 005 | TSV Output Format | Accepted | 2025-01-07 |
| 006 | Two-Stage Pipeline | Accepted | 2025-01-07 |
| 007 | Batch Processing | Accepted | 2025-01-07 |
| 008 | CLI Interface | Accepted | 2025-01-07 |
| 009 | OpenRouter Presets | Accepted | 2025-01-07 |
| 010 | Error Quarantine | Accepted | 2025-01-07 |

---

## Future Decisions Needed

1. **Monitoring Strategy**: How to collect and expose metrics
2. **Deployment Method**: Binary distribution vs Docker vs package managers  
3. **Configuration Management**: File-based vs environment vs CLI args
4. **Logging Standards**: Format, levels, destinations
5. **Testing Strategy**: Unit vs integration vs end-to-end balance
6. **Version Migration**: How to handle cache/schema updates between versions
7. **Security Model**: API key storage, secure communication
8. **Performance Targets**: Specific benchmarks and optimization priorities