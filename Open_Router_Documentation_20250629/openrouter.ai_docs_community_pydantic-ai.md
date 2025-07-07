---
url: "https://openrouter.ai/docs/community/pydantic-ai"
title: "PydanticAI Integration | OpenRouter SDK Support | OpenRouter | Documentation"
---

## Using PydanticAI

[PydanticAI](https://github.com/pydantic/pydantic-ai) provides a high-level interface for working with various LLM providers, including OpenRouter.

### Installation

```code-block text-sm

$pip install 'pydantic-ai-slim[openai]'
```

### Configuration

You can use OpenRouter with PydanticAI through its OpenAI-compatible interface:

```code-block text-sm

1from pydantic_ai import Agent2from pydantic_ai.models.openai import OpenAIModel34model = OpenAIModel(5    "anthropic/claude-3.5-sonnet",  # or any other OpenRouter model6    base_url="https://openrouter.ai/api/v1",7    api_key="sk-or-...",8)910agent = Agent(model)11result = await agent.run("What is the meaning of life?")12print(result)
```

For more details about using PydanticAI with OpenRouter, see the [PydanticAI documentation](https://ai.pydantic.dev/models/#api_key-argument).