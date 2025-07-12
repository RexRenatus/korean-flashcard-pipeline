# Flashcard Output Specification

## Overview

This document defines the expected output format from the Stage 2 Flashcard Generator. The generator takes the nuanced analysis from Stage 1 and produces multiple flashcards per vocabulary item in TSV (Tab-Separated Values) format.

## TSV Format

### Column Headers
```
position	term	term_number	tab_name	primer	front	back	tags	honorific_level
```

### Column Definitions

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `position` | integer | Sequential position in output file | 1, 2, 3... |
| `term` | string | Korean term with pronunciation | 남성[nam.sʌŋ] |
| `term_number` | integer | Original term number from input | 1 |
| `tab_name` | string | Card type/category | Scene, Usage-Comparison, Hanja |
| `primer` | string | Memory palace navigation instructions | You enter your clean... |
| `front` | string | Question/prompt for flashcard front | Stepping through another portal... |
| `back` | string | Answer/content for flashcard back | A sturdy oak tree stands tall... |
| `tags` | string | Comma-separated metadata tags | term:남성,pos:noun,card:Scene |
| `honorific_level` | string | Formality level (if applicable) | formal, casual, neutral |

## Card Types (tab_name)

### 1. Scene Card
- **Purpose**: Introduce the metaphorical scene and core meaning
- **Front**: Prompts to identify the key metaphorical object
- **Back**: Detailed scene description linking metaphor to meaning
- **Tags**: Include `concept:metaphor` and metaphor object

### 2. Usage-Comparison Card
- **Purpose**: Show practical usage and compare with similar terms
- **Front**: Asks about differences from similar terms
- **Back**: Real-world usage examples with nuanced comparisons
- **Tags**: Include `comparison_term:` with the compared term

### 3. Hanja Card
- **Purpose**: Explore Chinese character etymology
- **Front**: Prompts to examine character components
- **Back**: Detailed breakdown of hanja meanings and origins
- **Tags**: Include `hanja` and individual `character:` tags

### 4. Additional Card Types
- **Grammar**: Grammatical patterns and conjugations
- **Formal-Casual**: Formality level variations
- **Example**: Sentence examples with translations
- **Cultural**: Cultural context and usage notes

## Content Structure

### Primer Format
Standard memory palace navigation:
```
You enter your clean, pleasant-smelling memory room.
1. Walk to the cabinet labeled 'KOREAN'.
2. Open the drawer labeled 'TERMS'.
3. Pull out the binder marked '[POS]'.
4. Flip to the tab for 'Term #[N]: [TERM]' and prepare to step through the portal.
```

Variables:
- `[POS]`: Part of speech in caps (NOUN, VERB, etc.)
- `[N]`: Term number
- `[TERM]`: Korean term with pronunciation

### Front Content Guidelines
- **Scene**: "Stepping through another portal, you enter the [location]. What [sensory question]?"
- **Usage-Comparison**: "The [metaphor object] from the [location] pulses with meaning... How does it differ from [comparison term]?"
- **Hanja**: "The [metaphor object] from the [location] reveals hidden layers... What ancient meanings emerge?"

### Back Content Structure
1. **Opening**: Vivid sensory description of the scene/concept
2. **Core Content**: Main teaching point with examples
3. **Memory Hook**: Sensory detail that reinforces the connection
4. **Closing**: Summary or final insight

## Tag Format

Tags are comma-separated key:value pairs:
- `term:[korean_term]` - Always included
- `pos:[part_of_speech]` - Always included
- `card:[card_type]` - Card category
- `concept:[concept_type]` - For conceptual cards
- `metaphor:[object]` - Metaphor object name
- `comparison_term:[term]` - For comparison cards
- `hanja` - For hanja cards
- `character:[char]` - Individual hanja characters
- `level:[JLPT/TOPIK]` - Proficiency level
- `formality:[level]` - Formality level

## Example Output

```tsv
position	term	term_number	tab_name	primer	front	back	tags	honorific_level
1	남성[nam.sʌŋ]	1	Scene	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	Stepping through another portal, you enter the forest clearing. What single architectural feature demands your full attention?	A sturdy oak tree stands tall at the center, its broad trunk radiating ancient strength while rough bark catches golden sunlight. This towering presence perfectly captures how 남성[nam.sʌŋ] embodies adult male person—not just any man, but the formal, clinical designation used in medical charts and government forms. The tree's solid verticality mirrors the term's authoritative precision in distinguishing masculine gender both grammatically and as an abstract concept.	term:남성,pos:noun,card:Scene,concept:metaphor,metaphor:oak_tree	
2	남성[nam.sʌŋ]	1	Usage-Comparison	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	The oak tree from the forest clearing pulses with meaning as you explore how 남성[nam.sʌŋ] works in practice. How does it differ from 남자[nam.dʒa]?	Hospital marble echoes as staff announce "남성[nam.sʌŋ] 화장실[hwa.dʒaŋ.sil]"—the formal precision matching polished surfaces. Medical forms print "남성[nam.sʌŋ] 호르몬[ho.ɾɯ.mon]" in clinical black ink. Unlike everyday 남자[nam.dʒa] tossed around cafés and street corners, this oak-like term carries institutional weight—남성[nam.sʌŋ] is formal/clinical (adult male) while 남자[nam.dʒa] is the casual everyday term (boy/man/guy). The rough bark texture under fingertips reminds you how this distinction shapes every interaction.	term:남성,pos:noun,card:Usage-Comparison,comparison_term:남자	
3	남성[nam.sʌŋ]	1	Hanja	You enter your clean, pleasant-smelling memory room. 1. Walk to the cabinet labeled 'KOREAN'. 2. Open the drawer labeled 'TERMS'. 3. Pull out the binder marked 'NOUN'. 4. Flip to the tab for 'Term #1: 남성[nam.sʌŋ]' and prepare to step through the portal.	The oak tree from the forest clearing reveals hidden layers as you examine the Chinese characters. What ancient meanings emerge from the brushstrokes?	The hanja 男性[nam.sʌŋ] splits into two distinct components on rice paper—男[nam] (male) shows a field 田[tʰjen] above strength 力[njʌk̚], depicting traditional masculine labor, while 性[sʌŋ] (nature/gender) combines heart 心[sim] with life 生[sɛŋ]. Black ink bleeds slightly into fibrous paper as these ancient pictographs reveal how "male nature" became the formal designation for masculine gender. The musty smell of old scrolls mingles with fresh ink, grounding this clinical term in millennia of meaning.	term:남성,pos:noun,card:Hanja,hanja,character:男,character:性	
```

## Quality Requirements

### Content Length
- **Primer**: Standardized format, ~50-70 words
- **Front**: 15-30 words for clear, focused prompts
- **Back**: 80-150 words for rich, memorable content
- **Tags**: Comprehensive but concise metadata

### Sensory Details
Each card must include at least 2-3 sensory elements:
- Visual descriptions
- Tactile sensations
- Auditory elements
- Olfactory details (when appropriate)
- Kinesthetic actions

### Memory Palace Consistency
- Same entry sequence for all cards of a term
- Consistent location references
- Progressive building on previous cards
- Clear spatial navigation

### Language Precision
- Exact IPA pronunciation in brackets
- Accurate romanization
- Proper honorific level notation
- Correct grammatical terminology

## Database Storage

The flashcard data maps to the `flashcards` table:

```sql
-- Each TSV row becomes a flashcard record
INSERT INTO flashcards (
    vocabulary_id,
    task_id,
    card_number,
    deck_name,
    front_content,
    back_content,
    pronunciation_guide,
    tags,
    honorific_level,
    quality_score,
    is_published
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
```

Mapping:
- `position` → `card_number`
- `tab_name` → `deck_name`
- `primer` → stored separately or in metadata
- `front` → `front_content`
- `back` → `back_content`
- `term` → extract pronunciation for `pronunciation_guide`
- `tags` → `tags` (stored as JSON array)
- `honorific_level` → `honorific_level`

## Validation Rules

### Required Validations
1. **Column Count**: Exactly 9 columns per row
2. **Position**: Sequential integers starting from 1
3. **Term Format**: Korean text with [pronunciation]
4. **Tab Names**: Must be from approved list
5. **Tag Format**: Proper key:value structure
6. **No Empty Fields**: Except honorific_level can be empty

### Content Validations
1. **Unique Cards**: No duplicate front/back combinations
2. **Term Consistency**: All cards for a term use same spelling
3. **Memory Palace**: Primer matches term's POS and number
4. **Tag Completeness**: Required tags present for card type

## Export Formats

### Anki Import
- TSV format directly importable
- Tags properly formatted for Anki
- HTML formatting preserved

### Other Formats
The TSV can be converted to:
- JSON for API consumption
- CSV for spreadsheet tools
- Markdown for documentation
- PDF for printable study guides

## Error Handling

### Common Issues
1. **Malformed TSV**: Missing tabs, wrong column count
2. **Encoding Issues**: Non-UTF8 characters
3. **Tag Parsing**: Invalid tag format
4. **Length Violations**: Content exceeding limits

### Recovery Strategy
1. Log complete row for debugging
2. Attempt partial data extraction
3. Mark card as draft/unpublished
4. Allow manual correction

## Version History

- **v1.0** (2024-01-08): Initial specification based on example output
- Future enhancements:
  - Audio pronunciation links
  - Image/diagram references
  - Difficulty ratings
  - Spaced repetition metadata