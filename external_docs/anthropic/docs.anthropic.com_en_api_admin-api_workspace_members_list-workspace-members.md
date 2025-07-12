---
url: "https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members"
title: "List Workspace Members - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Workspace Member Management

List Workspace Members

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

/

members

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/workspaces/wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ/members" \
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
      "type": "workspace_member",\
      "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",\
      "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",\
      "workspace_role": "workspace_user"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```

**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#parameter-workspace-id)

workspace\_id

string

required

ID of the Workspace.

#### Query Parameters

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#parameter-before-id)

before\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#parameter-after-id)

after\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#parameter-limit)

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

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-data)

data

object\[\]

required

Showchild attributes

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-data-type)

data.type

enum<string>

default:workspace\_member

required

Object type.

For Workspace Members, this is always `"workspace_member"`.

Available options:

`workspace_member`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-data-user-id)

data.user\_id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-data-workspace-id)

data.workspace\_id

string

required

ID of the Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-data-workspace-role)

data.workspace\_role

enum<string>

required

Role of the Workspace Member.

Available options:

`workspace_user`,

`workspace_developer`,

`workspace_admin`,

`workspace_billing`

Examples:

`"workspace_user"`

`"workspace_developer"`

`"workspace_admin"`

`"workspace_billing"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-has-more)

has\_more

boolean

required

Indicates if there are more results in the requested page direction.

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-first-id)

first\_id

string \| null

required

First ID in the `data` list. Can be used as the `before_id` for the previous page.

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members#response-last-id)

last\_id

string \| null

required

Last ID in the `data` list. Can be used as the `after_id` for the next page.

Was this page helpful?

YesNo

[Get Workspace Member](https://docs.anthropic.com/en/api/admin-api/workspace_members/get-workspace-member) [Add Workspace Member](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/workspaces/wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ/members" \
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
      "type": "workspace_member",\
      "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",\
      "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",\
      "workspace_role": "workspace_user"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```