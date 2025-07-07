---
url: "https://openrouter.ai/docs/api-reference/overview"
title: "OpenRouter API Reference | Complete API Documentation | OpenRouter | Documentation"
---

OpenRouter’s request and response schemas are very similar to the OpenAI Chat API, with a few small differences. At a high level, **OpenRouter normalizes the schema across models and providers** so you only need to learn one.

## Requests

### Completions Request Format

Here is the request schema as a TypeScript type. This will be the body of your `POST` request to the `/api/v1/chat/completions` endpoint (see the [quick start](https://openrouter.ai/docs/quick-start) above for an example).

For a complete list of parameters, see the [Parameters](https://openrouter.ai/docs/api-reference/parameters).

Request Schema

```code-block text-sm

1// Definitions of subtypes are below2type Request = {3  // Either "messages" or "prompt" is required4  messages?: Message[];5  prompt?: string;67  // If "model" is unspecified, uses the user's default8  model?: string; // See "Supported Models" section910  // Allows to force the model to produce specific output format.11  // See models page and note on this docs page for which models support it.12  response_format?: { type: 'json_object' };1314  stop?: string | string[];15  stream?: boolean; // Enable streaming1617  // See LLM Parameters (openrouter.ai/docs/api-reference/parameters)18  max_tokens?: number; // Range: [1, context_length)19  temperature?: number; // Range: [0, 2]2021  // Tool calling22  // Will be passed down as-is for providers implementing OpenAI's interface.23  // For providers with custom interfaces, we transform and map the properties.24  // Otherwise, we transform the tools into a YAML template. The model responds with an assistant message.25  // See models supporting tool calling: openrouter.ai/models?supported_parameters=tools26  tools?: Tool[];27  tool_choice?: ToolChoice;2829  // Advanced optional parameters30  seed?: number; // Integer only31  top_p?: number; // Range: (0, 1]32  top_k?: number; // Range: [1, Infinity) Not available for OpenAI models33  frequency_penalty?: number; // Range: [-2, 2]34  presence_penalty?: number; // Range: [-2, 2]35  repetition_penalty?: number; // Range: (0, 2]36  logit_bias?: { [key: number]: number };37  top_logprobs: number; // Integer only38  min_p?: number; // Range: [0, 1]39  top_a?: number; // Range: [0, 1]4041  // Reduce latency by providing the model with a predicted output42  // https://platform.openai.com/docs/guides/latency-optimization#use-predicted-outputs43  prediction?: { type: 'content'; content: string };4445  // OpenRouter-only parameters46  // See "Prompt Transforms" section: openrouter.ai/docs/transforms47  transforms?: string[];48  // See "Model Routing" section: openrouter.ai/docs/model-routing49  models?: string[];50  route?: 'fallback';51  // See "Provider Routing" section: openrouter.ai/docs/provider-routing52  provider?: ProviderPreferences;53  user?: string; // A stable identifier for your end-users. Used to help detect and prevent abuse.54};5556// Subtypes:5758type TextContent = {59  type: 'text';60  text: string;61};6263type ImageContentPart = {64  type: 'image_url';65  image_url: {66    url: string; // URL or base64 encoded image data67    detail?: string; // Optional, defaults to "auto"68  };69};7071type ContentPart = TextContent | ImageContentPart;7273type Message =74  | {75      role: 'user' | 'assistant' | 'system';76      // ContentParts are only for the "user" role:77      content: string | ContentPart[];78      // If "name" is included, it will be prepended like this79      // for non-OpenAI models: `{name}: {content}`80      name?: string;81    }82  | {83      role: 'tool';84      content: string;85      tool_call_id: string;86      name?: string;87    };8889type FunctionDescription = {90  description?: string;91  name: string;92  parameters: object; // JSON Schema object93};9495type Tool = {96  type: 'function';97  function: FunctionDescription;98};99100type ToolChoice =101  | 'none'102  | 'auto'103  | {104      type: 'function';105      function: {106        name: string;107      };108    };

```

The `response_format` parameter ensures you receive a structured response from the LLM. The parameter is only supported by OpenAI models, Nitro models, and some others - check the providers on the model page on openrouter.ai/models to see if it’s supported, and set `require_parameters` to true in your Provider Preferences. See [Provider Routing](https://openrouter.ai/docs/features/provider-routing)

### Headers

OpenRouter allows you to specify some optional headers to identify your app and make it discoverable to users on our site.

- `HTTP-Referer`: Identifies your app on openrouter.ai
- `X-Title`: Sets/modifies your app’s title

TypeScript

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    Authorization: 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    model: 'openai/gpt-4o',11    messages: [12      {13        role: 'user',14        content: 'What is the meaning of life?',15      },16    ],17  }),18});
```

##### Model routing

If the `model` parameter is omitted, the user or payer’s default is used.
Otherwise, remember to select a value for `model` from the [supported\\
models](https://openrouter.ai/models) or [API](https://openrouter.ai/api/v1/models), and include the organization
prefix. OpenRouter will select the least expensive and best GPUs available to
serve the request, and fall back to other providers or GPUs if it receives a
5xx response code or if you are rate-limited.

##### Streaming

[Server-Sent Events\\
(SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#event_stream_format)
are supported as well, to enable streaming _for all models_. Simply send
`stream: true` in your request body. The SSE stream will occasionally contain
a “comment” payload, which you should ignore (noted below).

##### Non-standard parameters

If the chosen model doesn’t support a request parameter (such as `logit_bias`
in non-OpenAI models, or `top_k` for OpenAI), then the parameter is ignored.
The rest are forwarded to the underlying model API.

### Assistant Prefill

OpenRouter supports asking models to complete a partial response. This can be useful for guiding models to respond in a certain way.

To use this features, simply include a message with `role: "assistant"` at the end of your `messages` array.

TypeScript

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    Authorization: 'Bearer <OPENROUTER_API_KEY>',5    'Content-Type': 'application/json',6  },7  body: JSON.stringify({8    model: 'openai/gpt-4o',9    messages: [10      { role: 'user', content: 'What is the meaning of life?' },11      { role: 'assistant', content: "I'm not sure, but my best guess is" },12    ],13  }),14});
```

## Responses

### CompletionsResponse Format

OpenRouter normalizes the schema across models and providers to comply with the [OpenAI Chat API](https://platform.openai.com/docs/api-reference/chat).

This means that `choices` is always an array, even if the model only returns one completion. Each choice will contain a `delta` property if a stream was requested and a `message` property otherwise. This makes it easier to use the same code for all models.

Here’s the response schema as a TypeScript type:

TypeScript

```code-block text-sm

1// Definitions of subtypes are below2type Response = {3  id: string;4  // Depending on whether you set "stream" to "true" and5  // whether you passed in "messages" or a "prompt", you6  // will get a different output shape7  choices: (NonStreamingChoice | StreamingChoice | NonChatChoice)[];8  created: number; // Unix timestamp9  model: string;10  object: 'chat.completion' | 'chat.completion.chunk';1112  system_fingerprint?: string; // Only present if the provider supports it1314  // Usage data is always returned for non-streaming.15  // When streaming, you will get one usage object at16  // the end accompanied by an empty choices array.17  usage?: ResponseUsage;18};
```

```code-block text-sm

1// If the provider returns usage, we pass it down2// as-is. Otherwise, we count using the GPT-4 tokenizer.34type ResponseUsage = {5  /** Including images and tools if any */6  prompt_tokens: number;7  /** The tokens generated */8  completion_tokens: number;9  /** Sum of the above two fields */10  total_tokens: number;11};
```

```code-block text-sm

1// Subtypes:2type NonChatChoice = {3  finish_reason: string | null;4  text: string;5  error?: ErrorResponse;6};78type NonStreamingChoice = {9  finish_reason: string | null;10  native_finish_reason: string | null;11  message: {12    content: string | null;13    role: string;14    tool_calls?: ToolCall[];15  };16  error?: ErrorResponse;17};1819type StreamingChoice = {20  finish_reason: string | null;21  native_finish_reason: string | null;22  delta: {23    content: string | null;24    role?: string;25    tool_calls?: ToolCall[];26  };27  error?: ErrorResponse;28};2930type ErrorResponse = {31  code: number; // See "Error Handling" section32  message: string;33  metadata?: Record<string, unknown>; // Contains additional error information such as provider details, the raw error message, etc.34};3536type ToolCall = {37  id: string;38  type: 'function';39  function: FunctionCall;40};

```

Here’s an example:

```code-block text-sm

1{2  "id": "gen-xxxxxxxxxxxxxx",3  "choices": [4    {5      "finish_reason": "stop", // Normalized finish_reason6      "native_finish_reason": "stop", // The raw finish_reason from the provider7      "message": {8        // will be "delta" if streaming9        "role": "assistant",10        "content": "Hello there!"11      }12    }13  ],14  "usage": {15    "prompt_tokens": 0,16    "completion_tokens": 4,17    "total_tokens": 418  },19  "model": "openai/gpt-3.5-turbo" // Could also be "anthropic/claude-2.1", etc, depending on the "model" that ends up being used20}
```

### Finish Reason

OpenRouter normalizes each model’s `finish_reason` to one of the following values: `tool_calls`, `stop`, `length`, `content_filter`, `error`.

Some models and providers may have additional finish reasons. The raw finish\_reason string returned by the model is available via the `native_finish_reason` property.

### Querying Cost and Stats

The token counts that are returned in the completions API response are **not** counted via the model’s native tokenizer. Instead it uses a normalized, model-agnostic count (accomplished via the GPT4o tokenizer). This is because some providers do not reliably return native token counts. This behavior is becoming more rare, however, and we may add native token counts to the response object in the future.

Credit usage and model pricing are based on the **native** token counts (not the ‘normalized’ token counts returned in the API response).

For precise token accounting using the model’s native tokenizer, you can retrieve the full generation information via the `/api/v1/generation` endpoint.

You can use the returned `id` to query for the generation stats (including token counts and cost) after the request is complete. This is how you can get the cost and tokens for _all models and requests_, streaming and non-streaming.

Query Generation Stats

```code-block text-sm

1const generation = await fetch(2  'https://openrouter.ai/api/v1/generation?id=$GENERATION_ID',3  { headers },4);56const stats = await generation.json();
```

Please see the [Generation](https://openrouter.ai/docs/api-reference/get-a-generation) API reference for the full response shape.

Note that token counts are also available in the `usage` field of the response body for non-streaming completions.