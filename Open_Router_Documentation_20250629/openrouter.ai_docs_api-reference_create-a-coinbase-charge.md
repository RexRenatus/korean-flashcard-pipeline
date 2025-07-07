---
url: "https://openrouter.ai/docs/api-reference/create-a-coinbase-charge"
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