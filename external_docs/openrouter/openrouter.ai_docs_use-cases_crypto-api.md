---
url: "https://openrouter.ai/docs/use-cases/crypto-api"
title: "Crypto API | Purchase Credits with Cryptocurrency | OpenRouter | Documentation"
---

You can purchase credits using cryptocurrency through our Coinbase integration. This can either happen through the UI, on your [credits page](https://openrouter.ai/settings/credits), or through our API as described below. While other forms of payment are possible, this guide specifically shows how to pay with the chain’s native token.

Headless credit purchases involve three steps:

1. Getting the calldata for a new credit purchase
2. Sending a transaction on-chain using that data
3. Detecting low account balance, and purchasing more

## Getting Credit Purchase Calldata

Make a POST request to `/api/v1/credits/coinbase` to create a new charge. You’ll include the amount of credits you want to purchase (in USD, up to $100000), the address you’ll be sending the transaction from, and the EVM chain ID of the network you’ll be sending on.

Currently, we only support the following chains (mainnet only):

- Ethereum (1)
- Polygon (137)
- Base (8453) **_recommended_**

```code-block text-sm

1const response = await fetch('https://openrouter.ai/api/v1/credits/coinbase', {2  method: 'POST',3  headers: {4    Authorization: 'Bearer <OPENROUTER_API_KEY>',5    'Content-Type': 'application/json',6  },7  body: JSON.stringify({8    amount: 10, // Target credit amount in USD9    sender: '0x9a85CB3bfd494Ea3a8C9E50aA6a3c1a7E8BACE11',10    chain_id: 8453,11  }),12});13const responseJSON = await response.json();
```

The response includes the charge details and transaction data needed to execute the on-chain payment:

```code-block text-sm

1{2  "data": {3    "id": "...",4    "created_at": "2024-01-01T00:00:00Z",5    "expires_at": "2024-01-01T01:00:00Z",6    "web3_data": {7      "transfer_intent": {8        "metadata": {9          "chain_id": 8453,10          "contract_address": "0x03059433bcdb6144624cc2443159d9445c32b7a8",11          "sender": "0x9a85CB3bfd494Ea3a8C9E50aA6a3c1a7E8BACE11"12        },13        "call_data": {14          "recipient_amount": "...",15          "deadline": "...",16          "recipient": "...",17          "recipient_currency": "...",18          "refund_destination": "...",19          "fee_amount": "...",20          "id": "...",21          "operator": "...",22          "signature": "...",23          "prefix": "..."24        }25      }26    }27  }28}

```

## Sending the Transaction

You can use [viem](https://viem.sh/) (or another similar evm client) to execute the transaction on-chain.

In this example, we’ll be fulfilling the charge using the [swapAndTransferUniswapV3Native()](https://github.com/coinbase/commerce-onchain-payment-protocol/blob/d891289bd1f41bb95f749af537f2b6a36b17f889/contracts/interfaces/ITransfers.sol#L168-L171) function. Other methods of swapping are also available, and you can learn more by checking out Coinbase’s [onchain payment protocol here](https://github.com/coinbase/commerce-onchain-payment-protocol/tree/master). Note, if you are trying to pay in a less common ERC-20, there is added complexity in needing to make sure that there is sufficient liquidity in the pool to swap the tokens.

```code-block text-sm

1import { createPublicClient, createWalletClient, http, parseEther } from 'viem';2import { privateKeyToAccount } from 'viem/accounts';3import { base } from 'viem/chains';45// The ABI for Coinbase's onchain payment protocol6const abi = [7  {8    inputs: [9      {10        internalType: 'contract IUniversalRouter',11        name: '_uniswap',12        type: 'address',13      },14      { internalType: 'contract Permit2', name: '_permit2', type: 'address' },15      { internalType: 'address', name: '_initialOperator', type: 'address' },16      {17        internalType: 'address',18        name: '_initialFeeDestination',19        type: 'address',20      },21      {22        internalType: 'contract IWrappedNativeCurrency',23        name: '_wrappedNativeCurrency',24        type: 'address',25      },26    ],27    stateMutability: 'nonpayable',28    type: 'constructor',29  },30  { inputs: [], name: 'AlreadyProcessed', type: 'error' },31  { inputs: [], name: 'ExpiredIntent', type: 'error' },32  {33    inputs: [34      { internalType: 'address', name: 'attemptedCurrency', type: 'address' },35    ],36    name: 'IncorrectCurrency',37    type: 'error',38  },39  { inputs: [], name: 'InexactTransfer', type: 'error' },40  {41    inputs: [{ internalType: 'uint256', name: 'difference', type: 'uint256' }],42    name: 'InsufficientAllowance',43    type: 'error',44  },45  {46    inputs: [{ internalType: 'uint256', name: 'difference', type: 'uint256' }],47    name: 'InsufficientBalance',48    type: 'error',49  },50  {51    inputs: [{ internalType: 'int256', name: 'difference', type: 'int256' }],52    name: 'InvalidNativeAmount',53    type: 'error',54  },55  { inputs: [], name: 'InvalidSignature', type: 'error' },56  { inputs: [], name: 'InvalidTransferDetails', type: 'error' },57  {58    inputs: [59      { internalType: 'address', name: 'recipient', type: 'address' },60      { internalType: 'uint256', name: 'amount', type: 'uint256' },61      { internalType: 'bool', name: 'isRefund', type: 'bool' },62      { internalType: 'bytes', name: 'data', type: 'bytes' },63    ],64    name: 'NativeTransferFailed',65    type: 'error',66  },\
\
```\
\
Once the transaction succeeds on chain, we’ll add credits to your account. You can track the transaction status using the returned transaction hash.\
\
Credit purchases lower than $500 will be immediately credited once the transaction is on chain. Above $500, there is a ~15 minute confirmation delay, ensuring the chain does not re-org your purchase.\
\
## Detecting Low Balance\
\
While it is possible to simply run down the balance until your app starts receiving 402 error codes for insufficient credits, this gap in service while topping up might not be desirable.\
\
To avoid this, you can periodically call the `GET /api/v1/credits` endpoint to check your available credits.\
\
```code-block text-sm\
\
1const response = await fetch('https://openrouter.ai/api/v1/credits', {2  method: 'GET',3  headers: { Authorization: 'Bearer <OPENROUTER_API_KEY>' },4});5const { data } = await response.json();\
```\
\
The response includes your total credits purchased and usage, where your current balance is the difference between the two:\
\
```code-block text-sm\
\
1{2  "data": {3    "total_credits": 50.0,4    "total_usage": 42.05  }6}\
```\
\
Note that these values are cached, and may be up to 60 seconds stale.