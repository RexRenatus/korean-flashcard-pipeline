---
url: "https://docs.anthropic.com/en/api/complete"
title: "Create a Text Completion - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Text Completions (Legacy)

Create a Text Completion

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

POST

/

v1

/

complete

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/complete \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-2.1",
    "max_tokens_to_sample": 1024,
    "prompt": "\n\nHuman: Hello, Claude\n\nAssistant:"
}'
```

200

4XX

Copy

```
{
  "completion": " Hello! My name is Claude.",
  "id": "compl_018CKm6gsux7P8yMcwZbeCPw",
  "model": "claude-2.1",
  "stop_reason": "stop_sequence",
  "type": "completion"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/complete#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/complete#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

[​](https://docs.anthropic.com/en/api/complete#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

#### Body

application/json

[​](https://docs.anthropic.com/en/api/complete#body-model)

model

string

required

The model that will complete your prompt.

See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.

Examples:

`"claude-2.1"`

[​](https://docs.anthropic.com/en/api/complete#body-prompt)

prompt

string

required

The prompt that you want Claude to complete.

For proper response generation you will need to format your prompt using alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

```
"\n\nHuman: {userQuestion}\n\nAssistant:"

```

See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and our guide to [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more details.

Minimum length: `1`

Examples:

`"\n\nHuman: Hello, world!\n\nAssistant:"`

[​](https://docs.anthropic.com/en/api/complete#body-max-tokens-to-sample)

max\_tokens\_to\_sample

integer

required

The maximum number of tokens to generate before stopping.

Note that our models may stop _before_ reaching this maximum. This parameter only specifies the absolute maximum number of tokens to generate.

Required range: `x >= 1`

Examples:

`256`

[​](https://docs.anthropic.com/en/api/complete#body-stop-sequences)

stop\_sequences

string\[\]

Sequences that will cause the model to stop generating.

Our models stop on `"\n\nHuman:"`, and may include additional built-in stop sequences in the future. By providing the stop\_sequences parameter, you may include additional strings that will cause the model to stop generating.

[​](https://docs.anthropic.com/en/api/complete#body-temperature)

temperature

number

Amount of randomness injected into the response.

Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0` for analytical / multiple choice, and closer to `1.0` for creative and generative tasks.

Note that even with `temperature` of `0.0`, the results will not be fully deterministic.

Required range: `0 <= x <= 1`

Examples:

`1`

[​](https://docs.anthropic.com/en/api/complete#body-top-p)

top\_p

number

Use nucleus sampling.

In nucleus sampling, we compute the cumulative distribution over all the options for each subsequent token in decreasing probability order and cut it off once it reaches a particular probability specified by `top_p`. You should either alter `temperature` or `top_p`, but not both.

Recommended for advanced use cases only. You usually only need to use `temperature`.

Required range: `0 <= x <= 1`

Examples:

`0.7`

[​](https://docs.anthropic.com/en/api/complete#body-top-k)

top\_k

integer

Only sample from the top K options for each subsequent token.

Used to remove "long tail" low probability responses. [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

Recommended for advanced use cases only. You usually only need to use `temperature`.

Required range: `x >= 0`

Examples:

`5`

[​](https://docs.anthropic.com/en/api/complete#body-metadata)

metadata

object

An object describing metadata about the request.

Showchild attributes

[​](https://docs.anthropic.com/en/api/complete#body-metadata-user-id)

metadata.user\_id

string \| null

An external identifier for the user who is associated with the request.

This should be a uuid, hash value, or other opaque identifier. Anthropic may use this id to help detect abuse. Do not include any identifying information such as name, email address, or phone number.

Maximum length: `256`

Examples:

`"13803d75-b4b5-4c3e-b2a2-6f21399b021b"`

[​](https://docs.anthropic.com/en/api/complete#body-stream)

stream

boolean

Whether to incrementally stream the response using server-sent events.

See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

#### Response

200

2004XX

application/json

Text Completion object.

[​](https://docs.anthropic.com/en/api/complete#response-completion)

completion

string

required

The resulting completion up to and excluding the stop sequences.

Examples:

`" Hello! My name is Claude."`

[​](https://docs.anthropic.com/en/api/complete#response-id)

id

string

required

Unique object identifier.

The format and length of IDs may change over time.

[​](https://docs.anthropic.com/en/api/complete#response-model)

model

string

required

The model that handled the request.

Examples:

`"claude-2.1"`

[​](https://docs.anthropic.com/en/api/complete#response-stop-reason)

stop\_reason

string \| null

required

The reason that we stopped.

This may be one the following values:

- `"stop_sequence"`: we reached a stop sequence — either provided by you via the `stop_sequences` parameter, or a stop sequence built into the model
- `"max_tokens"`: we exceeded `max_tokens_to_sample` or the model's maximum

Examples:

`"stop_sequence"`

[​](https://docs.anthropic.com/en/api/complete#response-type)

type

enum<string>

default:completion

required

Object type.

For Text Completions, this is always `"completion"`.

Available options:

`completion`

Was this page helpful?

YesNo

[Migrating from Text Completions](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages) [Streaming Text Completions](https://docs.anthropic.com/en/api/streaming)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/complete \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-2.1",
    "max_tokens_to_sample": 1024,
    "prompt": "\n\nHuman: Hello, Claude\n\nAssistant:"
}'
```

200

4XX

Copy

```
{
  "completion": " Hello! My name is Claude.",
  "id": "compl_018CKm6gsux7P8yMcwZbeCPw",
  "model": "claude-2.1",
  "stop_reason": "stop_sequence",
  "type": "completion"
}
```