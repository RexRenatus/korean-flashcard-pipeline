# Intelligent Assistant Module

AI-powered assistance features for enhancing the flashcard generation process.

## Overview

This module provides intelligent features that leverage AI to improve flashcard quality, suggest enhancements, and provide contextual learning assistance. It acts as a smart layer on top of the basic pipeline.

## Features

### Current Capabilities
- **Prompt Enhancement** - Optimizes prompts for better AI responses
- **Context Management** - Maintains conversation context across requests
- **Quality Scoring** - Evaluates flashcard quality and suggests improvements
- **Adaptive Learning** - Adjusts difficulty based on user progress

### Planned Features
- **Smart Categorization** - Auto-categorize vocabulary by topic
- **Related Terms** - Suggest related vocabulary to study
- **Learning Paths** - Generate customized study sequences
- **Error Analysis** - Identify common mistakes and provide targeted practice

## Architecture

```
intelligent_assistant/
├── __init__.py              # Module initialization
├── prompt_enhancer.py       # Prompt optimization logic
├── context_manager.py       # Conversation context handling
├── quality_scorer.py        # Flashcard quality evaluation
├── adaptive_engine.py       # Adaptive learning algorithms
└── templates/               # AI prompt templates
```

## Core Components

### Prompt Enhancer
Optimizes prompts before sending to AI:
- Adds context and examples
- Ensures consistent formatting
- Includes quality guidelines
- Manages token limits

### Context Manager
Maintains state across interactions:
- User learning history
- Previous conversations
- Error patterns
- Preference tracking

### Quality Scorer
Evaluates generated flashcards:
- Completeness of information
- Clarity of explanations
- Example quality
- Difficulty appropriateness

## Usage Examples

```python
# Enhance a prompt
from flashcard_pipeline.intelligent_assistant import PromptEnhancer

enhancer = PromptEnhancer()
enhanced_prompt = await enhancer.enhance(
    base_prompt="Create a flashcard for 안녕하세요",
    context={"user_level": "beginner", "focus": "pronunciation"}
)

# Score flashcard quality
from flashcard_pipeline.intelligent_assistant import QualityScorer

scorer = QualityScorer()
score = await scorer.evaluate(flashcard)
suggestions = await scorer.suggest_improvements(flashcard)

# Adaptive difficulty
from flashcard_pipeline.intelligent_assistant import AdaptiveEngine

engine = AdaptiveEngine(user_profile)
next_difficulty = engine.calculate_next_level(
    current_performance=0.85,
    current_difficulty=3
)
```

## Prompt Templates

The module uses sophisticated prompt templates:

```python
FLASHCARD_GENERATION_TEMPLATE = """
You are creating a Korean language flashcard for a {level} learner.

Term: {term}
Context: {context}

Please provide:
1. Clear, concise English meaning
2. Pronunciation guide with tone markers
3. Common usage example with translation
4. Memory aids or mnemonics
5. Cultural notes if relevant

Quality guidelines:
- Use simple language for beginners
- Include formal/informal variations
- Highlight common mistakes
- Provide contextual usage
"""
```

## Configuration

```python
# config.py
ASSISTANT_CONFIG = {
    "prompt_enhancement": {
        "max_context_length": 1000,
        "include_examples": True,
        "quality_threshold": 0.8
    },
    "context_window": {
        "max_conversations": 10,
        "retention_days": 30
    },
    "scoring": {
        "weights": {
            "completeness": 0.3,
            "clarity": 0.3,
            "examples": 0.2,
            "cultural_notes": 0.2
        }
    }
}
```

## Best Practices

1. **Cache Enhanced Prompts** - Reuse successful prompt patterns
2. **Monitor Quality Scores** - Track trends and adjust thresholds
3. **Respect Context Limits** - Don't overload with historical data
4. **User Feedback Loop** - Incorporate user ratings into scoring
5. **A/B Test Prompts** - Compare different enhancement strategies

## Integration

The assistant integrates with:
- Main pipeline for prompt preprocessing
- Database for context storage
- API client for enhanced requests
- Monitoring for quality metrics