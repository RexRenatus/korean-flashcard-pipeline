---
url: "https://openrouter.ai/docs/api-reference/get-a-generation?explorer=true"
title: "Get a generation | OpenRouter | Documentation"
---

Returns metadata about a specific generation request

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Query parameters

idstringRequired

### Response

Returns the request metadata for this generation

dataobject

Show 27 properties

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

GEThttps://openrouter.ai/api/v1/generation?id=id

Send Request

Enter your bearer tokenNot Authenticated

##### Query Parameters

- idstringRequired


Use exampleClear form [View in API Reference](https://openrouter.ai/docs/api-reference/get-a-generation)

RequestcURLTypeScriptPython

```code-block text-xs

$curl -G https://openrouter.ai/api/v1/generation \>     -H "Authorization: Bearer " \>     -d id=id
```

Response

Send Request