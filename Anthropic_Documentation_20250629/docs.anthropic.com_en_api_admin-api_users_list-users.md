---
url: "https://docs.anthropic.com/en/api/admin-api/users/list-users"
title: "List Users - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Organization Member Management

List Users

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

GET

/

v1

/

organizations

/

users

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/users" \
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
      "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",\
      "type": "user",\
      "email": "user@emaildomain.com",\
      "name": "Jane Doe",\
      "role": "user",\
      "added_at": "2024-10-30T23:58:27.427722Z"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```

#### Headers

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#parameter-x-api-key)

x-api-key

string

required

Your unique Admin API key for authentication.

This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#parameter-anthropic-version)

anthropic-version

string

required

The version of the Anthropic API you want to use.

Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).

#### Query Parameters

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#parameter-before-id)

before\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#parameter-after-id)

after\_id

string

ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#parameter-limit)

limit

integer

default:20

Number of items to return per page.

Defaults to `20`. Ranges from `1` to `1000`.

Required range: `1 <= x <= 1000`

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#parameter-email)

email

string

Filter by user email.

#### Response

200

2004XX

application/json

Successful Response

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data)

data

object\[\]

required

Showchild attributes

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data-id)

data.id

string

required

ID of the User.

Examples:

`"user_01WCz1FkmYMm4gnmykNKUu3Q"`

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data-type)

data.type

enum<string>

default:user

required

Object type.

For Users, this is always `"user"`.

Available options:

`user`

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data-email)

data.email

string

required

Email of the User.

Examples:

`"user@emaildomain.com"`

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data-name)

data.name

string

required

Name of the User.

Examples:

`"Jane Doe"`

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data-role)

data.role

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

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-data-added-at)

data.added\_at

string

required

RFC 3339 datetime string indicating when the User joined the Organization.

Examples:

`"2024-10-30T23:58:27.427722Z"`

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-has-more)

has\_more

boolean

required

Indicates if there are more results in the requested page direction.

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-first-id)

first\_id

string \| null

required

First ID in the `data` list. Can be used as the `before_id` for the previous page.

[​](https://docs.anthropic.com/en/api/admin-api/users/list-users#response-last-id)

last\_id

string \| null

required

Last ID in the `data` list. Can be used as the `after_id` for the next page.

Was this page helpful?

YesNo

[Get User](https://docs.anthropic.com/en/api/admin-api/users/get-user) [Update User](https://docs.anthropic.com/en/api/admin-api/users/update-user)

cURL

Python

JavaScript

PHP

Go

Java

Copy

```
curl "https://api.anthropic.com/v1/organizations/users" \
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
      "id": "user_01WCz1FkmYMm4gnmykNKUu3Q",\
      "type": "user",\
      "email": "user@emaildomain.com",\
      "name": "Jane Doe",\
      "role": "user",\
      "added_at": "2024-10-30T23:58:27.427722Z"\
    }\
  ],
  "has_more": true,
  "first_id": "<string>",
  "last_id": "<string>"
}
```