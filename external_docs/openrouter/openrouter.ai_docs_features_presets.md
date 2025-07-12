---
url: "https://openrouter.ai/docs/features/presets"
title: "Presets | Configuration Management for AI Models | OpenRouter | Documentation"
---

[Presets](https://openrouter.ai/settings/presets) allow you to separate your LLM configuration from your code. Create and manage presets through the OpenRouter web application to control provider routing, model selection, system prompts, and other parameters, then reference them in OpenRouter API requests.

## What are Presets?

Presets are named configurations that encapsulate all the settings needed for a specific use case. For example, you might create:

- An “email-copywriter” preset for generating marketing copy
- An “inbound-classifier” preset for categorizing customer inquiries
- A “code-reviewer” preset for analyzing pull requests

Each preset can manage:

- Provider routing preferences (sort by price, latency, etc.)
- Model selection (specific model or array of models with fallbacks)
- System prompts
- Generation parameters (temperature, top\_p, etc.)
- Provider inclusion/exclusion rules

## Quick Start

1. [Create a preset](https://openrouter.ai/settings/presets). For example, select a model and restrict provider routing to just a few providers.
![Creating a new preset](https://prod.ferndocs.com/_next/image?url=https%3A%2F%2Ffiles.buildwithfern.com%2Fopenrouter.docs.buildwithfern.com%2Fdocs%2F2025-06-28T20%3A47%3A18.701Z%2Fcontent%2Fassets%2Fpreset-example.png&w=3840&q=75)

2. Make an API request to the preset:


```code-block text-sm

1{2  "model": "@preset/ravenel-bridge",3  "messages": [4    {5      "role": "user",6      "content": "What's your opinion of the Golden Gate Bridge? Isn't it beautiful?"7    }8  ]9}
```

## Benefits

### Separation of Concerns

Presets help you maintain a clean separation between your application code and LLM configuration. This makes your code more semantic and easier to maintain.

### Rapid Iteration

Update your LLM configuration without deploying code changes:

- Switch to new model versions
- Adjust system prompts
- Modify parameters
- Change provider preferences

## Using Presets

There are three ways to use presets in your API requests.

1. **Direct Model Reference**

You can reference the preset as if it was a model by sending requests to `@preset/preset-slug`

```code-block text-sm

1{2  "model": "@preset/email-copywriter",3  "messages": [4    {5      "role": "user",6      "content": "Write a marketing email about our new feature"7    }8  ]9}
```

2. **Preset Field**

```code-block text-sm

1{2  "model": "openai/gpt-4",3  "preset": "email-copywriter",4  "messages": [5    {6      "role": "user",7      "content": "Write a marketing email about our new feature"8    }9  ]10}
```

3. **Combined Model and Preset**

```code-block text-sm

1{2  "model": "openai/gpt-4@preset/email-copywriter",3  "messages": [4    {5      "role": "user",6      "content": "Write a marketing email about our new feature"7    }8  ]9}
```

## Other Notes

1. If you’re using an organization account, all members can access organization presets. This is a great way to share best practices across teams.
2. Version history is kept in order to understand changes that were made, and to be able to roll back. However when addressing a preset through the API, the latest version is always used.
3. If you provide parameters in the request, they will be shallow-merged with the options configured in the preset.