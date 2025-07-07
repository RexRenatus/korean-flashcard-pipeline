---
url: "https://openrouter.ai/docs/api-reference/chat-completion?explorer=true"
title: "Chat completion | OpenRouter | Documentation"
---

Send a chat completion request to a selected model. The request must contain a "messages" array. All advanced options from the base request are also supported.

### Headers

AuthorizationstringRequired

Bearer authentication of the form Bearer <token>, where token is your auth token.

### Request

This endpoint expects an object.

modelstringRequired

The model ID to use. If unspecified, the user's default is used.

messageslist of objectsRequired

Show 2 properties

modelslist of stringsOptional

Alternate list of models for routing overrides.

providerobjectOptional

Preferences for provider routing.

Show 1 properties

reasoningobjectOptional

Configuration for model reasoning/thinking tokens

Show 3 properties

usageobjectOptional

Whether to include usage information in the response

Show 1 properties

transformslist of stringsOptional

List of prompt transforms (OpenRouter-only).

streambooleanOptionalDefaults to `false`

Enable streaming of results.

max\_tokensintegerOptional

Maximum number of tokens (range: \[1, context\_length)).\
\
temperaturedoubleOptional\
\
Sampling temperature (range: \[0, 2\]).\
\
seedintegerOptional\
\
Seed for deterministic outputs.\
\
top\_pdoubleOptional\
\
Top-p sampling value (range: (0, 1\]).

top\_kintegerOptional

Top-k sampling value (range: \[1, Infinity)).\
\
frequency\_penaltydoubleOptional\
\
Frequency penalty (range: \[-2, 2\]).\
\
presence\_penaltydoubleOptional\
\
Presence penalty (range: \[-2, 2\]).\
\
repetition\_penaltydoubleOptional\
\
Repetition penalty (range: (0, 2\]).

logit\_biasmap from strings to doublesOptional

Mapping of token IDs to bias values.

top\_logprobsintegerOptional

Number of top log probabilities to return.

min\_pdoubleOptional

Minimum probability threshold (range: \[0, 1\]).

top\_adoubleOptional

Alternate top sampling parameter (range: \[0, 1\]).

userstringOptional

A stable identifier for your end-users. Used to help detect and prevent abuse.

### Response

Successful completion

idstring or null

choiceslist of objects or null

Show 1 properties

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

POSThttps://openrouter.ai/api/v1/chat/completions

Send Request

Enter your bearer tokenNot Authenticated

##### Body Parameters

- modelstringRequired

- messageslist of objectsRequired(1 item)





- 1



- roleenumRequired



user

- contentstringRequired


- Add new item

19 more optional propertiesmodels, provider, reasoning, usage, transforms, stream, max\_tokens, temperature, seed, top\_p, top\_k, frequency\_penalty, presence\_penalty, repetition\_penalty, logit\_bias, top\_logprobs, min\_p, top\_a, user

Use exampleClear form [View in API Reference](https://openrouter.ai/docs/api-reference/chat-completion)

RequestcURLTypeScriptPython

```code-block text-xs

$curl -X POST https://openrouter.ai/api/v1/chat/completions \>     -H "Authorization: Bearer " \>     -H "Content-Type: application/json" \>     -d '{>  "model": "openai/gpt-3.5-turbo",>  "messages": [>    {>      "role": "user",>      "content": "What is the meaning of life?">    }>  ]>}'
```

Response

Send Request