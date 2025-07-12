---
url: "https://docs.anthropic.com/en/api/models-list"
title: "List Models - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Models

List Models

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

models

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/models \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "data": [\
    {\
      "created_at": "2025-02-19T00:00:00Z",\
      "display_name": "Claude Sonnet 4",\
      "id": "claude-sonnet-4-20250514",\
      "type": "model"\
    }\
  ],
  "first_id": "<string>",
  "has_more": true,
  "last_id": "<string>"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/models-list#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

[​](https://docs.anthropic.com/en/api/models-list#parameter-x-api-key)

x-api-key

string

required

Your unique API key for authentication.

This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.

[​](https://docs.anthropic.com/en/api/models-list#parameter-anthropic-beta)

anthropic-beta

string\[\]

Optional header to specify the beta version(s) you want to use.

To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.

#### Query Parameters

[​](https://docs.anthropic.com/en/api/models-list#parameter-before-id)

before\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.

[​](https://docs.anthropic.com/en/api/models-list#parameter-after-id)

after\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.

[​](https://docs.anthropic.com/en/api/models-list#parameter-limit)

limit

integer

default:20

Number of items to return per page.

Defaults to `20`. Ranges from `1` to `1000`.

Required range: `1 <= x <= 1000`

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/models-list#response-data)

data

object\[\]

required

Showchild attributes

[​](https://docs.anthropic.com/en/api/models-list#response-data-created-at)

data.created\_at

string

required

RFC 3339 datetime string representing the time at which the model was released. May be set to an epoch value if the release date is unknown.

Examples:

`"2025-02-19T00:00:00Z"`

[​](https://docs.anthropic.com/en/api/models-list#response-data-display-name)

data.display\_name

string

required

A human-readable name for the model.

Examples:

`"Claude Sonnet 4"`

[​](https://docs.anthropic.com/en/api/models-list#response-data-id)

data.id

string

required

Unique model identifier.

Examples:

`"claude-sonnet-4-20250514"`

[​](https://docs.anthropic.com/en/api/models-list#response-data-type)

data.type

enum<string>

default:model

required

Object type.

For Models, this is always `"model"`.

Available options:

`model`

[​](https://docs.anthropic.com/en/api/models-list#response-first-id)

first\_id

string \| null

required

First ID in the `data` list. Can be used as the `before_id` for the previous page.

[​](https://docs.anthropic.com/en/api/models-list#response-has-more)

has\_more

boolean

required

Indicates if there are more results in the requested page direction.

[​](https://docs.anthropic.com/en/api/models-list#response-last-id)

last\_id

string \| null

required

Last ID in the `data` list. Can be used as the `after_id` for the next page.

Was this page helpful?

YesNo

[Count Message tokens](https://docs.anthropic.com/en/api/messages-count-tokens) [Get a Model](https://docs.anthropic.com/en/api/models)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl https://api.anthropic.com/v1/models \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01"
```

200

4XX

Copy

```
{
  "data": [\
    {\
      "created_at": "2025-02-19T00:00:00Z",\
      "display_name": "Claude Sonnet 4",\
      "id": "claude-sonnet-4-20250514",\
      "type": "model"\
    }\
  ],
  "first_id": "<string>",
  "has_more": true,
  "last_id": "<string>"
}
```