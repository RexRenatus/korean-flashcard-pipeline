---
url: "https://openrouter.ai/docs/api-reference/api-keys/get-current-api-key"
title: "Get current API key | OpenRouter | Documentation"
---

Get information on the API key associated with the current authentication session

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Response

Successfully retrieved API key information

dataobject

Show 6 properties

### Errors

401

Get Key Request Unauthorized Error

405

Get Key Request Method Not Allowed Error

500

Get Key Request Internal Server Error