---
url: "https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces"
title: "List Workspaces - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Workspace Management

List Workspaces

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

organizations

/

workspaces

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/workspaces" \
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
      "id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",\
      "type": "workspace",\
      "name": "Workspace Name",\
      "created_at": "2024-10-30T23:58:27.427722Z",\
      "archived_at": "2024-11-01T23:59:27.427722Z",\
      "display_color": "#6C5BB9"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Query Parameters

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#parameter-include-archived)

include\_archived

boolean

default:false

Whether to include Workspaces that have been archived in the response

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#parameter-before-id)

before\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#parameter-after-id)

after\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#parameter-limit)

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

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data)

data

object\[\]

required

Showchild attributes

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data-id)

data.id

string

required

ID of the Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data-type)

data.type

enum<string>

default:workspace

required

Object type.

For Workspaces, this is always `"workspace"`.

Available options:

`workspace`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data-name)

data.name

string

required

Name of the Workspace.

Examples:

`"Workspace Name"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data-created-at)

data.created\_at

string

required

RFC 3339 datetime string indicating when the Workspace was created.

Examples:

`"2024-10-30T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data-archived-at)

data.archived\_at

string \| null

required

RFC 3339 datetime string indicating when the Workspace was archived, or null if the Workspace is not archived.

Examples:

`"2024-11-01T23:59:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-data-display-color)

data.display\_color

string

required

Hex color code representing the Workspace in the Anthropic Console.

Examples:

`"#6C5BB9"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-has-more)

has\_more

boolean

required

Indicates if there are more results in the requested page direction.

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-first-id)

first\_id

string \| null

required

First ID in the `data` list. Can be used as the `before_id` for the previous page.

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces#response-last-id)

last\_id

string \| null

required

Last ID in the `data` list. Can be used as the `after_id` for the next page.

Was this page helpful?

YesNo

[Get Workspace](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace) [Update Workspace](https://docs.anthropic.com/en/api/admin-api/workspaces/update-workspace)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/workspaces" \
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
      "id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",\
      "type": "workspace",\
      "name": "Workspace Name",\
      "created_at": "2024-10-30T23:58:27.427722Z",\
      "archived_at": "2024-11-01T23:59:27.427722Z",\
      "display_color": "#6C5BB9"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```