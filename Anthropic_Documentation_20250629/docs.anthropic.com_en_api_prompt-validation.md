---
url: "https://docs.anthropic.com/en/api/prompt-validation"
title: "Prompt validation - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Text Completions (Legacy)

Prompt validation

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

**Legacy API**

The Text Completions API is a legacy API. Future models and features will require use of the [Messages API](https://docs.anthropic.com/en/api/messages), and we recommend [migrating](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages) as soon as possible.

The Anthropic API performs basic prompt sanitization and validation to help ensure that your prompts are well-formatted for Claude.

When creating Text Completions, if your prompt is not in the specified format, the API will first attempt to lightly sanitize it (for example, by removing trailing spaces). This exact behavior is subject to change, and we strongly recommend that you format your prompts with the [recommended](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) alternating `\n\nHuman:` and `\n\nAssistant:` turns.

Then, the API will validate your prompt under the following conditions:

- The first conversational turn in the prompt must be a `\n\nHuman:` turn
- The last conversational turn in the prompt be an `\n\nAssistant:` turn
- The prompt must be less than `100,000 - 1` tokens in length.

## [​](https://docs.anthropic.com/en/api/prompt-validation\#examples)  Examples

The following prompts will results in [API errors](https://docs.anthropic.com/en/api/errors):

Python

Copy

```Python
# Missing "\n\nHuman:" and "\n\nAssistant:" turns
prompt = "Hello, world"

# Missing "\n\nHuman:" turn
prompt = "Hello, world\n\nAssistant:"

# Missing "\n\nAssistant:" turn
prompt = "\n\nHuman: Hello, Claude"

# "\n\nHuman:" turn is not first
prompt = "\n\nAssistant: Hello, world\n\nHuman: Hello, Claude\n\nAssistant:"

# "\n\nAssistant:" turn is not last
prompt = "\n\nHuman: Hello, Claude\n\nAssistant: Hello, world\n\nHuman: How many toes do dogs have?"

# "\n\nAssistant:" only has one "\n"
prompt = "\n\nHuman: Hello, Claude \nAssistant:"

```

The following are currently accepted and automatically sanitized by the API, but you should not rely on this behavior, as it may change in the future:

Python

Copy

```Python
# No leading "\n\n" for "\n\nHuman:"
prompt = "Human: Hello, Claude\n\nAssistant:"

# Trailing space after "\n\nAssistant:"
prompt = "\n\nHuman: Hello, Claude:\n\nAssistant: "

```

Was this page helpful?

YesNo

[Streaming Text Completions](https://docs.anthropic.com/en/api/streaming) [Client SDKs](https://docs.anthropic.com/en/api/client-sdks)

On this page

- [Examples](https://docs.anthropic.com/en/api/prompt-validation#examples)