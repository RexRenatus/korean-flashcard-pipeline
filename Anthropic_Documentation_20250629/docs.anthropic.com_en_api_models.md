---
url: "https://docs.anthropic.com/en/api/models"
title: "Get a Model - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Models

Get a Model

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

models

/

{model\_id}

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/models/claude-sonnet-4-20250514 \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "created_at": "2025-02-19T00:00:00Z",
  "display_name": "Claude Sonnet 4",
  "id": "claude-sonnet-4-20250514",
  "type": "model"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/models#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/models#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

[​](https://docs.anthropic.com/en/api/models#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

#### Path Parameters

[​](https://docs.anthropic.com/en/api/models#parameter-model-id)

model\_id

string

required

Model identifier or alias.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/models#response-created-at)

created\_at

string

required

RFC 3339 datetime string representing the time at which the model was released. May be set to an epoch value if the release date is unknown.

Examples:

`"2025-02-19T00:00:00Z"`

[​](https://docs.anthropic.com/en/api/models#response-display-name)

display\_name

string

required

A human-readable name for the model.

Examples:

`"Claude Sonnet 4"`

[​](https://docs.anthropic.com/en/api/models#response-id)

id

string

required

Unique model identifier.

Examples:

`"claude-sonnet-4-20250514"`

[​](https://docs.anthropic.com/en/api/models#response-type)

type

enum<string>

default:model

required

Object type.

For Models, this is always `"model"`.

Available options:

`model`

Was this page helpful?

YesNo

[List Models](https://docs.anthropic.com/en/api/models-list) [Create a Message Batch](https://docs.anthropic.com/en/api/creating-message-batches)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/models/claude-sonnet-4-20250514 \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "created_at": "2025-02-19T00:00:00Z",
  "display_name": "Claude Sonnet 4",
  "id": "claude-sonnet-4-20250514",
  "type": "model"
}
```