---
url: "https://openrouter.ai/docs/api-reference/list-available-models?explorer=true"
title: "List available models | OpenRouter | Documentation"
---

Returns a list of models available through the API.
Note: `supported_parameters` is a union of all parameters supported by all providers for this model.
There may not be a single provider which offers all of the listed parameters for a model.
More documentation available [here](https://openrouter.ai/docs/models).

### Query parameters

categorystringOptional

Filter models by category (e.g. programming). Sorted from most to least used.

use\_rssbooleanOptionalDefaults to `false`

Return RSS XML feed instead of JSON (BETA)

use\_rss\_chat\_linksbooleanOptionalDefaults to `false`

Use chat URLs instead of model page URLs for RSS items (only applies when use\_rss=true) (BETA)

### Response

List of available models

datalist of objects

Show 12 properties

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

GEThttps://openrouter.ai/api/v1/models

Send Request

##### Query Parameters

3 optional propertiescategory, use\_rss, use\_rss\_chat\_links

Use exampleClear form [View in API Reference](https://openrouter.ai/docs/api-reference/list-available-models)

RequestcURLTypeScriptPython

```code-block text-xs

$curl https://openrouter.ai/api/v1/models
```

Response

Send Request