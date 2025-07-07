---
url: "https://docs.anthropic.com/en/api/retrieving-message-batches"
title: "Retrieve a Message Batch - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Message Batches

Retrieve a Message Batch

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

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "archived_at": "2024-08-20T18:37:24.100435Z",
  "cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
  "created_at": "2024-08-20T18:37:24.100435Z",
  "ended_at": "2024-08-20T18:37:24.100435Z",
  "expires_at": "2024-08-20T18:37:24.100435Z",
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "processing_status": "in_progress",
  "request_counts": {
    "canceled": 10,
    "errored": 30,
    "expired": 10,
    "processing": 100,
    "succeeded": 50
  },
  "results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
  "type": "message_batch"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

#### Path Parameters

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#parameter-message-batch-id)

message\_batch\_id

string

required

ID of the Message Batch.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-archived-at)

archived\_at

string \| null

required

RFC 3339 datetime string representing the time at which the Message Batch was archived and its results became unavailable.

Examples:

`"2024-08-20T18:37:24.100435Z"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-cancel-initiated-at)

cancel\_initiated\_at

string \| null

required

RFC 3339 datetime string representing the time at which cancellation was initiated for the Message Batch. Specified only if cancellation was initiated.

Examples:

`"2024-08-20T18:37:24.100435Z"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-created-at)

created\_at

string

required

RFC 3339 datetime string representing the time at which the Message Batch was created.

Examples:

`"2024-08-20T18:37:24.100435Z"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-ended-at)

ended\_at

string \| null

required

RFC 3339 datetime string representing the time at which processing for the Message Batch ended. Specified only once processing ends.

Processing ends when every request in a Message Batch has either succeeded, errored, canceled, or expired.

Examples:

`"2024-08-20T18:37:24.100435Z"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-expires-at)

expires\_at

string

required

RFC 3339 datetime string representing the time at which the Message Batch will expire and end processing, which is 24 hours after creation.

Examples:

`"2024-08-20T18:37:24.100435Z"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-id)

id

string

required

Unique object identifier.

The format and length of IDs may change over time.

Examples:

`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-processing-status)

processing\_status

enum<string>

required

Processing status of the Message Batch.

Available options:

`in_progress`,

`canceling`,

`ended`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-request-counts)

request\_counts

object

required

Tallies requests within the Message Batch, categorized by their status.

Requests start as `processing` and move to one of the other statuses only once processing of the entire batch ends. The sum of all values always matches the total number of requests in the batch.

Showchild attributes

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-request-counts-canceled)

request\_counts.canceled

integer

default:0

required

Number of requests in the Message Batch that have been canceled.

This is zero until processing of the entire Message Batch has ended.

Examples:

`10`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-request-counts-errored)

request\_counts.errored

integer

default:0

required

Number of requests in the Message Batch that encountered an error.

This is zero until processing of the entire Message Batch has ended.

Examples:

`30`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-request-counts-expired)

request\_counts.expired

integer

default:0

required

Number of requests in the Message Batch that have expired.

This is zero until processing of the entire Message Batch has ended.

Examples:

`10`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-request-counts-processing)

request\_counts.processing

integer

default:0

required

Number of requests in the Message Batch that are processing.

Examples:

`100`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-request-counts-succeeded)

request\_counts.succeeded

integer

default:0

required

Number of requests in the Message Batch that have completed successfully.

This is zero until processing of the entire Message Batch has ended.

Examples:

`50`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-results-url)

results\_url

string \| null

required

URL to a `.jsonl` file containing the results of the Message Batch requests. Specified only once processing ends.

Results in the file are not guaranteed to be in the same order as requests. Use the `custom_id` field to match results to requests.

Examples:

`"https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results"`

[​](https://docs.anthropic.com/en/api/retrieving-message-batches#response-type)

type

enum<string>

default:message\_batch

required

Object type.

For Message Batches, this is always `"message_batch"`.

Available options:

`message_batch`

Was this page helpful?

YesNo

[Create a Message Batch](https://docs.anthropic.com/en/api/creating-message-batches) [Retrieve Message Batch Results](https://docs.anthropic.com/en/api/retrieving-message-batch-results)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "archived_at": "2024-08-20T18:37:24.100435Z",
  "cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
  "created_at": "2024-08-20T18:37:24.100435Z",
  "ended_at": "2024-08-20T18:37:24.100435Z",
  "expires_at": "2024-08-20T18:37:24.100435Z",
  "id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
  "processing_status": "in_progress",
  "request_counts": {
    "canceled": 10,
    "errored": 30,
    "expired": 10,
    "processing": 100,
    "succeeded": 50
  },
  "results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
  "type": "message_batch"
}
```