---
url: "https://openrouter.ai/docs/overview/models"
title: "OpenRouter Models | Access 400+ AI Models Through One API | OpenRouter | Documentation"
---

Explore and browse 400+ models and providers [on our website](https://openrouter.ai/models), or [with our API](https://openrouter.ai/docs/api-reference/list-available-models) (including RSS).

## Models API Standard

Our [Models API](https://openrouter.ai/docs/api-reference/list-available-models) makes the most important information about all LLMs freely available as soon as we confirm it.

### API Response Schema

The Models API returns a standardized JSON response format that provides comprehensive metadata for each available model. This schema is cached at the edge and designed for reliable integration for production applications.

#### Root Response Object

```code-block text-sm

1{2  "data": [3    /* Array of Model objects */4  ]5}
```

#### Model Object Schema

Each model in the `data` array contains the following standardized fields:

| Field | Type | Description |
| --- | --- | --- |
| `id` | `string` | Unique model identifier used in API requests (e.g., `"google/gemini-2.5-pro-preview"`) |
| `canonical_slug` | `string` | Permanent slug for the model that never changes |
| `name` | `string` | Human-readable display name for the model |
| `created` | `number` | Unix timestamp of when the model was added to OpenRouter |
| `description` | `string` | Detailed description of the model’s capabilities and characteristics |
| `context_length` | `number` | Maximum context window size in tokens |
| `architecture` | `Architecture` | Object describing the model’s technical capabilities |
| `pricing` | `Pricing` | Lowest price structure for using this model |
| `top_provider` | `TopProvider` | Configuration details for the primary provider |
| `per_request_limits` | Rate limiting information (null if no limits) |  |
| `supported_parameters` | `string[]` | Array of supported API parameters for this model |

#### Architecture Object

```code-block text-sm

1{2  "input_modalities": string[], // Supported input types: ["file", "image", "text"]3  "output_modalities": string[], // Supported output types: ["text"]4  "tokenizer": string,          // Tokenization method used5  "instruct_type": string | null // Instruction format type (null if not applicable)6}
```

#### Pricing Object

All pricing values are in USD per token/request/unit. A value of `"0"` indicates the feature is free.

```code-block text-sm

1{2  "prompt": string,           // Cost per input token3  "completion": string,       // Cost per output token4  "request": string,          // Fixed cost per API request5  "image": string,           // Cost per image input6  "web_search": string,      // Cost per web search operation7  "internal_reasoning": string, // Cost for internal reasoning tokens8  "input_cache_read": string,   // Cost per cached input token read9  "input_cache_write": string   // Cost per cached input token write10}
```

#### Top Provider Object

```code-block text-sm

1{2  "context_length": number,        // Provider-specific context limit3  "max_completion_tokens": number, // Maximum tokens in response4  "is_moderated": boolean         // Whether content moderation is applied5}
```

#### Supported Parameters

The `supported_parameters` array indicates which OpenAI-compatible parameters work with each model:

- `tools` \- Function calling capabilities
- `tool_choice` \- Tool selection control
- `max_tokens` \- Response length limiting
- `temperature` \- Randomness control
- `top_p` \- Nucleus sampling
- `reasoning` \- Internal reasoning mode
- `include_reasoning` \- Include reasoning in response
- `structured_outputs` \- JSON schema enforcement
- `response_format` \- Output format specification
- `stop` \- Custom stop sequences
- `frequency_penalty` \- Repetition reduction
- `presence_penalty` \- Topic diversity
- `seed` \- Deterministic outputs

##### Different models tokenize text in different ways

Some models break up text into chunks of multiple characters (GPT, Claude,
Llama, etc), while others tokenize by character (PaLM). This means that token
counts (and therefore costs) will vary between models, even when inputs and
outputs are the same. Costs are displayed and billed according to the
tokenizer for the model in use. You can use the `usage` field in the response
to get the token counts for the input and output.

If there are models or providers you are interested in that OpenRouter doesn’t have, please tell us about them in our [Discord channel](https://openrouter.ai/discord).

## For Providers

If you’re interested in working with OpenRouter, you can learn more on our [providers page](https://openrouter.ai/docs/use-cases/for-providers).