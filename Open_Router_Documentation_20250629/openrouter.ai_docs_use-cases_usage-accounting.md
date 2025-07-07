---
url: "https://openrouter.ai/docs/use-cases/usage-accounting"
title: "Usage Accounting | Track AI Model Usage with OpenRouter | OpenRouter | Documentation"
---

The OpenRouter API provides built-in **Usage Accounting** that allows you to track AI model usage without making additional API calls. This feature provides detailed information about token counts, costs, and caching status directly in your API responses.

## Usage Information

When enabled, the API will return detailed usage information including:

1. Prompt and completion token counts using the model’s native tokenizer
2. Cost in credits
3. Reasoning token counts (if applicable)
4. Cached token counts (if available)

This information is included in the last SSE message for streaming responses, or in the complete response for non-streaming requests.

## Enabling Usage Accounting

You can enable usage accounting in your requests by including the `usage` parameter:

```code-block text-sm

1{2  "model": "your-model",3  "messages": [],4  "usage": {5    "include": true6  }7}
```

## Response Format

When usage accounting is enabled, the response will include a `usage` object with detailed token information:

```code-block text-sm

1{2  "object": "chat.completion.chunk",3  "usage": {4    "completion_tokens": 2,5    "completion_tokens_details": {6      "reasoning_tokens": 07    },8    "cost": 0.95,9    "cost_details": {10      "upstream_inference_cost": 1911    },12    "prompt_tokens": 194,13    "prompt_tokens_details": {14      "cached_tokens": 015    },16    "total_tokens": 19617  }18}
```

`cached_tokens` is the number of tokens that were _read_ from the cache. At this point in time, we do not support retrieving the number of tokens that were _written_ to the cache.

## Cost Breakdown

The usage response includes detailed cost information:

- `cost`: The total amount charged to your account
- `cost_details.upstream_inference_cost`: The actual cost charged by the upstream AI provider

**Note:** The `upstream_inference_cost` field only applies to BYOK (Bring Your Own Key) requests.

##### Performance Impact

Enabling usage accounting will add a few hundred milliseconds to the last
response as the API calculates token counts and costs. This only affects the
final message and does not impact overall streaming performance.

## Benefits

1. **Efficiency**: Get usage information without making separate API calls
2. **Accuracy**: Token counts are calculated using the model’s native tokenizer
3. **Transparency**: Track costs and cached token usage in real-time
4. **Detailed Breakdown**: Separate counts for prompt, completion, reasoning, and cached tokens

## Best Practices

1. Enable usage tracking when you need to monitor token consumption or costs
2. Account for the slight delay in the final response when usage accounting is enabled
3. Consider implementing usage tracking in development to optimize token usage before production
4. Use the cached token information to optimize your application’s performance

## Alternative: Getting Usage via Generation ID

You can also retrieve usage information asynchronously by using the generation ID returned from your API calls. This is particularly useful when you want to fetch usage statistics after the completion has finished or when you need to audit historical usage.

To use this method:

1. Make your chat completion request as normal
2. Note the `id` field in the response
3. Use that ID to fetch usage information via the `/generation` endpoint

For more details on this approach, see the [Get a Generation](https://openrouter.ai/docs/api-reference/get-a-generation) documentation.

## Examples

### Basic Usage with Token Tracking

PythonTypeScript

```code-block text-sm

1import requests2import json34url = "https://openrouter.ai/api/v1/chat/completions"5headers = {6    "Authorization": f"Bearer <OPENROUTER_API_KEY>",7    "Content-Type": "application/json"8}9payload = {10    "model": "anthropic/claude-3-opus",11    "messages": [12        {"role": "user", "content": "What is the capital of France?"}13    ],14    "usage": {15        "include": True16    }17}1819response = requests.post(url, headers=headers, data=json.dumps(payload))20print("Response:", response.json()['choices'][0]['message']['content'])21print("Usage Stats:", response.json()['usage'])
```

### Streaming with Usage Information

This example shows how to handle usage information in streaming mode:

PythonTypeScript

```code-block text-sm

1from openai import OpenAI23client = OpenAI(4    base_url="https://openrouter.ai/api/v1",5    api_key="<OPENROUTER_API_KEY>",6)78def chat_completion_with_usage(messages):9    response = client.chat.completions.create(10        model="anthropic/claude-3-opus",11        messages=messages,12        usage={13          "include": True14        },15        stream=True16    )17    return response1819for chunk in chat_completion_with_usage([20    {"role": "user", "content": "Write a haiku about Paris."}21]):22    if hasattr(chunk, 'usage'):23        if hasattr(chunk.usage, 'total_tokens'):24            print(f"\nUsage Statistics:")25            print(f"Total Tokens: {chunk.usage.total_tokens}")26            print(f"Prompt Tokens: {chunk.usage.prompt_tokens}")27            print(f"Completion Tokens: {chunk.usage.completion_tokens}")28            print(f"Cost: {chunk.usage.cost} credits")29    elif chunk.choices[0].delta.content:30        print(chunk.choices[0].delta.content, end="")

```