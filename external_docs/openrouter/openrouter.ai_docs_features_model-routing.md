---
url: "https://openrouter.ai/docs/features/model-routing"
title: "Model Routing | Dynamic AI Model Selection and Fallback | OpenRouter | Documentation"
---

OpenRouter provides two options for model routing.

## Auto Router

The [Auto Router](https://openrouter.ai/openrouter/auto), a special model ID that you can use to choose between selected high-quality models based on your prompt, powered by [NotDiamond](https://www.notdiamond.ai/).

```code-block text-sm

1{2  "model": "openrouter/auto",3  ... // Other params4}
```

The resulting generation will have `model` set to the model that was used.

## The `models` parameter

The `models` parameter lets you automatically try other models if the primary model’s providers are down, rate-limited, or refuse to reply due to content moderation.

```code-block text-sm

1{2  "models": ["anthropic/claude-3.5-sonnet", "gryphe/mythomax-l2-13b"],3  ... // Other params4}
```

If the model you selected returns an error, OpenRouter will try to use the fallback model instead. If the fallback model is down or returns an error, OpenRouter will return that error.

By default, any error can trigger the use of a fallback model, including context length validation errors, moderation flags for filtered models, rate-limiting, and downtime.

Requests are priced using the model that was ultimately used, which will be returned in the `model` attribute of the response body.

## Using with OpenAI SDK

To use the `models` array with the OpenAI SDK, include it in the `extra_body` parameter. In the example below, gpt-4o will be tried first, and the `models` array will be tried in order as fallbacks.

TypeScriptPython

```code-block text-sm

1import OpenAI from 'openai';23const openrouterClient = new OpenAI({4  baseURL: 'https://openrouter.ai/api/v1',5  // API key and headers6});78async function main() {9  // @ts-expect-error10  const completion = await openrouterClient.chat.completions.create({11    model: 'openai/gpt-4o',12    models: ['anthropic/claude-3.5-sonnet', 'gryphe/mythomax-l2-13b'],13    messages: [14      {15        role: 'user',16        content: 'What is the meaning of life?',17      },18    ],19  });20  console.log(completion.choices[0].message);21}2223main();

```