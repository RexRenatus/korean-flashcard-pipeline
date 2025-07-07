---
url: "https://openrouter.ai/docs/api-reference/api-keys/list-api-keys"
title: "List API keys | OpenRouter | Documentation"
---

Returns a list of all API keys associated with the account. Requires a Provisioning API key.

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Query parameters

offsetdoubleOptional

Offset for the API keys

include\_disabledbooleanOptional

Whether to include disabled API keys in the response

### Response

List of API keys

datalist of objects

Show 7 properties