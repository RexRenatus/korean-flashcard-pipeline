---
url: "https://docs.anthropic.com/en/api/messages-batch-examples"
title: "Message Batches examples - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Examples

Message Batches examples

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

The Message Batches API supports the same set of features as the Messages API. While this page focuses on how to use the Message Batches API, see [Messages API examples](https://docs.anthropic.com/en/api/messages-examples) for examples of the Messages API featureset.

## [​](https://docs.anthropic.com/en/api/messages-batch-examples\#creating-a-message-batch)  Creating a Message Batch

Python

TypeScript

Shell

Copy

```Python
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

client = anthropic.Anthropic()

message_batch = client.messages.batches.create(
    requests=[\
        Request(\
            custom_id="my-first-request",\
            params=MessageCreateParamsNonStreaming(\
                model="claude-opus-4-20250514",\
                max_tokens=1024,\
                messages=[{\
                    "role": "user",\
                    "content": "Hello, world",\
                }]\
            )\
        ),\
        Request(\
            custom_id="my-second-request",\
            params=MessageCreateParamsNonStreaming(\
                model="claude-opus-4-20250514",\
                max_tokens=1024,\
                messages=[{\
                    "role": "user",\
                    "content": "Hi again, friend",\
                }]\
            )\
        )\
    ]
)
print(message_batch)

```

JSON

Copy

```JSON
{
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "type": "message_batch",
  "processing_status": "in_progress",
  "request_counts": {
    "processing": 2,
    "succeeded": 0,
    "errored": 0,
    "canceled": 0,
    "expired": 0
  },
  "ended_at": null,
  "created_at": "2024-09-24T18:37:24.100435Z",
  "expires_at": "2024-09-25T18:37:24.100435Z",
  "cancel_initiated_at": null,
  "results_url": null
}

```

## [​](https://docs.anthropic.com/en/api/messages-batch-examples\#polling-for-message-batch-completion)  Polling for Message Batch completion

To poll a Message Batch, you’ll need its `id`, which is provided in the response when [creating](https://docs.anthropic.com/en/api/messages-batch-examples#creating-a-message-batch) request or by [listing](https://docs.anthropic.com/en/api/messages-batch-examples#listing-all-message-batches-in-a-workspace) batches. Example `id`: `msgbatch_013Zva2CMHLNnXjNJJKqJ2EF`.

Python

TypeScript

Shell

Copy

```Python
import anthropic

client = anthropic.Anthropic()

message_batch = None
while True:
    message_batch = client.messages.batches.retrieve(
        MESSAGE_BATCH_ID
    )
    if message_batch.processing_status == "ended":
        break

    print(f"Batch {MESSAGE_BATCH_ID} is still processing...")
    time.sleep(60)
print(message_batch)

```

## [​](https://docs.anthropic.com/en/api/messages-batch-examples\#listing-all-message-batches-in-a-workspace)  Listing all Message Batches in a Workspace

Python

TypeScript

Shell

Copy

```Python
import anthropic

client = anthropic.Anthropic()

# Automatically fetches more pages as needed.
for message_batch in client.messages.batches.list(
    limit=20
):
    print(message_batch)

```

Output

Copy

```Markup
{
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "type": "message_batch",
  ...
}
{
  "id": "msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d",
  "type": "message_batch",
  ...
}

```

## [​](https://docs.anthropic.com/en/api/messages-batch-examples\#retrieving-message-batch-results)  Retrieving Message Batch Results

Once your Message Batch status is `ended`, you will be able to view the `results_url` of the batch and retrieve results in the form of a `.jsonl` file.

Python

TypeScript

Shell

Copy

```Python
import anthropic

client = anthropic.Anthropic()

# Stream results file in memory-efficient chunks, processing one at a time
for result in client.messages.batches.results(
    MESSAGE_BATCH_ID,
):
    print(result)

```

Output

Copy

```Markup
{
  "id": "my-second-request",
  "result": {
    "type": "succeeded",
    "message": {
      "id": "msg_018gCsTGsXkYJVqYPxTgDHBU",
      "type": "message",
      ...
    }
  }
}
{
  "custom_id": "my-first-request",
  "result": {
    "type": "succeeded",
    "message": {
      "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
      "type": "message",
      ...
    }
  }
}

```

## [​](https://docs.anthropic.com/en/api/messages-batch-examples\#canceling-a-message-batch)  Canceling a Message Batch

Immediately after cancellation, a batch’s `processing_status` will be `canceling`. You can use the same [polling for batch completion](https://docs.anthropic.com/en/api/messages-batch-examples#polling-for-message-batch-completion) technique to poll for when cancellation is finalized as canceled batches also end up `ended` and may contain results.

Python

TypeScript

Shell

Copy

```Python
import anthropic

client = anthropic.Anthropic()

message_batch = client.messages.batches.cancel(
    MESSAGE_BATCH_ID,
)
print(message_batch)

```

JSON

Copy

```JSON
{
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "type": "message_batch",
  "processing_status": "canceling",
  "request_counts": {
    "processing": 2,
    "succeeded": 0,
    "errored": 0,
    "canceled": 0,
    "expired": 0
  },
  "ended_at": null,
  "created_at": "2024-09-24T18:37:24.100435Z",
  "expires_at": "2024-09-25T18:37:24.100435Z",
  "cancel_initiated_at": "2024-09-24T18:39:03.114875Z",
  "results_url": null
}

```

Was this page helpful?

YesNo

[Messages examples](https://docs.anthropic.com/en/api/messages-examples) [Amazon Bedrock API](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock)

On this page

- [Creating a Message Batch](https://docs.anthropic.com/en/api/messages-batch-examples#creating-a-message-batch)
- [Polling for Message Batch completion](https://docs.anthropic.com/en/api/messages-batch-examples#polling-for-message-batch-completion)
- [Listing all Message Batches in a Workspace](https://docs.anthropic.com/en/api/messages-batch-examples#listing-all-message-batches-in-a-workspace)
- [Retrieving Message Batch Results](https://docs.anthropic.com/en/api/messages-batch-examples#retrieving-message-batch-results)
- [Canceling a Message Batch](https://docs.anthropic.com/en/api/messages-batch-examples#canceling-a-message-batch)