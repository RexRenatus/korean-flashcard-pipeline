---
url: "https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key"
title: "Get API Key - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

API Keys

Get API Key

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

organizations

/

api\_keys

/

{api\_key\_id}

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/api_keys/apikey_01Rj2N8SVvo6BePZj99NhmiT" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "apikey_01Rj2N8SVvo6BePZj99NhmiT",
  "type": "api_key",
  "name": "Developer Key",
  "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "created_at": "2024-10-30T23:58:27.427722Z",
  "created_by": {
    "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
    "type": "user"
  },
  "partial_key_hint": "sk-ant-api03-R2D...igAA",
  "status": "active"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#parameter-api-key-id)

api\_key\_id

string

required

ID of the API key.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-id)

id

string

required

ID of the API key.

Examples:

`"apikey_01Rj2N8SVvo6BePZj99NhmiT"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-type)

type

enum<string>

default:api\_key

required

Object type.

For API Keys, this is always `"api_key"`.

Available options:

`api_key`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-name)

name

string

required

Name of the API key.

Examples:

`"Developer Key"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-workspace-id)

workspace\_id

string \| null

required

ID of the Workspace associated with the API key, or null if the API key belongs to the default Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-created-at)

created\_at

string

required

RFC 3339 datetime string indicating when the API Key was created.

Examples:

`"2024-10-30T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-created-by)

created\_by

object

required

The ID and type of the actor that created the API key.

Showchild attributes

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-created-by-id)

created\_by.id

string

required

ID of the actor that created the object.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-created-by-type)

created\_by.type

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

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-partial-key-hint)

partial\_key\_hint

string \| null

required

Partially redacted hint for the API key.

Examples:

`"sk-ant-api03-R2D...igAA"`

[​](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key#response-status)

status

enum<string>

required

Status of the API key.

Available options:

`active`,

`inactive`,

`archived`

Examples:

`"active"`

Was this page helpful?

YesNo

[Delete Workspace Member](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member) [List API Keys](https://docs.anthropic.com/en/api/admin-api/apikeys/list-api-keys)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/api_keys/apikey_01Rj2N8SVvo6BePZj99NhmiT" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "apikey_01Rj2N8SVvo6BePZj99NhmiT",
  "type": "api_key",
  "name": "Developer Key",
  "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "created_at": "2024-10-30T23:58:27.427722Z",
  "created_by": {
    "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
    "type": "user"
  },
  "partial_key_hint": "sk-ant-api03-R2D...igAA",
  "status": "active"
}
```