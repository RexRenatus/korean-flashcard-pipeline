---
url: "https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member"
title: "Add Workspace Member - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Workspace Member Management

Add Workspace Member

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

POST

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
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
  --data '{
    "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
    "workspace_role": "workspace_user"
  }'
```

200

4XX

Copy

```
{
  "type": "workspace_member",
  "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "workspace_role": "workspace_user"
}
```

**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#parameter-workspace-id)

workspace\_id

string

required

ID of the Workspace.

#### Body

application/json

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#body-user-id)

user\_id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#body-workspace-role)

workspace\_role

enum<string>

required

Role of the new Workspace Member. Cannot be "workspace\_billing".

Available options:

`workspace_user`,

`workspace_developer`,

`workspace_admin`

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#response-type)

type

enum<string>

default:workspace\_member

required

Object type.

For Workspace Members, this is always `"workspace_member"`.

Available options:

`workspace_member`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#response-user-id)

user\_id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#response-workspace-id)

workspace\_id

string

required

ID of the Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/create-workspace-member#response-workspace-role)

workspace\_role

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

Was this page helpful?

YesNo

[List Workspace Members](https://docs.anthropic.com/en/api/admin-api/workspace_members/list-workspace-members) [Update Workspace Member](https://docs.anthropic.com/en/api/admin-api/workspace_members/update-workspace-member)

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
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
  --data '{
    "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
    "workspace_role": "workspace_user"
  }'
```

200

4XX

Copy

```
{
  "type": "workspace_member",
  "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "workspace_role": "workspace_user"
}
```