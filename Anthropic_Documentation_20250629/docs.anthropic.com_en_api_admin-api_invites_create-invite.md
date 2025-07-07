---
url: "https://docs.anthropic.com/en/api/admin-api/invites/create-invite"
title: "Create Invite - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Organization Invites

Create Invite

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

POST

/

v1

/

organizations

/

invites

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/invites" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
  --data '{
    "email": "user@emaildomain.com",
    "role": "user"
  }'
```

200

4XX

Copy

```
{
  "id": "invite_015gWxCN9Hfg2QhZwTK7Mdeu",
  "type": "invite",
  "email": "user@emaildomain.com",
  "role": "user",
  "invited_at": "2024-10-30T23:58:27.427722Z",
  "expires_at": "2024-11-20T23:58:27.427722Z",
  "status": "pending"
}
```

**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Body

application/json

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#body-email)

email

string

required

Email of the User.

Examples:

`"user@emaildomain.com"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#body-role)

role

enum<string>

required

Role for the invited User. Cannot be "admin".

Available options:

`user`,

`developer`,

`billing`

Examples:

`"user"`

`"developer"`

`"billing"`

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-id)

id

string

required

ID of the Invite.

Examples:

`"invite_015gWxCN9Hfg2QhZwTK7Mdeu"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-type)

type

enum<string>

default:invite

required

Object type.

For Invites, this is always `"invite"`.

Available options:

`invite`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-email)

email

string

required

Email of the User being invited.

Examples:

`"user@emaildomain.com"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-role)

role

enum<string>

required

Organization role of the User.

Available options:

`user`,

`developer`,

`billing`,

`admin`

Examples:

`"user"`

`"developer"`

`"billing"`

`"admin"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-invited-at)

invited\_at

string

required

RFC 3339 datetime string indicating when the Invite was created.

Examples:

`"2024-10-30T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-expires-at)

expires\_at

string

required

RFC 3339 datetime string indicating when the Invite expires.

Examples:

`"2024-11-20T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/invites/create-invite#response-status)

status

enum<string>

required

Status of the Invite.

Available options:

`accepted`,

`expired`,

`deleted`,

`pending`

Examples:

`"pending"`

Was this page helpful?

YesNo

[List Invites](https://docs.anthropic.com/en/api/admin-api/invites/list-invites) [Delete Invite](https://docs.anthropic.com/en/api/admin-api/invites/delete-invite)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/invites" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
  --data '{
    "email": "user@emaildomain.com",
    "role": "user"
  }'
```

200

4XX

Copy

```
{
  "id": "invite_015gWxCN9Hfg2QhZwTK7Mdeu",
  "type": "invite",
  "email": "user@emaildomain.com",
  "role": "user",
  "invited_at": "2024-10-30T23:58:27.427722Z",
  "expires_at": "2024-11-20T23:58:27.427722Z",
  "status": "pending"
}
```