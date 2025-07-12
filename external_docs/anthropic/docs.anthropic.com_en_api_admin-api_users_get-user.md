---
url: "https://docs.anthropic.com/en/api/admin-api/users/get-user"
title: "Get User - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Organization Member Management

Get User

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

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
curl "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
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
  "type": "user",
  "email": "user@emaildomain.com",
  "name": "Jane Doe",
  "role": "user",
  "added_at": "2024-10-30T23:58:27.427722Z"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Path Parameters

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#parameter-user-id)

user\_id

string

required

ID of the User.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#response-id)

id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#response-type)

type

enum<string>

default:user

required

Object type.

For Users, this is always `"user"`.

Available options:

`user`

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#response-email)

email

string

required

Email of the User.

Examples:

`"user@emaildomain.com"`

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#response-name)

name

string

required

Name of the User.

Examples:

`"Jane Doe"`

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#response-role)

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

[​](https://docs.anthropic.com/en/api/admin-api/users/get-user#response-added-at)

added\_at

string

required

RFC 3339 datetime string indicating when the User joined the Organization.

Examples:

`"2024-10-30T23:58:27.427722Z"`

Was this page helpful?

YesNo

[Delete a File](https://docs.anthropic.com/en/api/files-delete) [List Users](https://docs.anthropic.com/en/api/admin-api/users/list-users)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
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
  "type": "user",
  "email": "user@emaildomain.com",
  "name": "Jane Doe",
  "role": "user",
  "added_at": "2024-10-30T23:58:27.427722Z"
}
```