---
url: "https://docs.anthropic.com/en/api/deleting-message-batches"
title: "Delete a Message Batch - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Message Batches

Delete a Message Batch

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

DELETE

/

v1

/

messages

/

batches

/

{message\_batch\_id}

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl -X DELETE https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "type": "message_batch_deleted"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/deleting-message-batches#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

[​](https://docs.anthropic.com/en/api/deleting-message-batches#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/deleting-message-batches#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

#### Path Parameters

[​](https://docs.anthropic.com/en/api/deleting-message-batches#parameter-message-batch-id)

message\_batch\_id

string

required

ID of the Message Batch.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/deleting-message-batches#response-id)

id

string

required

ID of the Message Batch.

Examples:

`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`

[​](https://docs.anthropic.com/en/api/deleting-message-batches#response-type)

type

enum<string>

default:message\_batch\_deleted

required

Deleted object type.

For Message Batches, this is always `"message_batch_deleted"`.

Available options:

`message_batch_deleted`

Was this page helpful?

YesNo

[Cancel a Message Batch](https://docs.anthropic.com/en/api/canceling-message-batches) [Create a File](https://docs.anthropic.com/en/api/files-create)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl -X DELETE https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "type": "message_batch_deleted"
}
```