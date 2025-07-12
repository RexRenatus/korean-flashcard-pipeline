---
url: "https://openrouter.ai/docs/api-reference/authentication/exchange-authorization-code-for-api-key"
title: "Exchange authorization code for API key | OpenRouter | Documentation"
---

Exchange an authorization code from the PKCE flow for a user-controlled API key

### Request

This endpoint expects an object.

codestringRequired

The authorization code received from the OAuth redirect

code\_verifierstringOptional

The code verifier if code\_challenge was used in the authorization request

code\_challenge\_methodenumOptional

The method used to generate the code challenge

Allowed values:S256plain

### Response

Successfully exchanged code for an API key

keystring

The API key to use for OpenRouter requests

user\_idstring or null

User ID associated with the API key

### Errors

400

Post Auth Keys Request Bad Request Error

403

Post Auth Keys Request Forbidden Error

405

Post Auth Keys Request Method Not Allowed Error