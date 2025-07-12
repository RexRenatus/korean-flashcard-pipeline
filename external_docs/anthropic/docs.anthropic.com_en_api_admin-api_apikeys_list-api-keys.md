---
url: "https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys"
title: "List API Keys - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

API Keys

List API Keys

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

organizations

/

api\_keys

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/api_keys" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "data": [\
    {\
      "id": "apikey_01Rj2N8SVvo6BePZj99NhmiT",\
      "type": "api_key",\
      "name": "Developer Key",\
      "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",\
      "created_at": "2024-10-30T23:58:27.427722Z",\
      "created_by": {\
        "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",\
        "type": "user"\
      },\
      "partial_key_hint": "sk-ant-api03-R2D...igAA",\
      "status": "active"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Query Parameters

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-before-id)

before\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-after-id)

after\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-limit)

limit

integer

default:20

Number of items to return per page.

Defaults to `20`. Ranges from `1` to `1000`.

Required range: `1 <= x <= 1000`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-status)

status

enum<string> \| null

Filter by API key status.

Available options:

`active`,

`inactive`,

`archived`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-workspace-id)

workspace\_id

string \| null

Filter by Workspace ID.

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#parameter-created-by-user-id)

created\_by\_user\_id

string \| null

Filter by the ID of the User who created the object.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data)

data

object\[\]

required

Showchild attributes

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-id)

data.id

string

required

ID of the API key.

Examples:

`"apikey_01Rj2N8SVvo6BePZj99NhmiT"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-type)

data.type

enum<string>

default:api\_key

required

Object type.

For API Keys, this is always `"api_key"`.

Available options:

`api_key`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-name)

data.name

string

required

Name of the API key.

Examples:

`"Developer Key"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-workspace-id)

data.workspace\_id

string \| null

required

ID of the Workspace associated with the API key, or null if the API key belongs to the default Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-created-at)

data.created\_at

string

required

RFC 3339 datetime string indicating when the API Key was created.

Examples:

`"2024-10-30T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-created-by)

data.created\_by

object

required

The ID and type of the actor that created the API key.

Showchild attributes

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-created-by-id)

data.created\_by.id

string

required

ID of the actor that created the object.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-created-by-type)

data.created\_by.type

string

required

Type of the actor that created the object.

Examples:

`"user"`

Examples:

```json
{
  "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "type": "user"
}

```

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-partial-key-hint)

data.partial\_key\_hint

string \| null

required

Partially redacted hint for the API key.

Examples:

`"sk-ant-api03-R2D...igAA"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-data-status)

data.status

enum<string>

required

Status of the API key.

Available options:

`active`,

`inactive`,

`archived`

Examples:

`"active"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-has-more)

has\_more

boolean

required

Indicates if there are more results in the requested page direction.

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-first-id)

first\_id

string \| null

required

First ID in the `data` list. Can be used as the `before_id` for the previous page.

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys#response-last-id)

last\_id

string \| null

required

Last ID in the `data` list. Can be used as the `after_id` for the next page.

Was this page helpful?

YesNo

[Get API Key](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key) [Update API Keys](https://docs.anthropic.com/en/api/admin-api/apikeys/update-api-key)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/api_keys" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "data": [\
    {\
      "id": "apikey_01Rj2N8SVvo6BePZj99NhmiT",\
      "type": "api_key",\
      "name": "Developer Key",\
      "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",\
      "created_at": "2024-10-30T23:58:27.427722Z",\
      "created_by": {\
        "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",\
        "type": "user"\
      },\
      "partial_key_hint": "sk-ant-api03-R2D...igAA",\
      "status": "active"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```