---
url: "https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member"
title: "Delete Workspace Member - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Workspace Member Management

Delete Workspace Member

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

DELETE

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

/

{user\_id}

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl --request DELETE "https://api.anthropic.com/v1/organizations/workspaces/wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ/members/user_01WCz1FkmYMm4gnmykNKUu3Q" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "type": "workspace_member_deleted"
}
```

**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#parameter-user-id)

user\_id

string

required

ID of the User.

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#parameter-workspace-id)

workspace\_id

string

required

ID of the Workspace.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#response-user-id)

user\_id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#response-workspace-id)

workspace\_id

string

required

ID of the Workspace.

Examples:

`"wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ"`

[​](https://docs.anthropic.com/en/api/admin-api/workspace_members/delete-workspace-member#response-type)

type

enum<string>

default:workspace\_member\_deleted

required

Deleted object type.

For Workspace Members, this is always `"workspace_member_deleted"`.

Available options:

`workspace_member_deleted`

Was this page helpful?

YesNo

[Update Workspace Member](https://docs.anthropic.com/en/api/admin-api/workspace_members/update-workspace-member) [Get API Key](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl --request DELETE "https://api.anthropic.com/v1/organizations/workspaces/wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ/members/user_01WCz1FkmYMm4gnmykNKUu3Q" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "user_id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "workspace_id": "wrkspc_01JwQvzr7rXLA5AGx3HKfFUJ",
  "type": "workspace_member_deleted"
}
```