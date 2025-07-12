---
url: "https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace"
title: "Get Workspace - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Workspace Management

Get Workspace

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

organizations

/

workspaces

/

{workspace\_id}

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/workspaces/wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "type": "workspace",
  "name": "Workspace Name",
  "created_at": "2024-10-30T23:58:27.427722Z",
  "archived_at": "2024-11-01T23:59:27.427722Z",
  "display_color": "#6C5BB9"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#parameter-workspace-id)

workspace\_id

string

required

ID of the Workspace.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#response-id)

id

string

required

ID of the Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#response-type)

type

enum<string>

default:workspace

required

Object type.

For Workspaces, this is always `"workspace"`.

Available options:

`workspace`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#response-name)

name

string

required

Name of the Workspace.

Examples:

`"Workspace Name"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#response-created-at)

created\_at

string

required

RFC 3339 datetime string indicating when the Workspace was created.

Examples:

`"2024-10-30T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#response-archived-at)

archived\_at

string \| null

required

RFC 3339 datetime string indicating when the Workspace was archived, or null if the Workspace is not archived.

Examples:

`"2024-11-01T23:59:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace#response-display-color)

display\_color

string

required

Hex color code representing the Workspace in the Anthropic Console.

Examples:

`"#6C5BB9"`

Was this page helpful?

YesNo

[Delete Invite](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite) [List Workspaces](https://docs.anthropic.com/en/api/admin-api/workspaces/list-workspaces)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/workspaces/wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "type": "workspace",
  "name": "Workspace Name",
  "created_at": "2024-10-30T23:58:27.427722Z",
  "archived_at": "2024-11-01T23:59:27.427722Z",
  "display_color": "#6C5BB9"
}
```