---
url: "https://openrouter.ai/docs/api-reference/create-a-coinbase-charge?explorer=true"
title: "Create a Coinbase charge | OpenRouter | Documentation"
---

Creates and hydrates a Coinbase Commerce charge for cryptocurrency payments

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Request

This endpoint expects an object.

amountdoubleRequired

USD amount to charge (must be between min and max purchase limits)

senderstringRequired

Ethereum address of the sender

chain\_idintegerRequired

Chain ID for the transaction

### Response

Returns the calldata to fulfill the transaction

dataobject

Show 5 properties

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

POSThttps://openrouter.ai/api/v1/credits/coinbase

Send Request

Enter your bearer tokenNot Authenticated

##### Body Parameters

- amountdoubleRequired

- senderstringRequired

- chain\_idintegerRequired


Use exampleClear form [View in API Reference](https://openrouter.ai/docs/api-reference/create-a-coinbase-charge)

RequestcURLTypeScriptPython

```code-block text-xs

$curl -X POST https://openrouter.ai/api/v1/credits/coinbase \>     -H "Authorization: Bearer " \>     -H "Content-Type: application/json" \>     -d '{>  "amount": 1.1,>  "sender": "sender",>  "chain_id": 1>}'
```

Response

Send Request