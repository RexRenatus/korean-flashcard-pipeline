---
url: "https://openrouter.ai/docs/features/web-search"
title: "Web Search | Add Real-time Web Data to AI Model Responses | OpenRouter | Documentation"
---

You can incorporate relevant web search results for _any_ model on OpenRouter by activating and customizing the `web` plugin, or by appending `:online` to the model slug:

```code-block text-sm

1{2  "model": "openai/gpt-4o:online"3}
```

This is a shortcut for using the `web` plugin, and is exactly equivalent to:

```code-block text-sm

1{2  "model": "openrouter/auto",3  "plugins": [{ "id": "web" }]4}
```

The web search plugin is powered by [Exa](https://exa.ai/) and uses their [“auto”](https://docs.exa.ai/reference/how-exa-search-works#combining-neural-and-keyword-the-best-of-both-worlds-through-exa-auto-search) method (a combination of keyword search and embeddings-based web search) to find the most relevant results and augment/ground your prompt.

## Parsing web search results

Web search results for all models (including native-only models like Perplexity and OpenAI Online) are available in the API and standardized by OpenRouterto follow the same annotation schema in the [OpenAI Chat Completion Message type](https://platform.openai.com/docs/api-reference/chat/object):

```code-block text-sm

1{2  "message": {3    "role": "assistant",4    "content": "Here's the latest news I found: ...",5    "annotations": [6      {7        "type": "url_citation",8        "url_citation": {9          "url": "https://www.example.com/web-search-result",10          "title": "Title of the web search result",11          "content": "Content of the web search result", // Added by OpenRouter if available12          "start_index": 100, // The index of the first character of the URL citation in the message.13          "end_index": 200 // The index of the last character of the URL citation in the message.14        }15      }16    ]17  }18}
```

## Customizing the Web Plugin

The maximum results allowed by the web plugin and the prompt used to attach them to your message stream can be customized:

```code-block text-sm

1{2  "model": "openai/gpt-4o:online",3  "plugins": [4    {5      "id": "web",6      "max_results": 1, // Defaults to 57      "search_prompt": "Some relevant web results:" // See default below8    }9  ]10}
```

By default, the web plugin uses the following search prompt, using the current date:

```code-block text-sm

A web search was conducted on `date`. Incorporate the following web search results into your response.IMPORTANT: Cite them using markdown links named using the domain of the source.Example: [nytimes.com](https://nytimes.com/some-page).
```

## Pricing

The web plugin uses your OpenRouter credits and charges _$4 per 1000 results_. By default, `max_results` set to 5, this comes out to a maximum of $0.02 per request, in addition to the LLM usage for the search result prompt tokens.

## Non-plugin Web Search

Some models have built-in web search. These models charge a fee based on the search context size, which determines how much search data is retrieved and processed for a query.

### Search Context Size Thresholds

Search context can be ‘low’, ‘medium’, or ‘high’ and determines how much search context is retrieved for a query:

- **Low**: Minimal search context, suitable for basic queries
- **Medium**: Moderate search context, good for general queries
- **High**: Extensive search context, ideal for detailed research

### Specifying Search Context Size

You can specify the search context size in your API request using the `web_search_options` parameter:

```code-block text-sm

1{2  "model": "openai/gpt-4.1",3  "messages": [4    {5      "role": "user",6      "content": "What are the latest developments in quantum computing?"7    }8  ],9  "web_search_options": {10    "search_context_size": "high"11  }12}
```

### OpenAI Model Pricing

For GPT-4.1, GPT-4o, and GPT-4o search preview Models:

| Search Context Size | Price per 1000 Requests |
| --- | --- |
| Low | $30.00 |
| Medium | $35.00 |
| High | $50.00 |

For GPT-4.1-Mini, GPT-4o-Mini, and GPT-4o-Mini-Search-Preview Models:

| Search Context Size | Price per 1000 Requests |
| --- | --- |
| Low | $25.00 |
| Medium | $27.50 |
| High | $30.00 |

### Perplexity Model Pricing

For Sonar and SonarReasoning:

| Search Context Size | Price per 1000 Requests |
| --- | --- |
| Low | $5.00 |
| Medium | $8.00 |
| High | $12.00 |

For SonarPro and SonarReasoningPro:

| Search Context Size | Price per 1000 Requests |
| --- | --- |
| Low | $6.00 |
| Medium | $10.00 |
| High | $14.00 |

##### Pricing Documentation

For more detailed information about pricing models, refer to the official documentation:

- [OpenAI Pricing](https://platform.openai.com/docs/pricing#web-search)
- [Perplexity Pricing](https://docs.perplexity.ai/guides/pricing)