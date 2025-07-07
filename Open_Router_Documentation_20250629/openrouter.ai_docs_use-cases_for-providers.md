---
url: "https://openrouter.ai/docs/use-cases/for-providers"
title: "Provider Integration | Add Your AI Models to OpenRouter | OpenRouter | Documentation"
---

## For Providers

If you’d like to be a model provider and sell inference on OpenRouter, [fill out our form](https://openrouter.notion.site/15a2fd57c4dc8067bc61ecd5263b31fd) to get started.

To be eligible to provide inference on OpenRouter you must have the following:

### 1\. List Models Endpoint

You must implement an endpoint that returns all models that should be served by OpenRouter. At this endpoint, please return a list of all available models on your platform. Below is an example of the response format:

```code-block text-sm

1{2  "data": [3    {4      // Required5      "id": "anthropic/claude-sonnet-4",6      "name": "Anthropic: Claude Sonnet 4",7      "created": 1690502400,8      "input_modalities": ["text", "image", "file"],9      "output_modalities": ["text", "image", "file"],10      "quantization": "fp8",11      "context_length": 1000000,12      "max_output_length": 128000,13      "pricing": {14        "prompt": "0.000008", // pricing per 1 token15        "completion": "0.000024", // pricing per 1 token16        "image": "0", // pricing per 1 image17        "request": "0", // pricing per 1 request18        "input_cache_reads": "0", // pricing per 1 token19        "input_cache_writes": "0" // pricing per 1 token20      },21      "supported_sampling_parameters": ["temperature", "stop"],22      "supported_features": [23        "tools",24        "json_mode",25        "structured_outputs",26        "web_search",27        "reasoning"28      ],29      // Optional30      "description": "Anthropic's flagship model...",31      "openrouter": {32        "slug": "anthropic/claude-sonnet-4"33      },34      "datacenters": [35        {36          "country_code": "US" // `Iso3166Alpha2Code`37        }38      ]39    }40  ]41}

```

NOTE: `pricing` fields are in string format to avoid floating point precision issues, and must be in USD.

Valid quantization values are: `int4`, `int8`, `fp4`, `fp6`, `fp8`, `fp16`, `bf16`, `fp32`.

Valid sampling parameters are: `temperature`, `top_p`, `top_k`, `repetition_penalty`, `frequency_penalty`, `presence_penalty`, `stop`, `seed`.

Valid features are: `tools`, `json_mode`, `structured_outputs`, `web_search`, `reasoning`.

### 2\. Auto Top Up or Invoicing

For OpenRouter to use the provider we must be able to pay for inference automatically. This can be done via auto top up or invoicing.