---
url: "https://openrouter.ai/docs/api-reference/authentication/exchange-authorization-code-for-api-key?explorer=true"
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

## API Explorer

Browse, explore, and try out API endpoints without leaving the documentation.

- [POSTCompletion](https://openrouter.ai/docs/api-reference/completion?explorer=true)
- [POSTChat completion](https://openrouter.ai/docs/api-reference/chat-completion?explorer=true)
- [GETGet a generation](https://openrouter.ai/docs/api-reference/get-a-generation?explorer=true)
- [GETList available models](https://openrouter.ai/docs/api-reference/list-available-models?explorer=true)
- [GETList endpoints for a model](https://openrouter.ai/docs/api-reference/list-endpoints-for-a-model?explorer=true)
- [GETList available providers](https://openrouter.ai/docs/api-reference/list-available-providers?explorer=true)
- [GETGet credits](https://openrouter.ai/docs/api-reference/get-credits?explorer=true)
- [POSTCreate a Coinbase charge](https://openrouter.ai/docs/api-reference/create-a-coinbase-charge?explorer=true)
- Authentication

- [POSTExchange authorization code for API key](https://openrouter.ai/docs/api-reference/authentication/exchange-authorization-code-for-api-key?explorer=true)
- API Keys

- [GETGet current API key](https://openrouter.ai/docs/api-reference/api-keys/get-current-api-key?explorer=true)
- [GETList API keys](https://openrouter.ai/docs/api-reference/api-keys/list-api-keys?explorer=true)
- [POSTCreate API key](https://openrouter.ai/docs/api-reference/api-keys/create-api-key?explorer=true)
- [GETGet API key](https://openrouter.ai/docs/api-reference/api-keys/get-api-key?explorer=true)
- [DELDelete API key](https://openrouter.ai/docs/api-reference/api-keys/delete-api-key?explorer=true)
- [PATCHUpdate API key](https://openrouter.ai/docs/api-reference/api-keys/update-api-key?explorer=true)

[Built with](https://buildwithfern.com/?utm_campaign=buildWith&utm_medium=docs&utm_source=openrouter.ai)

POSThttps://openrouter.ai/api/v1/auth/keys

Send Request

##### Body Parameters

- codestringRequired


2 more optional propertiescode\_verifier, code\_challenge\_method

Use exampleClear form [View in API Reference](https://openrouter.ai/docs/api-reference/authentication/exchange-authorization-code-for-api-key)

RequestcURLTypeScriptPython

```code-block text-xs

$curl -X POST https://openrouter.ai/api/v1/auth/keys \>     -H "Content-Type: application/json" \>     -d '{>  "code": "code">}'
```

Response

Send Request