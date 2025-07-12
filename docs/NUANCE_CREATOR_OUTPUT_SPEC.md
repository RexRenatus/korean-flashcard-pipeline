# Nuance Creator Output Specification

## Overview

This document defines the expected output format from the Stage 1 Nuance Creator API. The nuance creator analyzes Korean vocabulary items and produces rich, structured data for flashcard generation.

## Output Format

The output is a JSON object with the following structure:

```json
{
  "term_number": 1,
  "term": "남성[nam.sʌŋ]",
  "ipa": "[nam.sʌŋ]",
  "pos": "noun",
  "primary_meaning": "adult male person; man",
  "other_meanings": "masculine gender (grammatical); masculinity (abstract concept)",
  "metaphor": "A sturdy oak tree standing tall in a forest clearing",
  "metaphor_noun": "oak tree",
  "metaphor_action": "stands tall",
  "suggested_location": "forest clearing",
  "anchor_object": "oak tree",
  "anchor_sensory": "rough bark texture under fingertips",
  "explanation": "The oak tree represents traditional masculine strength and presence, standing prominently like the social role of adult males",
  "usage_context": null,
  "comparison": {
    "vs": "남자[nam.dʒa]",
    "nuance": "남성 is formal/clinical (adult male); 남자 is casual everyday term (boy/man/guy)"
  },
  "homonyms": [
    {
      "hanja": "男性",
      "reading": "남성",
      "meaning": "male gender/masculinity",
      "differentiator": "same word - hanja shows meaning components: 男 (male) + 性 (nature/gender)"
    }
  ],
  "korean_keywords": ["남성", "남자", "여성", "성별"]
}
```

## Field Definitions

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `term_number` | integer | Yes | Sequential number of the term in the batch |
| `term` | string | Yes | Korean term with pronunciation in brackets |
| `ipa` | string | Yes | IPA pronunciation notation |
| `pos` | string | Yes | Part of speech (noun, verb, adjective, etc.) |
| `primary_meaning` | string | Yes | Main English translation/definition |
| `other_meanings` | string | No | Secondary meanings or uses |

### Memory Palace Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metaphor` | string | Yes | Complete metaphorical scene description |
| `metaphor_noun` | string | Yes | Key noun from the metaphor |
| `metaphor_action` | string | Yes | Key action from the metaphor |
| `suggested_location` | string | Yes | Memory palace location suggestion |
| `anchor_object` | string | Yes | Physical object for memory anchoring |
| `anchor_sensory` | string | Yes | Sensory detail for stronger memory encoding |
| `explanation` | string | Yes | How the metaphor relates to the meaning |

### Context Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `usage_context` | string/null | No | Specific contexts where the term is used |
| `comparison` | object | No | Comparison with similar terms |
| `comparison.vs` | string | No | Term being compared against |
| `comparison.nuance` | string | No | Explanation of nuanced differences |

### Etymology Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `homonyms` | array | No | List of homonyms or related hanja |
| `homonyms[].hanja` | string | Yes | Chinese characters |
| `homonyms[].reading` | string | Yes | Korean reading of hanja |
| `homonyms[].meaning` | string | Yes | Meaning of this specific hanja combination |
| `homonyms[].differentiator` | string | Yes | How to distinguish from other homonyms |

### Search Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `korean_keywords` | array | Yes | Related Korean terms for searching |

## Value Constraints

### Part of Speech (pos)
Valid values:
- `noun` - 명사
- `verb` - 동사
- `adjective` - 형용사
- `adverb` - 부사
- `particle` - 조사
- `determiner` - 관형사
- `numeral` - 수사
- `pronoun` - 대명사
- `interjection` - 감탄사

### String Length Limits
- `term`: max 100 characters
- `primary_meaning`: max 200 characters
- `other_meanings`: max 500 characters
- `metaphor`: max 300 characters
- `explanation`: max 500 characters
- `anchor_sensory`: max 200 characters

### Array Limits
- `homonyms`: max 5 entries
- `korean_keywords`: max 10 entries

## Null Handling

Fields that can be null:
- `other_meanings` - When term has only one clear meaning
- `usage_context` - When no specific context restrictions
- `comparison` - When no similar terms to compare
- `homonyms` - When no homonyms exist

## Examples

### Basic Word
```json
{
  "term_number": 1,
  "term": "책[tɕʰɛk]",
  "ipa": "[tɕʰɛk]",
  "pos": "noun",
  "primary_meaning": "book",
  "other_meanings": "written work; volume",
  "metaphor": "A treasure chest of knowledge sitting on a wooden shelf",
  "metaphor_noun": "treasure chest",
  "metaphor_action": "sits waiting",
  "suggested_location": "library",
  "anchor_object": "treasure chest",
  "anchor_sensory": "smooth paper pages rustling",
  "explanation": "Books contain treasures of knowledge waiting to be discovered",
  "usage_context": null,
  "comparison": null,
  "homonyms": [
    {
      "hanja": "冊",
      "reading": "책",
      "meaning": "book/volume",
      "differentiator": "single hanja meaning book"
    }
  ],
  "korean_keywords": ["책", "도서", "서적", "책자"]
}
```

### Complex Term with Comparison
```json
{
  "term_number": 2,
  "term": "아름답다[a.ɾɯm.dap.t͈a]",
  "ipa": "[a.ɾɯm.dap.t͈a]",
  "pos": "adjective",
  "primary_meaning": "beautiful; lovely",
  "other_meanings": "aesthetically pleasing; gorgeous",
  "metaphor": "A sunrise painting the sky with golden brushstrokes",
  "metaphor_noun": "sunrise",
  "metaphor_action": "paints",
  "suggested_location": "mountaintop",
  "anchor_object": "golden sun",
  "anchor_sensory": "warm light on your face",
  "explanation": "Beauty that takes your breath away like a perfect sunrise",
  "usage_context": "Used for visual beauty, scenery, and abstract beauty",
  "comparison": {
    "vs": "예쁘다[je.p͈ɯ.da]",
    "nuance": "아름답다 is profound/majestic beauty; 예쁘다 is cute/pretty"
  },
  "homonyms": null,
  "korean_keywords": ["아름답다", "예쁘다", "곱다", "화려하다"]
}
```

## Database Storage

The nuance creator output should be stored in the `processing_results` table with the following mapping:

```sql
-- Each field stored as a separate row
INSERT INTO processing_results (task_id, stage, result_type, result_key, result_value)
VALUES 
  (?, 1, 'core', 'term', ?),
  (?, 1, 'core', 'ipa', ?),
  (?, 1, 'core', 'pos', ?),
  (?, 1, 'core', 'primary_meaning', ?),
  (?, 1, 'memory', 'metaphor', ?),
  (?, 1, 'memory', 'anchor_object', ?),
  -- etc for all fields
```

For complex objects like `comparison` and `homonyms`, store as JSON strings:
```sql
INSERT INTO processing_results (task_id, stage, result_type, result_key, result_value)
VALUES 
  (?, 1, 'comparison', 'data', '{"vs": "남자", "nuance": "..."}'),
  (?, 1, 'homonyms', 'data', '[{"hanja": "男性", ...}]');
```

## Validation Rules

1. **Required Fields**: All fields marked as required must be present and non-empty
2. **IPA Format**: Must be enclosed in square brackets
3. **Term Format**: Korean text optionally followed by pronunciation in brackets
4. **Arrays**: Must not be empty if present (use null instead)
5. **Homonyms**: Each entry must have all required subfields
6. **Korean Keywords**: Must include the original term as first entry

## Error Handling

If the nuance creator returns invalid data:
1. Log the complete response for debugging
2. Extract any salvageable fields
3. Mark the task as failed with specific error details
4. Allow retry with exponential backoff

## Version History

- **v1.0** (2024-01-08): Initial specification based on example output
- Future versions may add fields for:
  - Formality levels
  - Regional variations
  - Historical etymology
  - Frequency data