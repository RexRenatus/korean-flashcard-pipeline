---
url: "https://docs.anthropic.com/en/api/admin-api/invites/delete-invite"
title: "Delete Invite - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Organization Invites

Delete Invite

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

DELETE

/

v1

/

organizations

/

invites

/

{invite\_id}

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl --request DELETE "https://api.anthropic.com/v1/organizations/invites/invite_015gWxCN9Hfg2QhZwTK7Mdeu" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "invite_015gWxCN9Hfg2QhZwTK7Mdeu",
  "type": "invite_deleted"
}
```

**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite#parameter-invite-id)

invite\_id

string

required

ID of the Invite.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite#response-id)

id

string

required

ID of the Invite.

Examples:

`"invite_015gWxCN9Hfg2QhZwTK7Mdeu"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite#response-type)

type

enum<string>

default:invite\_deleted

required

Deleted object type.

For Invites, this is always `"invite_deleted"`.

Available options:

`invite_deleted`

Was this page helpful?

YesNo

[Create Invite](https://docs.anthropic.com/en/api/admin-api/invites/create-invite) [Get Workspace](https://docs.anthropic.com/en/api/admin-api/workspaces/get-workspace)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl --request DELETE "https://api.anthropic.com/v1/organizations/invites/invite_015gWxCN9Hfg2QhZwTK7Mdeu" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "invite_015gWxCN9Hfg2QhZwTK7Mdeu",
  "type": "invite_deleted"
}
```