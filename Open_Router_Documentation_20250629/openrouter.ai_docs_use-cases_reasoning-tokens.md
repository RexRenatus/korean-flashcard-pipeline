---
url: "https://openrouter.ai/docs/use-cases/reasoning-tokens"
title: "Reasoning Tokens | Enhanced AI Model Reasoning with OpenRouter | OpenRouter | Documentation"
---

For models that support it, the OpenRouter API can return **Reasoning Tokens**, also known as thinking tokens. OpenRouter normalizes the different ways of customizing the amount of reasoning tokens that the model will use, providing a unified interface across different providers.

Reasoning tokens provide a transparent look into the reasoning steps taken by a model. Reasoning tokens are considered output tokens and charged accordingly.

Reasoning tokens are included in the response by default if the model decides to output them. Reasoning tokens will appear in the `reasoning` field of each message, unless you decide to exclude them.

##### Some reasoning models do not return their reasoning tokens

While most models and providers make reasoning tokens available in the
response, some (like the OpenAI o-series and Gemini Flash Thinking) do not.

## Controlling Reasoning Tokens

You can control reasoning tokens in your requests using the `reasoning` parameter:

```code-block text-sm

1{2  "model": "your-model",3  "messages": [],4  "reasoning": {5    // One of the following (not both):6    "effort": "high", // Can be "high", "medium", or "low" (OpenAI-style)7    "max_tokens": 2000, // Specific token limit (Anthropic-style)89    // Optional: Default is false. All models support this.10    "exclude": false, // Set to true to exclude reasoning tokens from response1112    // Or enable reasoning with the default parameters:13    "enabled": true // Default: inferred from `effort` or `max_tokens`14  }15}
```

The `reasoning` config object consolidates settings for controlling reasoning strength across different models. See the Note for each option below to see which models are supported and how other models will behave.

### Max Tokens for Reasoning

##### Supported models

Currently supported by:

- Gemini thinking models
- Anthropic models (by using the `reasoning.max_tokens`
parameter)


For models that support reasoning token allocation, you can control it like this:

- `"max_tokens": 2000` \- Directly specifies the maximum number of tokens to use for reasoning

For models that only support `reasoning.effort` (see below), the `max_tokens` value will be used to determine the effort level.

### Reasoning Effort Level

##### Supported models

Currently supported by the OpenAI o-series and Grok models

- `"effort": "high"` \- Allocates a large portion of tokens for reasoning (approximately 80% of max\_tokens)
- `"effort": "medium"` \- Allocates a moderate portion of tokens (approximately 50% of max\_tokens)
- `"effort": "low"` \- Allocates a smaller portion of tokens (approximately 20% of max\_tokens)

For models that only support `reasoning.max_tokens`, the effort level will be set based on the percentages above.

### Excluding Reasoning Tokens

If you want the model to use reasoning internally but not include it in the response:

- `"exclude": true` \- The model will still use reasoning, but it won’t be returned in the response

Reasoning tokens will appear in the `reasoning` field of each message.

### Enable Reasoning with Default Config

To enable reasoning with the default parameters:

- `"enabled": true` \- Enables reasoning at the “medium” effort level with no exclusions.

## Legacy Parameters

For backward compatibility, OpenRouter still supports the following legacy parameters:

- `include_reasoning: true` \- Equivalent to `reasoning: {}`
- `include_reasoning: false` \- Equivalent to `reasoning: { exclude: true }`

However, we recommend using the new unified `reasoning` parameter for better control and future compatibility.

## Examples

### Basic Usage with Reasoning Tokens

PythonTypeScript

```code-block text-sm

1import requests2import json34url = "https://openrouter.ai/api/v1/chat/completions"5headers = {6    "Authorization": f"Bearer <OPENROUTER_API_KEY>",7    "Content-Type": "application/json"8}9payload = {10    "model": "openai/o3-mini",11    "messages": [12        {"role": "user", "content": "How would you build the world's tallest skyscraper?"}13    ],14    "reasoning": {15        "effort": "high"  # Use high reasoning effort16    }17}1819response = requests.post(url, headers=headers, data=json.dumps(payload))20print(response.json()['choices'][0]['message']['reasoning'])
```

### Using Max Tokens for Reasoning

For models that support direct token allocation (like Anthropic models), you can specify the exact number of tokens to use for reasoning:

PythonTypeScript

```code-block text-sm

1import requests2import json34url = "https://openrouter.ai/api/v1/chat/completions"5headers = {6    "Authorization": f"Bearer <OPENROUTER_API_KEY>",7    "Content-Type": "application/json"8}9payload = {10    "model": "anthropic/claude-3.7-sonnet",11    "messages": [12        {"role": "user", "content": "What's the most efficient algorithm for sorting a large dataset?"}13    ],14    "reasoning": {15        "max_tokens": 2000  # Allocate 2000 tokens (or approximate effort) for reasoning16    }17}1819response = requests.post(url, headers=headers, data=json.dumps(payload))20print(response.json()['choices'][0]['message']['reasoning'])21print(response.json()['choices'][0]['message']['content'])
```

### Excluding Reasoning Tokens from Response

If you want the model to use reasoning internally but not include it in the response:

PythonTypeScript

```code-block text-sm

1import requests2import json34url = "https://openrouter.ai/api/v1/chat/completions"5headers = {6    "Authorization": f"Bearer <OPENROUTER_API_KEY>",7    "Content-Type": "application/json"8}9payload = {10    "model": "deepseek/deepseek-r1",11    "messages": [12        {"role": "user", "content": "Explain quantum computing in simple terms."}13    ],14    "reasoning": {15        "effort": "high",16        "exclude": true  # Use reasoning but don't include it in the response17    }18}1920response = requests.post(url, headers=headers, data=json.dumps(payload))21# No reasoning field in the response22print(response.json()['choices'][0]['message']['content'])

```

### Advanced Usage: Reasoning Chain-of-Thought

This example shows how to use reasoning tokens in a more complex workflow. It injects one model’s reasoning into another model to improve its response quality:

PythonTypeScript

```code-block text-sm

1import requests2import json34question = "Which is bigger: 9.11 or 9.9?"56url = "https://openrouter.ai/api/v1/chat/completions"7headers = {8    "Authorization": f"Bearer <OPENROUTER_API_KEY>",9    "Content-Type": "application/json"10}1112def do_req(model, content, reasoning_config=None):13    payload = {14        "model": model,15        "messages": [16            {"role": "user", "content": content}17        ],18        "stop": "</think>"19    }2021    return requests.post(url, headers=headers, data=json.dumps(payload))2223# Get reasoning from a capable model24content = f"{question} Please think this through, but don't output an answer"25reasoning_response = do_req("deepseek/deepseek-r1", content)26reasoning = reasoning_response.json()['choices'][0]['message']['reasoning']2728# Let's test! Here's the naive response:29simple_response = do_req("openai/gpt-4o-mini", question)30print(simple_response.json()['choices'][0]['message']['content'])3132# Here's the response with the reasoning token injected:33content = f"{question}. Here is some context to help you: {reasoning}"34smart_response = do_req("openai/gpt-4o-mini", content)35print(smart_response.json()['choices'][0]['message']['content'])

```

## Provider-Specific Reasoning Implementation

### Anthropic Models with Reasoning Tokens

The latest Claude models, such as [anthropic/claude-3.7-sonnet](https://openrouter.ai/anthropic/claude-3.7-sonnet), support working with and returning reasoning tokens.

You can enable reasoning on Anthropic models **only** using the unified `reasoning` parameter with either `effort` or `max_tokens`.

**Note:** The `:thinking` variant is no longer supported for Anthropic models. Use the `reasoning` parameter instead.

#### Reasoning Max Tokens for Anthropic Models

When using Anthropic models with reasoning:

- When using the `reasoning.max_tokens` parameter, that value is used directly with a minimum of 1024 tokens.
- When using the `reasoning.effort` parameter, the budget\_tokens are calculated based on the `max_tokens` value.

The reasoning token allocation is capped at 32,000 tokens maximum and 1024 tokens minimum. The formula for calculating the budget\_tokens is: `budget_tokens = max(min(max_tokens * {effort_ratio}, 32000), 1024)`

effort\_ratio is 0.8 for high effort, 0.5 for medium effort, and 0.2 for low effort.

**Important**: `max_tokens` must be strictly higher than the reasoning budget to ensure there are tokens available for the final response after thinking.

##### Token Usage and Billing

Please note that reasoning tokens are counted as output tokens for billing
purposes. Using reasoning tokens will increase your token usage but can
significantly improve the quality of model responses.

### Examples with Anthropic Models

#### Example 1: Streaming mode with reasoning tokens

PythonTypeScript

```code-block text-sm

1from openai import OpenAI23client = OpenAI(4    base_url="https://openrouter.ai/api/v1",5    api_key="<OPENROUTER_API_KEY>",6)78def chat_completion_with_reasoning(messages):9    response = client.chat.completions.create(10        model="anthropic/claude-3.7-sonnet",11        messages=messages,12        max_tokens=10000,13        reasoning={14            "max_tokens": 8000  # Directly specify reasoning token budget15        },16        stream=True17    )18    return response1920for chunk in chat_completion_with_reasoning([21    {"role": "user", "content": "What's bigger, 9.9 or 9.11?"}22]):23    if hasattr(chunk.choices[0].delta, 'reasoning') and chunk.choices[0].delta.reasoning:24        print(f"REASONING: {chunk.choices[0].delta.reasoning}")25    elif chunk.choices[0].delta.content:26        print(f"CONTENT: {chunk.choices[0].delta.content}")

```

## Preserving Reasoning Blocks

##### Model Support

The reasoning\_details are currently returned by Anthropic reasoning models,
but will soon expand to include OpenAI models.

If you want to pass reasoning back in context, you must pass reasoning blocks back to the API. This is useful for maintaining the model’s reasoning flow and conversation integrity.

Preserving reasoning blocks is useful specifically for tool calling. When models like Claude invoke tools, it is pausing its construction of a response to await external information. When tool results are returned, the model will continue building that existing response. This necessitates preserving reasoning blocks during tool use, for a couple of reasons:

**Reasoning continuity**: The reasoning blocks capture the model’s step-by-step reasoning that led to tool requests. When you post tool results, including the original reasoning ensures the model can continue its reasoning from where it left off.

**Context maintenance**: While tool results appear as user messages in the API structure, they’re part of a continuous reasoning flow. Preserving reasoning blocks maintains this conceptual flow across multiple API calls.

##### Important for Claude Models

When providing reasoning\_details blocks, the entire sequence of consecutive
reasoning blocks must match the outputs generated by the model during the
original request; you cannot rearrange or modify the sequence of these blocks.

### Example: Preserving Reasoning Blocks with OpenRouter and Claude

PythonTypeScript

```code-block text-sm

1from openai import OpenAI23client = OpenAI(4    base_url="https://openrouter.ai/api/v1",5    api_key="<OPENROUTER_API_KEY>",6)78# First API call with tools9response = client.chat.completions.create(10    model="anthropic/claude-sonnet-4",11    messages=[12        {"role": "user", "content": "What's the weather like in Boston? Then recommend what to wear."}13    ],14    tools=[{15        "type": "function",16        "function": {17            "name": "get_weather",18            "description": "Get current weather",19            "parameters": {20                "type": "object",21                "properties": {22                    "location": {"type": "string"}23                },24                "required": ["location"]25            }26        }27    }],28    reasoning={"max_tokens": 2000}29)3031# Extract the assistant message with reasoning_details32message = response.choices[0].message3334# Preserve the complete reasoning_details when passing back35messages = [36    {"role": "user", "content": "What's the weather like in Boston? Then recommend what to wear."},37    {38        "role": "assistant",39        "content": message.content,40        "tool_calls": message.tool_calls,41        "reasoning_details": message.reasoning_details  # Pass back unmodified42    },43    {44        "role": "tool",45        "tool_call_id": message.tool_calls[0].id,46        "content": '{"temperature": 45, "condition": "rainy", "humidity": 85}'47    }48]4950# Second API call - Claude continues reasoning from where it left off51response2 = client.chat.completions.create(52    model="anthropic/claude-sonnet-4",53    messages=messages,  # Includes preserved thinking blocks54    tools=tools55)

```

For more detailed information about thinking encryption, redacted blocks, and advanced use cases, see [Anthropic’s documentation on extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#extended-thinking).