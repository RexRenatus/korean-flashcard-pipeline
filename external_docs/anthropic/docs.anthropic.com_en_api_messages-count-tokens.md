---
url: "https://docs.anthropic.com/en/api/messages-count-tokens"
title: "Count Message tokens - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Messages

Count Message tokens

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

POST

/

v1

/

messages

/

count\_tokens

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/messages/count_tokens \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-3-7-sonnet-20250219",
    "messages": [\
        {"role": "user", "content": "Hello, world"}\
    ]
}'
```

200

4XX

Copy

```
{
  "input_tokens": 2095
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/messages-count-tokens#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

[​](https://docs.anthropic.com/en/api/messages-count-tokens#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/messages-count-tokens#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

#### Body

application/json

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-messages)

messages

object\[\]

required

Input messages.

Our models are trained to operate on alternating `user` and `assistant` conversational turns. When creating a new `Message`, you specify the prior conversational turns with the `messages` parameter, and the model then generates the next `Message` in the conversation. Consecutive `user` or `assistant` turns in your request will be combined into a single turn.

Each input message must be an object with a `role` and `content`. You can specify a single `user`-role message, or you can include multiple `user` and `assistant` messages.

If the final message uses the `assistant` role, the response content will continue immediately from the content in that message. This can be used to constrain part of the model's response.

Example with a single `user` message:

```json
[{"role": "user", "content": "Hello, Claude"}]

```

Example with multiple conversational turns:

```json
[\
  {"role": "user", "content": "Hello there."},\
  {"role": "assistant", "content": "Hi, I'm Claude. How can I help you?"},\
  {"role": "user", "content": "Can you explain LLMs in plain English?"},\
]

```

Example with a partially-filled response from Claude:

```json
[\
  {"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},\
  {"role": "assistant", "content": "The best answer is ("},\
]

```

Each input message `content` may be either a single `string` or an array of content blocks, where each block has a specific `type`. Using a `string` for `content` is shorthand for an array of one content block of type `"text"`. The following input messages are equivalent:

```json
{"role": "user", "content": "Hello, Claude"}

```

```json
{"role": "user", "content": [{"type": "text", "text": "Hello, Claude"}]}

```

Starting with Claude 3 models, you can also send image content blocks:

```json
{"role": "user", "content": [\
  {\
    "type": "image",\
    "source": {\
      "type": "base64",\
      "media_type": "image/jpeg",\
      "data": "/9j/4AAQSkZJRg...",\
    }\
  },\
  {"type": "text", "text": "What is in this image?"}\
]}

```

We currently support the `base64` source type for images, and the `image/jpeg`, `image/png`, `image/gif`, and `image/webp` media types.

See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for more input examples.

Note that if you want to include a [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use the top-level `system` parameter — there is no `"system"` role for input messages in the Messages API.

There is a limit of 100,000 messages in a single request.

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-messages-content)

messages.content

stringobject\[\]

required

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-messages-role)

messages.role

enum<string>

required

Available options:

`user`,

`assistant`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-model)

model

string

required

The model that will complete your prompt.

See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.

Required string length: `1 - 256`

Examples:

`"claude-sonnet-4-20250514"`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers)

mcp\_servers

object\[\]

MCP servers to be utilized in this request

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-name)

mcp\_servers.name

string

required

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-type)

mcp\_servers.type

enum<string>

required

Available options:

`url`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-url)

mcp\_servers.url

string

required

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-authorization-token)

mcp\_servers.authorization\_token

string \| null

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-tool-configuration)

mcp\_servers.tool\_configuration

object \| null

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-tool-configuration-allowed-tools)

mcp\_servers.tool\_configuration.allowed\_tools

string\[\] \| null

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-mcp-servers-tool-configuration-enabled)

mcp\_servers.tool\_configuration.enabled

boolean \| null

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-system)

system

stringobject\[\]

System prompt.

A system prompt is a way of providing context and instructions to Claude, such as specifying a particular goal or role. See our [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

Examples:

```json
[\
  {\
    "text": "Today's date is 2024-06-01.",\
    "type": "text"\
  }\
]

```

`"Today's date is 2023-01-01."`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-thinking)

thinking

object

Configuration for enabling Claude's extended thinking.

When enabled, responses include `thinking` content blocks showing Claude's thinking process before the final answer. Requires a minimum budget of 1,024 tokens and counts towards your `max_tokens` limit.

See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.

- Enabled
- Disabled

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-thinking-budget-tokens)

thinking.budget\_tokens

integer

required

Determines how many tokens Claude can use for its internal reasoning process. Larger budgets can enable more thorough analysis for complex problems, improving response quality.

Must be ≥1024 and less than `max_tokens`.

See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.

Required range: `x >= 1024`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-thinking-type)

thinking.type

enum<string>

required

Available options:

`enabled`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tool-choice)

tool\_choice

object

How the model should use the provided tools. The model can use a specific tool, any available tool, decide by itself, or not use tools at all.

- Auto
- Any
- Tool
- None

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tool-choice-type)

tool\_choice.type

enum<string>

required

Available options:

`auto`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tool-choice-disable-parallel-tool-use)

tool\_choice.disable\_parallel\_tool\_use

boolean

Whether to disable parallel tool use.

Defaults to `false`. If set to `true`, the model will output at most one tool use.

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools)

tools

object\[\]

Definitions of tools that the model may use.

If you include `tools` in your API request, the model may return `tool_use` content blocks that represent the model's use of those tools. You can then run those tools using the tool input generated by the model and then optionally return results back to the model using `tool_result` content blocks.

There are two types of tools: **client tools** and **server tools**. The behavior described below applies to client tools. For [server tools](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview#server-tools), see their individual documentation as each has its own behavior (e.g., the [web search tool](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool)).

Each tool definition includes:

- `name`: Name of the tool.
- `description`: Optional, but strongly-recommended description of the tool.
- `input_schema`: [JSON schema](https://json-schema.org/draft/2020-12) for the tool `input` shape that the model will produce in `tool_use` output content blocks.

For example, if you defined `tools` as:

```json
[\
  {\
    "name": "get_stock_price",\
    "description": "Get the current stock price for a given ticker symbol.",\
    "input_schema": {\
      "type": "object",\
      "properties": {\
        "ticker": {\
          "type": "string",\
          "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."\
        }\
      },\
      "required": ["ticker"]\
    }\
  }\
]

```

And then asked the model "What's the S&P 500 at today?", the model might produce `tool_use` content blocks in the response like this:

```json
[\
  {\
    "type": "tool_use",\
    "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",\
    "name": "get_stock_price",\
    "input": { "ticker": "^GSPC" }\
  }\
]

```

You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an input, and return the following back to the model in a subsequent `user` message:

```json
[\
  {\
    "type": "tool_result",\
    "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",\
    "content": "259.75 USD"\
  }\
]

```

Tools can be used for workflows that include running client-side tools and functions, or more generally whenever you want the model to produce a particular JSON structure of output.

See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

- Custom tool
- Bash tool (2024-10-22)
- Bash tool (2025-01-24)
- Code execution tool (2025-05-22)
- Computer use tool (2024-01-22)
- Computer use tool (2025-01-24)
- Text editor tool (2024-10-22)
- Text editor tool (2025-01-24)
- Text editor tool (2025-04-29)
- Web search tool (2025-03-05)

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-name)

tools.name

string

required

Name of the tool.

This is how the tool will be called by the model and in `tool_use` blocks.

Required string length: `1 - 128`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-input-schema)

tools.input\_schema

object

required

[JSON schema](https://json-schema.org/draft/2020-12) for this tool's input.

This defines the shape of the `input` that your tool accepts and that the model will produce.

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-input-schema-type)

tools.input\_schema.type

enum<string>

required

Available options:

`object`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-input-schema-properties)

tools.input\_schema.properties

object \| null

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-input-schema-required)

tools.input\_schema.required

string\[\] \| null

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-type)

tools.type

enum<string> \| null

Available options:

`custom`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-description)

tools.description

string

Description of what this tool does.

Tool descriptions should be as detailed as possible. The more information that the model has about what the tool is and how to use it, the better it will perform. You can use natural language descriptions to reinforce important aspects of the tool input JSON schema.

Examples:

`"Get the current weather in a given location"`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-cache-control)

tools.cache\_control

object \| null

Create a cache control breakpoint at this content block.

Showchild attributes

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-cache-control-type)

tools.cache\_control.type

enum<string>

required

Available options:

`ephemeral`

[​](https://docs.anthropic.com/en/api/messages-count-tokens#body-tools-cache-control-ttl)

tools.cache\_control.ttl

enum<string>

The time-to-live for the cache control breakpoint.

This may be one the following values:

- `5m`: 5 minutes
- `1h`: 1 hour

Defaults to `5m`.

Available options:

`5m`,

`1h`

Examples:

```json
{
  "description": "Get the current weather in a given location",
  "input_schema": {
    "properties": {
      "location": {
        "description": "The city and state, e.g. San Francisco, CA",
        "type": "string"
      },
      "unit": {
        "description": "Unit for the output - one of (celsius, fahrenheit)",
        "type": "string"
      }
    },
    "required": ["location"],
    "type": "object"
  },
  "name": "get_weather"
}

```

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/messages-count-tokens#response-input-tokens)

input\_tokens

integer

required

The total number of tokens across the provided list of messages, system prompt, and tools.

Examples:

`2095`

Was this page helpful?

YesNo

[Messages](https://docs.anthropic.com/en/api/messages) [List Models](https://docs.anthropic.com/en/api/models-list)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/messages/count_tokens \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-3-7-sonnet-20250219",
    "messages": [\
        {"role": "user", "content": "Hello, world"}\
    ]
}'
```

200

4XX

Copy

```
{
  "input_tokens": 2095
}
```