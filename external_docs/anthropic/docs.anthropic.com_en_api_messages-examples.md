---
url: "https://docs.anthropic.com/en/api/messages-examples"
title: "Messages examples - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Examples

Messages examples

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

See the [API reference](https://docs.anthropic.com/en/api/messages) for full documentation on available parameters.

## [​](https://docs.anthropic.com/en/api/messages-examples\#basic-request-and-response)  Basic request and response

Shell

Python

TypeScript

Copy

```bash
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-opus-4-20250514",
    "max_tokens": 1024,
    "messages": [\
        {"role": "user", "content": "Hello, Claude"}\
    ]
}'

```

JSON

Copy

```JSON
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [\
    {\
      "type": "text",\
      "text": "Hello!"\
    }\
  ],
  "model": "claude-opus-4-20250514",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 12,
    "output_tokens": 6
  }
}

```

## [​](https://docs.anthropic.com/en/api/messages-examples\#multiple-conversational-turns)  Multiple conversational turns

The Messages API is stateless, which means that you always send the full conversational history to the API. You can use this pattern to build up a conversation over time. Earlier conversational turns don’t necessarily need to actually originate from Claude — you can use synthetic `assistant` messages.

Shell

Python

TypeScript

Copy

```bash
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-opus-4-20250514",
    "max_tokens": 1024,
    "messages": [\
        {"role": "user", "content": "Hello, Claude"},\
        {"role": "assistant", "content": "Hello!"},\
        {"role": "user", "content": "Can you describe LLMs to me?"}\
\
    ]
}'

```

JSON

Copy

```JSON
{
    "id": "msg_018gCsTGsXkYJVqYPxTgDHBU",
    "type": "message",
    "role": "assistant",
    "content": [\
        {\
            "type": "text",\
            "text": "Sure, I'd be happy to provide..."\
        }\
    ],
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "usage": {
      "input_tokens": 30,
      "output_tokens": 309
    }
}

```

## [​](https://docs.anthropic.com/en/api/messages-examples\#putting-words-in-claude%E2%80%99s-mouth)  Putting words in Claude’s mouth

You can pre-fill part of Claude’s response in the last position of the input messages list. This can be used to shape Claude’s response. The example below uses `"max_tokens": 1` to get a single multiple choice answer from Claude.

Shell

Python

TypeScript

Copy

```bash
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-opus-4-20250514",
    "max_tokens": 1,
    "messages": [\
        {"role": "user", "content": "What is latin for Ant? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"},\
        {"role": "assistant", "content": "The answer is ("}\
    ]
}'

```

JSON

Copy

```JSON
{
  "id": "msg_01Q8Faay6S7QPTvEUUQARt7h",
  "type": "message",
  "role": "assistant",
  "content": [\
    {\
      "type": "text",\
      "text": "C"\
    }\
  ],
  "model": "claude-opus-4-20250514",
  "stop_reason": "max_tokens",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 42,
    "output_tokens": 1
  }
}

```

## [​](https://docs.anthropic.com/en/api/messages-examples\#vision)  Vision

Claude can read both text and images in requests. We support both `base64` and `url` source types for images, and the `image/jpeg`, `image/png`, `image/gif`, and `image/webp` media types. See our [vision guide](https://docs.anthropic.com/en/docs/build-with-claude/vision) for more details.

Shell

Python

TypeScript

Copy

```bash
#!/bin/sh

# Option 1: Base64-encoded image
IMAGE_URL="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
IMAGE_MEDIA_TYPE="image/jpeg"
IMAGE_BASE64=$(curl "$IMAGE_URL" | base64)

curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-opus-4-20250514",
    "max_tokens": 1024,
    "messages": [\
        {"role": "user", "content": [\
            {"type": "image", "source": {\
                "type": "base64",\
                "media_type": "'$IMAGE_MEDIA_TYPE'",\
                "data": "'$IMAGE_BASE64'"\
            }},\
            {"type": "text", "text": "What is in the above image?"}\
        ]}\
    ]
}'

# Option 2: URL-referenced image
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-opus-4-20250514",
    "max_tokens": 1024,
    "messages": [\
        {"role": "user", "content": [\
            {"type": "image", "source": {\
                "type": "url",\
                "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"\
            }},\
            {"type": "text", "text": "What is in the above image?"}\
        ]}\
    ]
}'

```

JSON

Copy

```JSON
{
  "id": "msg_01EcyWo6m4hyW8KHs2y2pei5",
  "type": "message",
  "role": "assistant",
  "content": [\
    {\
      "type": "text",\
      "text": "This image shows an ant, specifically a close-up view of an ant. The ant is shown in detail, with its distinct head, antennae, and legs clearly visible. The image is focused on capturing the intricate details and features of the ant, likely taken with a macro lens to get an extreme close-up perspective."\
    }\
  ],
  "model": "claude-opus-4-20250514",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 1551,
    "output_tokens": 71
  }
}

```

## [​](https://docs.anthropic.com/en/api/messages-examples\#tool-use%2C-json-mode%2C-and-computer-use)  Tool use, JSON mode, and computer use

See our [guide](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) for examples for how to use tools with the Messages API.
See our [computer use guide](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/computer-use-tool) for examples of how to control desktop computer environments with the Messages API.

Was this page helpful?

YesNo

[OpenAI SDK compatibility](https://docs.anthropic.com/en/api/openai-sdk) [Message Batches examples](https://docs.anthropic.com/en/api/messages-batch-examples)

On this page

- [Basic request and response](https://docs.anthropic.com/en/api/messages-examples#basic-request-and-response)
- [Multiple conversational turns](https://docs.anthropic.com/en/api/messages-examples#multiple-conversational-turns)
- [Putting words in Claude’s mouth](https://docs.anthropic.com/en/api/messages-examples#putting-words-in-claude%E2%80%99s-mouth)
- [Vision](https://docs.anthropic.com/en/api/messages-examples#vision)
- [Tool use, JSON mode, and computer use](https://docs.anthropic.com/en/api/messages-examples#tool-use%2C-json-mode%2C-and-computer-use)