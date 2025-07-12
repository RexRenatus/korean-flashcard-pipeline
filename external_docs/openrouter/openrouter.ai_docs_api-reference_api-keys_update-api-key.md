---
url: "https://openrouter.ai/docs/api-reference/api-keys/update-api-key"
title: "Update API key | OpenRouter | Documentation"
---

Updates an existing API key. Requires a Provisioning API key.

### Path parameters

hashstringRequired

The hash of the API key

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Request

This endpoint expects an object.

namestringOptional

New display name for the key

disabledbooleanOptional

Whether the key should be disabled

limitdoubleOptional

New credit limit for the key

include\_byok\_in\_limitbooleanOptional

Whether to include BYOK usage in the credit limit

### Response

Updated API key

dataobject

Show 7 properties