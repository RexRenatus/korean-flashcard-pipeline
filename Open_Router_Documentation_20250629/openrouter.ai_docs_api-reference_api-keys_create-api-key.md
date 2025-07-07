---
url: "https://openrouter.ai/docs/api-reference/api-keys/create-api-key"
title: "Create API key | OpenRouter | Documentation"
---

Creates a new API key. Requires a Provisioning API key.

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Request

This endpoint expects an object.

namestringRequired

Display name for the API key

limitdoubleOptional

Optional credit limit for the key

include\_byok\_in\_limitbooleanOptional

Whether to include BYOK usage in the credit limit

### Response

Created API key

dataobject

Show 7 properties

keystring or null

The API key string itself. Only returned when creating a new key.