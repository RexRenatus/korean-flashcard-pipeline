---
url: "https://openrouter.ai/docs/features/prompt-caching"
title: "Prompt Caching | Reduce AI Model Costs with OpenRouter | OpenRouter | Documentation"
---

To save on inference costs, you can enable prompt caching on supported providers and models.

Most providers automatically enable prompt caching, but note that some (see Anthropic below) require you to enable it on a per-message basis.

When using caching (whether automatically in supported models, or via the `cache_control` header), OpenRouter will make a best-effort to continue routing to the same provider to make use of the warm cache. In the event that the provider with your cached prompt is not available, OpenRouter will try the next-best provider.

## Inspecting cache usage

To see how much caching saved on each generation, you can:

1. Click the detail button on the [Activity](https://openrouter.ai/activity) page
2. Use the `/api/v1/generation` API, [documented here](https://openrouter.ai/docs/api-reference/overview#querying-cost-and-stats)
3. Use `usage: {include: true}` in your request to get the cache tokens at the end of the response (see [Usage Accounting](https://openrouter.ai/docs/use-cases/usage-accounting) for details)

The `cache_discount` field in the response body will tell you how much the response saved on cache usage. Some providers, like Anthropic, will have a negative discount on cache writes, but a positive discount (which reduces total cost) on cache reads.

## OpenAI

Caching price changes:

- **Cache writes**: no cost
- **Cache reads**: (depending on the model) charged at 0.25x or 0.50x the price of the original input pricing

[Click here to view OpenAI’s cache pricing per model.](https://platform.openai.com/docs/pricing)

Prompt caching with OpenAI is automated and does not require any additional configuration. There is a minimum prompt size of 1024 tokens.

[Click here to read more about OpenAI prompt caching and its limitation.](https://platform.openai.com/docs/guides/prompt-caching)

## Grok

Caching price changes:

- **Cache writes**: no cost
- **Cache reads**: charged at 0.25x the price of the original input pricing

[Click here to view Grok’s cache pricing per model.](https://docs.x.ai/docs/models#models-and-pricing)

Prompt caching with Grok is automated and does not require any additional configuration.

## Anthropic Claude

Caching price changes:

- **Cache writes**: charged at 1.25x the price of the original input pricing
- **Cache reads**: charged at 0.1x the price of the original input pricing

Prompt caching with Anthropic requires the use of `cache_control` breakpoints. There is a limit of four breakpoints, and the cache will expire within five minutes. Therefore, it is recommended to reserve the cache breakpoints for large bodies of text, such as character cards, CSV data, RAG data, book chapters, etc.

[Click here to read more about Anthropic prompt caching and its limitation.](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)

The `cache_control` breakpoint can only be inserted into the text part of a multipart message.

System message caching example:

```code-block text-sm

1{2  "messages": [3    {4      "role": "system",5      "content": [6        {7          "type": "text",8          "text": "You are a historian studying the fall of the Roman Empire. You know the following book very well:"9        },10        {11          "type": "text",12          "text": "HUGE TEXT BODY",13          "cache_control": {14            "type": "ephemeral"15          }16        }17      ]18    },19    {20      "role": "user",21      "content": [22        {23          "type": "text",24          "text": "What triggered the collapse?"25        }26      ]27    }28  ]29}

```

User message caching example:

```code-block text-sm

1{2  "messages": [3    {4      "role": "user",5      "content": [6        {7          "type": "text",8          "text": "Given the book below:"9        },10        {11          "type": "text",12          "text": "HUGE TEXT BODY",13          "cache_control": {14            "type": "ephemeral"15          }16        },17        {18          "type": "text",19          "text": "Name all the characters in the above book"20        }21      ]22    }23  ]24}

```

## DeepSeek

Caching price changes:

- **Cache writes**: charged at the same price as the original input pricing
- **Cache reads**: charged at 0.1x the price of the original input pricing

Prompt caching with DeepSeek is automated and does not require any additional configuration.

## Google Gemini

### Implicit Caching

Gemini 2.5 Pro and 2.5 Flash models now support **implicit caching**, providing automatic caching functionality similar to OpenAI’s automatic caching. Implicit caching works seamlessly — no manual setup or additional `cache_control` breakpoints required.

Pricing Changes:

- No cache write or storage costs.
- Cached tokens are charged at 0.25x the original input token cost.

Note that the TTL is on average 3-5 minutes, but will vary. There is a minimum of 1028 tokens for Gemini 2.5 Flash, and 2048 tokens for Gemini 2.5 Pro for requests to be eligible for caching.

[Official announcement from Google](https://developers.googleblog.com/en/gemini-2-5-models-now-support-implicit-caching/)

To maximize implicit cache hits, keep the initial portion of your message
arrays consistent between requests. Push variations (such as user questions or
dynamic context elements) toward the end of your prompt/requests.

### Pricing Changes for Cached Requests:

- **Cache Writes:** Charged at the input token cost plus 5 minutes of cache storage, calculated as follows:

```code-block text-sm

Cache write cost = Input token price + (Cache storage price × (5 minutes / 60 minutes))
```

- **Cache Reads:** Charged at 0.25× the original input token cost.

### Supported Models and Limitations:

Only certain Gemini models support caching. Please consult Google’s [Gemini API Pricing Documentation](https://ai.google.dev/gemini-api/docs/pricing) for the most current details.

Cache Writes have a 5 minute Time-to-Live (TTL) that does not update. After 5 minutes, the cache expires and a new cache must be written.

Gemini models have typically have a 4096 token minimum for cache write to occur. Cached tokens count towards the model’s maximum token usage. Gemini 2.5 Pro has a minimum of 2048 tokens, and Gemini 2.5 Flash has a minimum of 1028 tokens.

### How Gemini Prompt Caching works on OpenRouter:

OpenRouter simplifies Gemini cache management, abstracting away complexities:

- You **do not** need to manually create, update, or delete caches.
- You **do not** need to manage cache names or TTL explicitly.

### How to Enable Gemini Prompt Caching:

Gemini caching in OpenRouter requires you to insert `cache_control` breakpoints explicitly within message content, similar to Anthropic. We recommend using caching primarily for large content pieces (such as CSV files, lengthy character cards, retrieval augmented generation (RAG) data, or extensive textual sources).

There is not a limit on the number of `cache_control` breakpoints you can
include in your request. OpenRouter will use only the last breakpoint for
Gemini caching. Including multiple breakpoints is safe and can help maintain
compatibility with Anthropic, but only the final one will be used for Gemini.

### Examples:

#### System Message Caching Example

```code-block text-sm

1{2  "messages": [3    {4      "role": "system",5      "content": [6        {7          "type": "text",8          "text": "You are a historian studying the fall of the Roman Empire. Below is an extensive reference book:"9        },10        {11          "type": "text",12          "text": "HUGE TEXT BODY HERE",13          "cache_control": {14            "type": "ephemeral"15          }16        }17      ]18    },19    {20      "role": "user",21      "content": [22        {23          "type": "text",24          "text": "What triggered the collapse?"25        }26      ]27    }28  ]29}

```

#### User Message Caching Example

```code-block text-sm

1{2  "messages": [3    {4      "role": "user",5      "content": [6        {7          "type": "text",8          "text": "Based on the book text below:"9        },10        {11          "type": "text",12          "text": "HUGE TEXT BODY HERE",13          "cache_control": {14            "type": "ephemeral"15          }16        },17        {18          "type": "text",19          "text": "List all main characters mentioned in the text above."20        }21      ]22    }23  ]24}

```