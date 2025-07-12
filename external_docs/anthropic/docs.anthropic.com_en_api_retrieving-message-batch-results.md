---
url: "https://docs.anthropic.com/en/api/retrieving-message-batch-results"
title: "Retrieve Message Batch Results - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Message Batches

Retrieve Message Batch Results

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

messages

/

batches

/

{message\_batch\_id}

/

results

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d/results \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```JSON
{"custom_id":"my-second-request","result":{"type":"succeeded","message":{"id":"msg_014VwiXbi91y3JMjcpyGBHX5","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello again! It's nice to see you. How can I assist you today? Is there anything specific you'd like to chat about or any questions you have?"}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":11,"output_tokens":36}}}}
{"custom_id":"my-first-request","result":{"type":"succeeded","message":{"id":"msg_01FqfsLoHwgeFbguDgpz48m7","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello! How can I assist you today? Feel free to ask me any questions or let me know if there's anything you'd like to chat about."}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":10,"output_tokens":34}}}}

```

The path for retrieving Message Batch results should be pulled from the batch’s `results_url`. This path should not be assumed and may change.

#### Headers

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

#### Path Parameters

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#parameter-message-batch-id)

message\_batch\_id

string

required

ID of the Message Batch.

#### Response

200

2004XX

application/x-jsonl

Successful Response

This is a single line in the response `.jsonl` file and does not represent the response as a whole.

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-custom-id)

custom\_id

string

required

Developer-provided ID created for each request in a Message Batch. Useful for matching results to requests, as results may be given out of request order.

Must be unique for each request within the Message Batch.

Examples:

`"my-custom-id-1"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result)

result

object

required

Processing result for this request.

Contains a Message output if processing was successful, an error response if processing failed, or the reason why processing was not attempted, such as cancellation or expiration.

- SucceededResult
- ErroredResult
- CanceledResult
- ExpiredResult

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message)

result.message

object

required

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-id)

result.message.id

string

required

Unique object identifier.

The format and length of IDs may change over time.

Examples:

`"msg_013Zva2CMHLNnXjNJJKqJ2EF"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-type)

result.message.type

enum<string>

default:message

required

Object type.

For Messages, this is always `"message"`.

Available options:

`message`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-role)

result.message.role

enum<string>

default:assistant

required

Conversational role of the generated message.

This will always be `"assistant"`.

Available options:

`assistant`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-content)

result.message.content

object\[\]

required

Content generated by the model.

This is an array of content blocks, each of which has a `type` that determines its shape.

Example:

```json
[{"type": "text", "text": "Hi, I'm Claude."}]

```

If the request input `messages` ended with an `assistant` turn, then the response `content` will continue directly from that last turn. You can use this to constrain the model's output.

For example, if the input `messages` were:

```json
[\
  {"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},\
  {"role": "assistant", "content": "The best answer is ("}\
]

```

Then the response `content` might be:

```json
[{"type": "text", "text": "B)"}]

```

- Thinking
- Redacted thinking
- Tool use
- Server tool use
- Web search tool result
- Code execution tool result
- MCP tool use
- MCP tool result
- Container upload

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-content-signature)

result.message.content.signature

string

required

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-content-thinking)

result.message.content.thinking

string

required

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-content-type)

result.message.content.type

enum<string>

default:thinking

required

Available options:

`thinking`

Examples:

```json
[\
  {\
    "text": "Hi! My name is Claude.",\
    "type": "text"\
  }\
]

```

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-model)

result.message.model

string

required

The model that handled the request.

Required string length: `1 - 256`

Examples:

`"claude-sonnet-4-20250514"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-stop-reason)

result.message.stop\_reason

enum<string> \| null

required

The reason that we stopped.

This may be one the following values:

- `"end_turn"`: the model reached a natural stopping point
- `"max_tokens"`: we exceeded the requested `max_tokens` or the model's maximum
- `"stop_sequence"`: one of your provided custom `stop_sequences` was generated
- `"tool_use"`: the model invoked one or more tools
- `"pause_turn"`: we paused a long-running turn. You may provide the response back as-is in a subsequent request to let the model continue.
- `"refusal"`: when streaming classifiers intervene to handle potential policy violations

In non-streaming mode this value is always non-null. In streaming mode, it is null in the `message_start` event and non-null otherwise.

Available options:

`end_turn`,

`max_tokens`,

`stop_sequence`,

`tool_use`,

`pause_turn`,

`refusal`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-stop-sequence)

result.message.stop\_sequence

string \| null

required

Which custom stop sequence was generated, if any.

This value will be a non-null string if one of your custom stop sequences was generated.

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage)

result.message.usage

object

required

Billing and rate-limit usage.

Anthropic's API bills and rate-limits by token counts, as tokens represent the underlying cost to our systems.

Under the hood, the API transforms requests into a format suitable for the model. The model's output then goes through a parsing stage before becoming an API response. As a result, the token counts in `usage` will not match one-to-one with the exact visible content of an API request or response.

For example, `output_tokens` will be non-zero, even for an empty string response from Claude.

Total input tokens in a request is the summation of `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`.

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-cache-creation)

result.message.usage.cache\_creation

object \| null

required

Breakdown of cached tokens by TTL

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-cache-creation-ephemeral-1h-input-tokens)

result.message.usage.cache\_creation.ephemeral\_1h\_input\_tokens

integer

default:0

required

The number of input tokens used to create the 1 hour cache entry.

Required range: `x >= 0`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-cache-creation-ephemeral-5m-input-tokens)

result.message.usage.cache\_creation.ephemeral\_5m\_input\_tokens

integer

default:0

required

The number of input tokens used to create the 5 minute cache entry.

Required range: `x >= 0`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-cache-creation-input-tokens)

result.message.usage.cache\_creation\_input\_tokens

integer \| null

required

The number of input tokens used to create the cache entry.

Required range: `x >= 0`

Examples:

`2051`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-cache-read-input-tokens)

result.message.usage.cache\_read\_input\_tokens

integer \| null

required

The number of input tokens read from the cache.

Required range: `x >= 0`

Examples:

`2051`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-input-tokens)

result.message.usage.input\_tokens

integer

required

The number of input tokens which were used.

Required range: `x >= 0`

Examples:

`2095`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-output-tokens)

result.message.usage.output\_tokens

integer

required

The number of output tokens which were used.

Required range: `x >= 0`

Examples:

`503`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-server-tool-use)

result.message.usage.server\_tool\_use

object \| null

required

The number of server tool requests.

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-server-tool-use-web-search-requests)

result.message.usage.server\_tool\_use.web\_search\_requests

integer

default:0

required

The number of web search tool requests.

Required range: `x >= 0`

Examples:

`0`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-usage-service-tier)

result.message.usage.service\_tier

enum<string> \| null

required

If the request used the priority, standard, or batch tier.

Available options:

`standard`,

`priority`,

`batch`

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-container)

result.message.container

object \| null

required

Information about the container used in this request.

This will be non-null if a container tool (e.g. code execution) was used.

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-container-expires-at)

result.message.container.expires\_at

string

required

The time at which the container will expire.

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-message-container-id)

result.message.container.id

string

required

Identifier for the container used in this request

Examples:

```json
{
  "content": [\
    {\
      "text": "Hi! My name is Claude.",\
      "type": "text"\
    }\
  ],
  "id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
  "model": "claude-sonnet-4-20250514",
  "role": "assistant",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "type": "message",
  "usage": {
    "input_tokens": 2095,
    "output_tokens": 503
  }
}

```

[​](https://docs.anthropic.com/en/api/retrieving-message-batch-results#response-result-type)

result.type

enum<string>

default:succeeded

required

Available options:

`succeeded`

Was this page helpful?

YesNo

[Retrieve a Message Batch](https://docs.anthropic.com/en/api/retrieving-message-batches) [List Message Batches](https://docs.anthropic.com/en/api/listing-message-batches)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d/results \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```JSON
{"custom_id":"my-second-request","result":{"type":"succeeded","message":{"id":"msg_014VwiXbi91y3JMjcpyGBHX5","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello again! It's nice to see you. How can I assist you today? Is there anything specific you'd like to chat about or any questions you have?"}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":11,"output_tokens":36}}}}
{"custom_id":"my-first-request","result":{"type":"succeeded","message":{"id":"msg_01FqfsLoHwgeFbguDgpz48m7","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello! How can I assist you today? Feel free to ask me any questions or let me know if there's anything you'd like to chat about."}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":10,"output_tokens":34}}}}

```