---
url: "https://docs.anthropic.com/en/api/openai-sdk"
title: "OpenAI SDK compatibility - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

SDKs

OpenAI SDK compatibility

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

This compatibility layer is primarily intended to test and compare model capabilities, and is not considered a long-term or production-ready solution for most use cases. While we do intend to keep it fully functional and not make breaking changes, our priority is the reliability and effectiveness of the [Anthropic API](https://docs.anthropic.com/en/api/overview).

For more information on known compatibility limitations, see [Important OpenAI compatibility limitations](https://docs.anthropic.com/en/api/openai-sdk#important-openai-compatibility-limitations).

If you encounter any issues with the OpenAI SDK compatibility feature, please let us know [here](https://forms.gle/oQV4McQNiuuNbz9n8).

For the best experience and access to Anthropic API full feature set ( [PDF processing](https://docs.anthropic.com/en/docs/build-with-claude/pdf-support), [citations](https://docs.anthropic.com/en/docs/build-with-claude/citations), [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking), and [prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)), we recommend using the native [Anthropic API](https://docs.anthropic.com/en/api/getting-started).

## [​](https://docs.anthropic.com/en/api/openai-sdk\#getting-started-with-the-openai-sdk)  Getting started with the OpenAI SDK

To use the OpenAI SDK compatibility feature, you’ll need to:

1. Use an official OpenAI SDK
2. Change the following
   - Update your base URL to point to Anthropic’s API
   - Replace your API key with an [Anthropic API key](https://console.anthropic.com/settings/keys)
   - Update your model name to use a [Claude model](https://docs.anthropic.com/en/docs/about-claude/models#model-names)
3. Review the documentation below for what features are supported

### [​](https://docs.anthropic.com/en/api/openai-sdk\#quick-start-example)  Quick start example

Python

TypeScript

Copy

```Python
from openai import OpenAI

client = OpenAI(
    api_key="ANTHROPIC_API_KEY",  # Your Anthropic API key
    base_url="https://api.anthropic.com/v1/"  # Anthropic's API endpoint
)

response = client.chat.completions.create(
    model="claude-opus-4-20250514", # Anthropic model name
    messages=[\
        {"role": "system", "content": "You are a helpful assistant."},\
        {"role": "user", "content": "Who are you?"}\
    ],
)

print(response.choices[0].message.content)

```

## [​](https://docs.anthropic.com/en/api/openai-sdk\#important-openai-compatibility-limitations)  Important OpenAI compatibility limitations

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#api-behavior)  API behavior

Here are the most substantial differences from using OpenAI:

- The `strict` parameter for function calling is ignored, which means the tool use JSON is not guaranteed to follow the supplied schema.
- Audio input is not supported; it will simply be ignored and stripped from input
- Prompt caching is not supported, but it is supported in [the Anthropic SDK](https://docs.anthropic.com/en/api/client-sdks)
- System/developer messages are hoisted and concatenated to the beginning of the conversation, as Anthropic only supports a single initial system message.

Most unsupported fields are silently ignored rather than producing errors. These are all documented below.

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#output-quality-considerations)  Output quality considerations

If you’ve done lots of tweaking to your prompt, it’s likely to be well-tuned to OpenAI specifically. Consider using our [prompt improver in the Anthropic Console](https://console.anthropic.com/dashboard) as a good starting point.

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#system-%2F-developer-message-hoisting)  System / Developer message hoisting

Most of the inputs to the OpenAI SDK clearly map directly to Anthropic’s API parameters, but one distinct difference is the handling of system / developer prompts. These two prompts can be put throughout a chat conversation via OpenAI. Since Anthropic only supports an initial system message, we take all system/developer messages and concatenate them together with a single newline ( `\n`) in between them. This full string is then supplied as a single system message at the start of the messages.

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#extended-thinking-support)  Extended thinking support

You can enable [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) capabilities by adding the `thinking` parameter. While this will improve Claude’s reasoning for complex tasks, the OpenAI SDK won’t return Claude’s detailed thought process. For full extended thinking features, including access to Claude’s step-by-step reasoning output, use the native Anthropic API.

Python

TypeScript

Copy

```Python
response = client.chat.completions.create(
    model="claude-opus-4-20250514",
    messages=...,
    extra_body={
        "thinking": { "type": "enabled", "budget_tokens": 2000 }
    }
)

```

## [​](https://docs.anthropic.com/en/api/openai-sdk\#rate-limits)  Rate limits

Rate limits follow Anthropic’s [standard limits](https://docs.anthropic.com/en/api/rate-limits) for the `/v1/messages` endpoint.

## [​](https://docs.anthropic.com/en/api/openai-sdk\#detailed-openai-compatible-api-support)  Detailed OpenAI Compatible API Support

### [​](https://docs.anthropic.com/en/api/openai-sdk\#request-fields)  Request fields

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#simple-fields)  Simple fields

| Field | Support status |
| --- | --- |
| `model` | Use Claude model names |
| `max_tokens` | Fully supported |
| `max_completion_tokens` | Fully supported |
| `stream` | Fully supported |
| `stream_options` | Fully supported |
| `top_p` | Fully supported |
| `parallel_tool_calls` | Fully supported |
| `stop` | All non-whitespace stop sequences work |
| `temperature` | Between 0 and 1 (inclusive). Values greater than 1 are capped at 1. |
| `n` | Must be exactly 1 |
| `logprobs` | Ignored |
| `metadata` | Ignored |
| `response_format` | Ignored |
| `prediction` | Ignored |
| `presence_penalty` | Ignored |
| `frequency_penalty` | Ignored |
| `seed` | Ignored |
| `service_tier` | Ignored |
| `audio` | Ignored |
| `logit_bias` | Ignored |
| `store` | Ignored |
| `user` | Ignored |
| `modalities` | Ignored |
| `top_logprobs` | Ignored |
| `Reasoning_effort` | Ignored |

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#tools-%2F-functions-fields)  `tools` / `functions` fields

Show fields

- Tools
- Functions

`tools[n].function` fields

| Field | Support status |
| --- | --- |
| `name` | Fully supported |
| `description` | Fully supported |
| `parameters` | Fully supported |
| `strict` | Ignored |

`tools[n].function` fields

| Field | Support status |
| --- | --- |
| `name` | Fully supported |
| `description` | Fully supported |
| `parameters` | Fully supported |
| `strict` | Ignored |

`functions[n]` fields

OpenAI has deprecated the `functions` field and suggests using `tools` instead.

| Field | Support status |
| --- | --- |
| `name` | Fully supported |
| `description` | Fully supported |
| `parameters` | Fully supported |
| `strict` | Ignored |

#### [​](https://docs.anthropic.com/en/api/openai-sdk\#messages-array-fields)  `messages` array fields

Show fields

- Developer role
- System role
- User role
- Assistant role
- Tool role
- Function role

Fields for `messages[n].role == "developer"`

Developer messages are hoisted to beginning of conversation as part of the initial system message

| Field | Support status |
| --- | --- |
| `content` | Fully supported, but hoisted |
| `name` | Ignored |

Fields for `messages[n].role == "developer"`

Developer messages are hoisted to beginning of conversation as part of the initial system message

| Field | Support status |
| --- | --- |
| `content` | Fully supported, but hoisted |
| `name` | Ignored |

Fields for `messages[n].role == "system"`

System messages are hoisted to beginning of conversation as part of the initial system message

| Field | Support status |
| --- | --- |
| `content` | Fully supported, but hoisted |
| `name` | Ignored |

Fields for `messages[n].role == "user"`

| Field | Variant | Sub-field | Support status |
| --- | --- | --- | --- |
| `content` | `string` |  | Fully supported |
|  | `array`, `type == "text"` |  | Fully supported |
|  | `array`, `type == "image_url"` | `url` | Fully supported |
|  |  | `detail` | Ignored |
|  | `array`, `type == "input_audio"` |  | Ignored |
|  | `array`, `type == "file"` |  | Ignored |
| `name` |  |  | Ignored |

Fields for `messages[n].role == "assistant"`

| Field | Variant | Support status |
| --- | --- | --- |
| `content` | `string` | Fully supported |
|  | `array`, `type == "text"` | Fully supported |
|  | `array`, `type == "refusal"` | Ignored |
| `tool_calls` |  | Fully supported |
| `function_call` |  | Fully supported |
| `audio` |  | Ignored |
| `refusal` |  | Ignored |

Fields for `messages[n].role == "tool"`

| Field | Variant | Support status |
| --- | --- | --- |
| `content` | `string` | Fully supported |
|  | `array`, `type == "text"` | Fully supported |
| `tool_call_id` |  | Fully supported |
| `tool_choice` |  | Fully supported |
| `name` |  | Ignored |

Fields for `messages[n].role == "function"`

| Field | Variant | Support status |
| --- | --- | --- |
| `content` | `string` | Fully supported |
|  | `array`, `type == "text"` | Fully supported |
| `tool_choice` |  | Fully supported |
| `name` |  | Ignored |

### [​](https://docs.anthropic.com/en/api/openai-sdk\#response-fields)  Response fields

| Field | Support status |
| --- | --- |
| `id` | Fully supported |
| `choices[]` | Will always have a length of 1 |
| `choices[].finish_reason` | Fully supported |
| `choices[].index` | Fully supported |
| `choices[].message.role` | Fully supported |
| `choices[].message.content` | Fully supported |
| `choices[].message.tool_calls` | Fully supported |
| `object` | Fully supported |
| `created` | Fully supported |
| `model` | Fully supported |
| `finish_reason` | Fully supported |
| `content` | Fully supported |
| `usage.completion_tokens` | Fully supported |
| `usage.prompt_tokens` | Fully supported |
| `usage.total_tokens` | Fully supported |
| `usage.completion_tokens_details` | Always empty |
| `usage.prompt_tokens_details` | Always empty |
| `choices[].message.refusal` | Always empty |
| `choices[].message.audio` | Always empty |
| `logprobs` | Always empty |
| `service_tier` | Always empty |
| `system_fingerprint` | Always empty |

### [​](https://docs.anthropic.com/en/api/openai-sdk\#error-message-compatibility)  Error message compatibility

The compatibility layer maintains consistent error formats with the OpenAI API. However, the detailed error messages will not be equivalent. We recommend only using the error messages for logging and debugging.

### [​](https://docs.anthropic.com/en/api/openai-sdk\#header-compatibility)  Header compatibility

While the OpenAI SDK automatically manages headers, here is the complete list of headers supported by Anthropic’s API for developers who need to work with them directly.

| Header | Support Status |
| --- | --- |
| `x-ratelimit-limit-requests` | Fully supported |
| `x-ratelimit-limit-tokens` | Fully supported |
| `x-ratelimit-remaining-requests` | Fully supported |
| `x-ratelimit-remaining-tokens` | Fully supported |
| `x-ratelimit-reset-requests` | Fully supported |
| `x-ratelimit-reset-tokens` | Fully supported |
| `retry-after` | Fully supported |
| `request-id` | Fully supported |
| `openai-version` | Always `2020-10-01` |
| `authorization` | Fully supported |
| `openai-processing-ms` | Always empty |

Was this page helpful?

YesNo

[Client SDKs](https://docs.anthropic.com/en/api/client-sdks) [Messages examples](https://docs.anthropic.com/en/api/messages-examples)

On this page

- [Getting started with the OpenAI SDK](https://docs.anthropic.com/en/api/openai-sdk#getting-started-with-the-openai-sdk)
- [Quick start example](https://docs.anthropic.com/en/api/openai-sdk#quick-start-example)
- [Important OpenAI compatibility limitations](https://docs.anthropic.com/en/api/openai-sdk#important-openai-compatibility-limitations)
- [API behavior](https://docs.anthropic.com/en/api/openai-sdk#api-behavior)
- [Output quality considerations](https://docs.anthropic.com/en/api/openai-sdk#output-quality-considerations)
- [System / Developer message hoisting](https://docs.anthropic.com/en/api/openai-sdk#system-%2F-developer-message-hoisting)
- [Extended thinking support](https://docs.anthropic.com/en/api/openai-sdk#extended-thinking-support)
- [Rate limits](https://docs.anthropic.com/en/api/openai-sdk#rate-limits)
- [Detailed OpenAI Compatible API Support](https://docs.anthropic.com/en/api/openai-sdk#detailed-openai-compatible-api-support)
- [Request fields](https://docs.anthropic.com/en/api/openai-sdk#request-fields)
- [Simple fields](https://docs.anthropic.com/en/api/openai-sdk#simple-fields)
- [tools / functions fields](https://docs.anthropic.com/en/api/openai-sdk#tools-%2F-functions-fields)
- [messages array fields](https://docs.anthropic.com/en/api/openai-sdk#messages-array-fields)
- [Response fields](https://docs.anthropic.com/en/api/openai-sdk#response-fields)
- [Error message compatibility](https://docs.anthropic.com/en/api/openai-sdk#error-message-compatibility)
- [Header compatibility](https://docs.anthropic.com/en/api/openai-sdk#header-compatibility)