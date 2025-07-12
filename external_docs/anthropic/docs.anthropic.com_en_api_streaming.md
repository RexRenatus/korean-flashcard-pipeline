---
url: "https://docs.anthropic.com/en/api/streaming"
title: "Streaming Text Completions - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Text Completions (Legacy)

Streaming Text Completions

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

**Legacy API**

The Text Completions API is a legacy API. Future models and features will require use of the [Messages API](https://docs.anthropic.com/en/api/messages), and we recommend [migrating](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages) as soon as possible.

When creating a Text Completion, you can set `"stream": true` to incrementally stream the response using [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent%5Fevents/Using%5Fserver-sent%5Fevents) (SSE). If you are using our [client libraries](https://docs.anthropic.com/en/api/client-sdks), parsing these events will be handled for you automatically. However, if you are building a direct API integration, you will need to handle these events yourself.

## [​](https://docs.anthropic.com/en/api/streaming\#example)  Example

Shell

Copy

```bash
curl https://api.anthropic.com/v1/complete \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --data '
{
  "model": "claude-2",
  "prompt": "\n\nHuman: Hello, world!\n\nAssistant:",
  "max_tokens_to_sample": 256,
  "stream": true
}
'

```

Response

Copy

```json
event: completion
data: {"type": "completion", "completion": " Hello", "stop_reason": null, "model": "claude-2.0"}

event: completion
data: {"type": "completion", "completion": "!", "stop_reason": null, "model": "claude-2.0"}

event: ping
data: {"type": "ping"}

event: completion
data: {"type": "completion", "completion": " My", "stop_reason": null, "model": "claude-2.0"}

event: completion
data: {"type": "completion", "completion": " name", "stop_reason": null, "model": "claude-2.0"}

event: completion
data: {"type": "completion", "completion": " is", "stop_reason": null, "model": "claude-2.0"}

event: completion
data: {"type": "completion", "completion": " Claude", "stop_reason": null, "model": "claude-2.0"}

event: completion
data: {"type": "completion", "completion": ".", "stop_reason": null, "model": "claude-2.0"}

event: completion
data: {"type": "completion", "completion": "", "stop_reason": "stop_sequence", "model": "claude-2.0"}

```

## [​](https://docs.anthropic.com/en/api/streaming\#events)  Events

Each event includes a named event type and associated JSON data.

Event types: `completion`, `ping`, `error`.

### [​](https://docs.anthropic.com/en/api/streaming\#error-event-types)  Error event types

We may occasionally send [errors](https://docs.anthropic.com/en/api/errors) in the event stream. For example, during periods of high usage, you may receive an `overloaded_error`, which would normally correspond to an HTTP 529 in a non-streaming context:

Example error

Copy

```json
event: completion
data: {"completion": " Hello", "stop_reason": null, "model": "claude-2.0"}

event: error
data: {"error": {"type": "overloaded_error", "message": "Overloaded"}}

```

## [​](https://docs.anthropic.com/en/api/streaming\#older-api-versions)  Older API versions

If you are using an [API version](https://docs.anthropic.com/en/api/versioning) prior to `2023-06-01`, the response shape will be different. See [versioning](https://docs.anthropic.com/en/api/versioning) for details.

Was this page helpful?

YesNo

[Create a Text Completion](https://docs.anthropic.com/en/api/complete) [Prompt validation](https://docs.anthropic.com/en/api/prompt-validation)

On this page

- [Example](https://docs.anthropic.com/en/api/streaming#example)
- [Events](https://docs.anthropic.com/en/api/streaming#events)
- [Error event types](https://docs.anthropic.com/en/api/streaming#error-event-types)
- [Older API versions](https://docs.anthropic.com/en/api/streaming#older-api-versions)