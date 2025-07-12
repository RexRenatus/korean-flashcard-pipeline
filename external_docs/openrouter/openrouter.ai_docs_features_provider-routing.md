---
url: "https://openrouter.ai/docs/features/provider-routing"
title: "Provider Routing | Intelligent Multi-Provider Request Routing | OpenRouter | Documentation"
---

OpenRouter routes requests to the best available providers for your model. By default, [requests are load balanced](https://openrouter.ai/docs/features/provider-routing#load-balancing-default-strategy) across the top providers to maximize uptime.

You can customize how your requests are routed using the `provider` object in the request body for [Chat Completions](https://openrouter.ai/docs/api-reference/chat-completion) and [Completions](https://openrouter.ai/docs/api-reference/completion).

For a complete list of valid provider names to use in the API, see the [full\\
provider schema](https://openrouter.ai/docs/features/provider-routing#json-schema-for-provider-preferences).

The `provider` object can contain the following fields:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `order` | string\[\] | - | List of provider slugs to try in order (e.g. `["anthropic", "openai"]`). [Learn more](https://openrouter.ai/docs/features/provider-routing#ordering-specific-providers) |
| `allow_fallbacks` | boolean | `true` | Whether to allow backup providers when the primary is unavailable. [Learn more](https://openrouter.ai/docs/features/provider-routing#disabling-fallbacks) |
| `require_parameters` | boolean | `false` | Only use providers that support all parameters in your request. [Learn more](https://openrouter.ai/docs/features/provider-routing#requiring-providers-to-support-all-parameters-beta) |
| `data_collection` | ”allow” \| “deny" | "allow” | Control whether to use providers that may store data. [Learn more](https://openrouter.ai/docs/features/provider-routing#requiring-providers-to-comply-with-data-policies) |
| `only` | string\[\] | - | List of provider slugs to allow for this request. [Learn more](https://openrouter.ai/docs/features/provider-routing#allowing-only-specific-providers) |
| `ignore` | string\[\] | - | List of provider slugs to skip for this request. [Learn more](https://openrouter.ai/docs/features/provider-routing#ignoring-providers) |
| `quantizations` | string\[\] | - | List of quantization levels to filter by (e.g. `["int4", "int8"]`). [Learn more](https://openrouter.ai/docs/features/provider-routing#quantization) |
| `sort` | string | - | Sort providers by price or throughput. (e.g. `"price"` or `"throughput"`). [Learn more](https://openrouter.ai/docs/features/provider-routing#provider-sorting) |
| `max_price` | object | - | The maximum pricing you want to pay for this request. [Learn more](https://openrouter.ai/docs/features/provider-routing#maximum-price) |

## Price-Based Load Balancing (Default Strategy)

For each model in your request, OpenRouter’s default behavior is to load balance requests across providers, prioritizing price.

If you are more sensitive to throughput than price, you can use the `sort` field to explicitly prioritize throughput.

When you send a request with `tools` or `tool_choice`, OpenRouter will only
route to providers that support tool use. Similarly, if you set a
`max_tokens`, then OpenRouter will only route to providers that support a
response of that length.

Here is OpenRouter’s default load balancing strategy:

1. Prioritize providers that have not seen significant outages in the last 30 seconds.
2. For the stable providers, look at the lowest-cost candidates and select one weighted by inverse square of the price (example below).
3. Use the remaining providers as fallbacks.

##### A Load Balancing Example

If Provider A costs $1 per million tokens, Provider B costs $2, and Provider C costs $3, and Provider B recently saw a few outages.

- Your request is routed to Provider A. Provider A is 9x more likely to be first routed to Provider A than Provider C because (1/32=1/9)(1 / 3^2 = 1/9)(1/32=1/9) (inverse square of the price).
- If Provider A fails, then Provider C will be tried next.
- If Provider C also fails, Provider B will be tried last.

If you have `sort` or `order` set in your provider preferences, load balancing will be disabled.

## Provider Sorting

As described above, OpenRouter load balances based on price, while taking uptime into account.

If you instead want to _explicitly_ prioritize a particular provider attribute, you can include the `sort` field in the `provider` preferences. Load balancing will be disabled, and the router will try providers in order.

The three sort options are:

- `"price"`: prioritize lowest price
- `"throughput"`: prioritize highest throughput
- `"latency"`: prioritize lowest latency

TypeScript Example with Fallbacks EnabledPython Example with Fallbacks Enabled

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'meta-llama/llama-3.1-70b-instruct',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'sort': 'throughput'19    }20  }),21});
```

To _always_ prioritize low prices, and not apply any load balancing, set `sort` to `"price"`.

To _always_ prioritize low latency, and not apply any load balancing, set `sort` to `"latency"`.

## Nitro Shortcut

You can append `:nitro` to any model slug as a shortcut to sort by throughput. This is exactly equivalent to setting `provider.sort` to `"throughput"`.

TypeScript Example using Nitro shortcutPython Example using Nitro shortcut

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'meta-llama/llama-3.1-70b-instruct:nitro',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ]17  }),18});
```

## Floor Price Shortcut

You can append `:floor` to any model slug as a shortcut to sort by price. This is exactly equivalent to setting `provider.sort` to `"price"`.

TypeScript Example using Floor shortcutPython Example using Floor shortcut

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'meta-llama/llama-3.1-70b-instruct:floor',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ]17  }),18});
```

## Ordering Specific Providers

You can set the providers that OpenRouter will prioritize for your request using the `order` field.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `order` | string\[\] | - | List of provider slugs to try in order (e.g. `["anthropic", "openai"]`). |

The router will prioritize providers in this list, and in this order, for the model you’re using. If you don’t set this field, the router will [load balance](https://openrouter.ai/docs/features/provider-routing#load-balancing-default-strategy) across the top providers to maximize uptime.

You can use the copy button next to provider names on model pages to get the exact provider slug,
including any variants like “/turbo”. See [Targeting Specific Provider Endpoints](https://openrouter.ai/docs/features/provider-routing#targeting-specific-provider-endpoints) for details.

OpenRouter will try them one at a time and proceed to other providers if none are operational. If you don’t want to allow any other providers, you should [disable fallbacks](https://openrouter.ai/docs/features/provider-routing#disabling-fallbacks) as well.

### Example: Specifying providers with fallbacks

This example skips over OpenAI (which doesn’t host Mixtral), tries Together, and then falls back to the normal list of providers on OpenRouter:

TypeScript Example with Fallbacks EnabledPython Example with Fallbacks Enabled

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'mistralai/mixtral-8x7b-instruct',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'order': [19        'openai',20        'together'21      ]22    }23  }),24});

```

### Example: Specifying providers with fallbacks disabled

Here’s an example with `allow_fallbacks` set to `false` that skips over OpenAI (which doesn’t host Mixtral), tries Together, and then fails if Together fails:

TypeScript Example with Fallbacks DisabledPython Example with Fallbacks Disabled

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'mistralai/mixtral-8x7b-instruct',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'order': [19        'openai',20        'together'21      ],22      'allow_fallbacks': false23    }24  }),25});

```

## Targeting Specific Provider Endpoints

Each provider on OpenRouter may host multiple endpoints for the same model, such as a default endpoint and a specialized “turbo” endpoint. To target a specific endpoint, you can use the copy button next to the provider name on the model detail page to obtain the exact provider slug.

For example, DeepInfra offers DeepSeek R1 through multiple endpoints:

- Default endpoint with slug `deepinfra`
- Turbo endpoint with slug `deepinfra/turbo`

By copying the exact provider slug and using it in your request’s `order` array, you can ensure your request is routed to the specific endpoint you want:

TypeScript Example targeting DeepInfra Turbo endpointPython Example targeting DeepInfra Turbo endpoint

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'deepseek/deepseek-r1',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'order': [19        'deepinfra/turbo'20      ],21      'allow_fallbacks': false22    }23  }),24});

```

This approach is especially useful when you want to consistently use a specific variant of a model from a particular provider.

## Requiring Providers to Support All Parameters

You can restrict requests only to providers that support all parameters in your request using the `require_parameters` field.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `require_parameters` | boolean | `false` | Only use providers that support all parameters in your request. |

With the default routing strategy, providers that don’t support all the [LLM parameters](https://openrouter.ai/docs/api-reference/parameters) specified in your request can still receive the request, but will ignore unknown parameters. When you set `require_parameters` to `true`, the request won’t even be routed to that provider.

### Example: Excluding providers that don’t support JSON formatting

For example, to only use providers that support JSON formatting:

TypeScript Python

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'messages': [11      {12        'role': 'user',13        'content': 'Hello'14      }15    ],16    'provider': {17      'require_parameters': true18    },19    'response_format': {20      'type': 'json_object'21    }22  }),23});

```

## Requiring Providers to Comply with Data Policies

You can restrict requests only to providers that comply with your data policies using the `data_collection` field.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `data_collection` | ”allow” \| “deny" | "allow” | Control whether to use providers that may store data. |

- `allow`: (default) allow providers which store user data non-transiently and may train on it
- `deny`: use only providers which do not collect user data

Some model providers may log prompts, so we display them with a **Data Policy** tag on model pages. This is not a definitive source of third party data policies, but represents our best knowledge.

##### Account-Wide Data Policy Filtering

This is also available as an account-wide setting in [your privacy\\
settings](https://openrouter.ai/settings/privacy). You can disable third party
model providers that store inputs for training.

### Example: Excluding providers that don’t comply with data policies

To exclude providers that don’t comply with your data policies, set `data_collection` to `deny`:

TypeScript Python

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'messages': [11      {12        'role': 'user',13        'content': 'Hello'14      }15    ],16    'provider': {17      'data_collection': 'deny'18    }19  }),20});
```

## Disabling Fallbacks

To guarantee that your request is only served by the top (lowest-cost) provider, you can disable fallbacks.

This is combined with the `order` field from [Ordering Specific Providers](https://openrouter.ai/docs/features/provider-routing#ordering-specific-providers) to restrict the providers that OpenRouter will prioritize to just your chosen list.

TypeScript Python

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'messages': [11      {12        'role': 'user',13        'content': 'Hello'14      }15    ],16    'provider': {17      'allow_fallbacks': false18    }19  }),20});
```

## Allowing Only Specific Providers

You can allow only specific providers for a request by setting the `only` field in the `provider` object.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `only` | string\[\] | - | List of provider slugs to allow for this request. |

Only allowing some providers may significantly reduce fallback options and
limit request recovery.

##### Account-Wide Allowed Providers

You can allow providers for all account requests by configuring your [preferences](https://openrouter.ai/settings/preferences). This configuration applies to all API requests and chatroom messages.

Note that when you allow providers for a specific request, the list of allowed providers is merged with your account-wide allowed providers.

### Example: Allowing Azure for a request calling GPT-4 Omni

Here’s an example that will only use Azure for a request calling GPT-4 Omni:

TypeScript Python

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'openai/gpt-4o',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'only': [19        'azure'20      ]21    }22  }),23});

```

## Ignoring Providers

You can ignore providers for a request by setting the `ignore` field in the `provider` object.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `ignore` | string\[\] | - | List of provider slugs to skip for this request. |

Ignoring multiple providers may significantly reduce fallback options and
limit request recovery.

##### Account-Wide Ignored Providers

You can ignore providers for all account requests by configuring your [preferences](https://openrouter.ai/settings/preferences). This configuration applies to all API requests and chatroom messages.

Note that when you ignore providers for a specific request, the list of ignored providers is merged with your account-wide ignored providers.

### Example: Ignoring DeepInfra for a request calling Llama 3.3 70b

Here’s an example that will ignore DeepInfra for a request calling Llama 3.3 70b:

TypeScript Python

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'meta-llama/llama-3.3-70b-instruct',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'ignore': [19        'deepinfra'20      ]21    }22  }),23});

```

## Quantization

Quantization reduces model size and computational requirements while aiming to preserve performance. Most LLMs today use FP16 or BF16 for training and inference, cutting memory requirements in half compared to FP32. Some optimizations use FP8 or quantization to reduce size further (e.g., INT8, INT4).

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `quantizations` | string\[\] | - | List of quantization levels to filter by (e.g. `["int4", "int8"]`). [Learn more](https://openrouter.ai/docs/features/provider-routing#quantization) |

Quantized models may exhibit degraded performance for certain prompts,
depending on the method used.

Providers can support various quantization levels for open-weight models.

### Quantization Levels

By default, requests are load-balanced across all available providers, ordered by price. To filter providers by quantization level, specify the `quantizations` field in the `provider` parameter with the following values:

- `int4`: Integer (4 bit)
- `int8`: Integer (8 bit)
- `fp4`: Floating point (4 bit)
- `fp6`: Floating point (6 bit)
- `fp8`: Floating point (8 bit)
- `fp16`: Floating point (16 bit)
- `bf16`: Brain floating point (16 bit)
- `fp32`: Floating point (32 bit)
- `unknown`: Unknown

### Example: Requesting FP8 Quantization

Here’s an example that will only use providers that support FP8 quantization:

TypeScript Python

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    'Authorization': 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    'model': 'meta-llama/llama-3.1-8b-instruct',11    'messages': [12      {13        'role': 'user',14        'content': 'Hello'15      }16    ],17    'provider': {18      'quantizations': [19        'fp8'20      ]21    }22  }),23});

```

### Max Price

To filter providers by price, specify the `max_price` field in the `provider` parameter with a JSON object specifying the highest provider pricing you will accept.

For example, the value `{"prompt": 1, "completion": 2}` will route to any provider with a price of `<= $1/m` prompt tokens, and `<= $2/m` completion tokens or less.

Some providers support per request pricing, in which case you can use the `request` attribute of max\_price. Lastly, `image` is also available, which specifies the max price per image you will accept.

Practically, this field is often combined with a provider `sort` to express, for example, “Use the provider with the highest throughput, as long as it doesn’t cost more than `$x/m` tokens.”

## Terms of Service

You can view the terms of service for each provider below. You may not violate the terms of service or policies of third-party providers that power the models on OpenRouter.

\- `Mistral`: [https://mistral.ai/terms/#terms-of-use](https://mistral.ai/terms/#terms-of-use)

\- `AionLabs`: [https://www.aionlabs.ai/terms/](https://www.aionlabs.ai/terms/)

\- `AtlasCloud`: [https://www.atlascloud.ai/privacy](https://www.atlascloud.ai/privacy)

\- `Atoma`: [https://atoma.network/terms\_of\_service](https://atoma.network/terms_of_service)

\- `Avian.io`: [https://avian.io/terms](https://avian.io/terms)

\- `Azure`: [https://www.microsoft.com/en-us/legal/terms-of-use?oneroute=true](https://www.microsoft.com/en-us/legal/terms-of-use?oneroute=true)

\- `Cloudflare`: [https://www.cloudflare.com/service-specific-terms-developer-platform/#developer-platform-terms](https://www.cloudflare.com/service-specific-terms-developer-platform/#developer-platform-terms)

\- `Cohere`: [https://cohere.com/terms-of-use](https://cohere.com/terms-of-use)

\- `DeepSeek`: [https://chat.deepseek.com/downloads/DeepSeek%20Terms%20of%20Use.html](https://chat.deepseek.com/downloads/DeepSeek%20Terms%20of%20Use.html)

\- `Enfer`: [https://enfer.ai/privacy-policy](https://enfer.ai/privacy-policy)

\- `Featherless`: [https://featherless.ai/terms](https://featherless.ai/terms)

\- `Friendli`: [https://friendli.ai/terms-of-service](https://friendli.ai/terms-of-service)

\- `OpenAI`: [https://openai.com/policies/row-terms-of-use/](https://openai.com/policies/row-terms-of-use/)

\- `OpenInference`: [https://www.openinference.xyz/terms](https://www.openinference.xyz/terms)

\- `Nebius AI Studio`: [https://docs.nebius.com/legal/studio/terms-of-use/](https://docs.nebius.com/legal/studio/terms-of-use/)

\- `Groq`: [https://groq.com/terms-of-use/](https://groq.com/terms-of-use/)

\- `Hyperbolic`: [https://hyperbolic.xyz/terms](https://hyperbolic.xyz/terms)

\- `Inception`: [https://www.inceptionlabs.ai/terms](https://www.inceptionlabs.ai/terms)

\- `inference.net`: [https://inference.net/terms-of-service](https://inference.net/terms-of-service)

\- `Lambda`: [https://lambda.ai/legal/terms-of-service](https://lambda.ai/legal/terms-of-service)

\- `Liquid`: [https://www.liquid.ai/terms-conditions](https://www.liquid.ai/terms-conditions)

\- `Mancer (private)`: [https://mancer.tech/terms](https://mancer.tech/terms)

\- `Minimax`: [https://www.minimax.io/platform/protocol/terms-of-service](https://www.minimax.io/platform/protocol/terms-of-service)

\- `nCompass`: [https://ncompass.tech/terms](https://ncompass.tech/terms)

\- `Crusoe`: [https://legal.crusoe.ai/open-router#managed-inference-tos-open-router](https://legal.crusoe.ai/open-router#managed-inference-tos-open-router)

\- `Inflection`: [https://developers.inflection.ai/tos](https://developers.inflection.ai/tos)

\- `Chutes`: [https://chutes.ai/tos](https://chutes.ai/tos)

\- `DeepInfra`: [https://deepinfra.com/terms](https://deepinfra.com/terms)

\- `CrofAI`: [https://ai.nahcrof.com/privacy](https://ai.nahcrof.com/privacy)

\- `AI21`: [https://www.ai21.com/terms-of-service/](https://www.ai21.com/terms-of-service/)

\- `Alibaba`: [https://www.alibabacloud.com/help/en/legal/latest/alibaba-cloud-international-website-product-terms-of-service-v-3-8-0](https://www.alibabacloud.com/help/en/legal/latest/alibaba-cloud-international-website-product-terms-of-service-v-3-8-0)

\- `Amazon Bedrock`: [https://aws.amazon.com/service-terms/](https://aws.amazon.com/service-terms/)

\- `Anthropic`: [https://www.anthropic.com/legal/commercial-terms](https://www.anthropic.com/legal/commercial-terms)

\- `Google Vertex`: [https://cloud.google.com/terms/](https://cloud.google.com/terms/)

\- `Fireworks`: [https://fireworks.ai/terms-of-service](https://fireworks.ai/terms-of-service)

\- `NovitaAI`: [https://novita.ai/legal/terms-of-service](https://novita.ai/legal/terms-of-service)

\- `NextBit`: [https://www.nextbit256.com/docs/terms-of-service](https://www.nextbit256.com/docs/terms-of-service)

\- `Nineteen`: [https://nineteen.ai/tos](https://nineteen.ai/tos)

\- `Baseten`: [https://www.baseten.co/terms-and-conditions](https://www.baseten.co/terms-and-conditions)

\- `Cerebras`: [https://www.cerebras.ai/terms-of-service](https://www.cerebras.ai/terms-of-service)

\- `GMICloud`: [https://docs.gmicloud.ai/privacy](https://docs.gmicloud.ai/privacy)

\- `Parasail`: [https://www.parasail.io/legal/terms](https://www.parasail.io/legal/terms)

\- `Perplexity`: [https://www.perplexity.ai/hub/legal/perplexity-api-terms-of-service](https://www.perplexity.ai/hub/legal/perplexity-api-terms-of-service)

\- `Phala`: [https://red-pill.ai/terms](https://red-pill.ai/terms)

\- `SambaNova`: [https://sambanova.ai/terms-and-conditions](https://sambanova.ai/terms-and-conditions)

\- `Ubicloud`: [https://www.ubicloud.com/docs/about/terms-of-service](https://www.ubicloud.com/docs/about/terms-of-service)

\- `Venice`: [https://venice.ai/legal/tos](https://venice.ai/legal/tos)

\- `xAI`: [https://x.ai/legal/terms-of-service](https://x.ai/legal/terms-of-service)

\- `Meta`: [https://llama.developer.meta.com/legal/terms-of-service](https://llama.developer.meta.com/legal/terms-of-service)

\- `kluster.ai`: [https://www.kluster.ai/terms-of-use](https://www.kluster.ai/terms-of-use)

\- `Targon`: [https://targon.com/terms](https://targon.com/terms)

\- `Infermatic`: [https://infermatic.ai/terms-and-conditions/](https://infermatic.ai/terms-and-conditions/)

\- `Morph`: [https://morphllm.com/privacy](https://morphllm.com/privacy)

\- `Google AI Studio`: [https://cloud.google.com/terms/](https://cloud.google.com/terms/)

\- `Together`: [https://www.together.ai/terms-of-service](https://www.together.ai/terms-of-service)

## JSON Schema for Provider Preferences

For a complete list of options, see this JSON schema:

Provider Preferences Schema

```code-block text-sm

1{2    "$ref": "#/definitions/Provider Preferences Schema",3    "definitions": {4      "Provider Preferences Schema": {5        "type": "object",6        "properties": {7          "allow_fallbacks": {8            "type": [9              "boolean",10              "null"11            ],12            "description": "Whether to allow backup providers to serve requests\n- true: (default) when the primary provider (or your custom providers in \"order\") is unavailable, use the next best provider.\n- false: use only the primary/custom provider, and return the upstream error if it's unavailable.\n"13          },14          "require_parameters": {15            "type": [16              "boolean",17              "null"18            ],19            "description": "Whether to filter providers to only those that support the parameters you've provided. If this setting is omitted or set to false, then providers will receive only the parameters they support, and ignore the rest."20          },21          "data_collection": {22            "anyOf": [23              {24                "type": "string",25                "enum": [26                  "deny",27                  "allow"28                ]29              },30              {31                "type": "null"32              }33            ],34            "description": "Data collection setting. If no available model provider meets the requirement, your request will return an error.\n- allow: (default) allow providers which store user data non-transiently and may train on it\n- deny: use only providers which do not collect user data.\n"35          },36          "order": {37            "anyOf": [38              {39                "type": "array",40                "items": {41                  "anyOf": [42                    {43                      "type": "string",44                      "enum": [45                        "AnyScale",46                        "Cent-ML",47                        "HuggingFace",48                        "Hyperbolic 2",49                        "Lepton",50                        "Lynn 2",51                        "Lynn",52                        "Mancer",53                        "Modal",54                        "OctoAI",55                        "Recursal",56                        "Reflection",57                        "Replicate",58                        "SambaNova 2",59                        "SF Compute",60                        "Together 2",61                        "01.AI",62                        "AI21",63                        "AionLabs",64                        "Alibaba",65                        "Amazon Bedrock",66                        "Anthropic",67                        "AtlasCloud",68                        "Atoma",69                        "Avian",70                        "Azure",71                        "BaseTen",72                        "Cerebras",73                        "Chutes",74                        "Cloudflare",75                        "Cohere",76                        "CrofAI",77                        "Crusoe",78                        "DeepInfra",79                        "DeepSeek",80                        "Enfer",81                        "Featherless",82                        "Fireworks",83                        "Friendli",84                        "GMICloud",85                        "Google",86                        "Google AI Studio",87                        "Groq",88                        "Hyperbolic",89                        "Inception",90                        "InferenceNet",91                        "Infermatic",92                        "Inflection",93                        "InoCloud",94                        "Kluster",95                        "Lambda",96                        "Liquid",97                        "Mancer 2",98                        "Meta",99                        "Minimax",100                        "Morph",101                        "Mistral",102                        "NCompass",103                        "Nebius",104                        "NextBit",105                        "Nineteen",106                        "Novita",107                        "OpenAI",108                        "OpenInference",109                        "Parasail",110                        "Perplexity",111                        "Phala",112                        "SambaNova",113                        "Stealth",114                        "Switchpoint",115                        "Targon",116                        "Together",117                        "Ubicloud",118                        "Venice",119                        "xAI"120                      ]121                    },122                    {123                      "type": "string"124                    }125                  ]126                }127              },128              {129                "type": "null"130              }131            ],132            "description": "An ordered list of provider slugs. The router will attempt to use the first provider in the subset of this list that supports your requested model, and fall back to the next if it is unavailable. If no providers are available, the request will fail with an error message."133          },134          "only": {135            "anyOf": [136              {137                "$ref": "#/definitions/Provider Preferences Schema/properties/order/anyOf/0"138              },139              {140                "type": "null"141              }142            ],143            "description": "List of provider slugs to allow. If provided, this list is merged with your account-wide allowed provider settings for this request."144          },145          "ignore": {146            "anyOf": [147              {148                "$ref": "#/definitions/Provider Preferences Schema/properties/order/anyOf/0"149              },150              {151                "type": "null"152              }153            ],154            "description": "List of provider slugs to ignore. If provided, this list is merged with your account-wide ignored provider settings for this request."155          },156          "quantizations": {157            "anyOf": [158              {159                "type": "array",160                "items": {161                  "type": "string",162                  "enum": [163                    "int4",164                    "int8",165                    "fp4",166                    "fp6",167                    "fp8",168                    "fp16",169                    "bf16",170                    "fp32",171                    "unknown"172                  ]173                }174              },175              {176                "type": "null"177              }178            ],179            "description": "A list of quantization levels to filter the provider by."180          },181          "sort": {182            "anyOf": [183              {184                "type": "string",185                "enum": [186                  "price",187                  "throughput",188                  "latency"189                ]190              },191              {192                "type": "null"193              }194            ],195            "description": "The sorting strategy to use for this request, if \"order\" is not specified. When set, no load balancing is performed."196          },197          "max_price": {198            "type": "object",199            "properties": {200              "prompt": {201                "anyOf": [202                  {203                    "type": "number"204                  },205                  {206                    "type": "string"207                  },208                  {}209                ]210              },211              "completion": {212                "$ref": "#/definitions/Provider Preferences Schema/properties/max_price/properties/prompt"213              },214              "image": {215                "$ref": "#/definitions/Provider Preferences Schema/properties/max_price/properties/prompt"216              },217              "request": {218                "$ref": "#/definitions/Provider Preferences Schema/properties/max_price/properties/prompt"219              }220            },221            "additionalProperties": false,222            "description": "The object specifying the maximum price you want to pay for this request. USD price per million tokens, for prompt and completion."223          },224          "experimental": {225            "anyOf": [226              {227                "type": "object",228                "properties": {},229                "additionalProperties": false230              },231              {232                "type": "null"233              }234            ]235          }236        },237        "additionalProperties": false238      }239    },240    "$schema": "http://json-schema.org/draft-07/schema#"241  }

```