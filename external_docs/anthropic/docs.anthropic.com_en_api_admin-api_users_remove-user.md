---
url: "https://docs.anthropic.com/en/api/admin-api/users/remove-user"
title: "Remove User - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Organization Member Management

Remove User

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

DELETE

/

v1

/

organizations

/

users

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
curl --request DELETE "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "type": "user_deleted"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/users/remove-user#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/users/remove-user#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/users/remove-user#parameter-user-id)

user\_id

string

required

ID of the User.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/users/remove-user#response-id)

id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/users/remove-user#response-type)

type

enum<string>

default:user\_deleted

required

Deleted object type.

For Users, this is always `"user_deleted"`.

Available options:

`user_deleted`

Was this page helpful?

YesNo

[Update User](https://docs.anthropic.com/en/api/admin-api/users/update-user) [Get Invite](https://docs.anthropic.com/en/api/admin-api/invites/get-invite)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl --request DELETE "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --header "x-api-key: $ANTHROPIC_ADMIN_KEY"
```

200

4XX

Copy

```
{
  "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
  "type": "user_deleted"
}
```