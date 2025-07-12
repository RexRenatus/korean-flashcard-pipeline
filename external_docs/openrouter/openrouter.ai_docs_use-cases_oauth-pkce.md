---
url: "https://openrouter.ai/docs/use-cases/oauth-pkce"
title: "OAuth PKCE | Secure Authentication for OpenRouter | OpenRouter | Documentation"
---

Users can connect to OpenRouter in one click using [Proof Key for Code Exchange (PKCE)](https://oauth.net/2/pkce/).

Here’s a step-by-step guide:

## PKCE Guide

### Step 1: Send your user to OpenRouter

To start the PKCE flow, send your user to OpenRouter’s `/auth` URL with a `callback_url` parameter pointing back to your site:

With S256 Code Challenge (Recommended)With Plain Code ChallengeWithout Code Challenge

```code-block text-sm

https://openrouter.ai/auth?callback_url=<YOUR_SITE_URL>&code_challenge=<CODE_CHALLENGE>&code_challenge_method=S256
```

The `code_challenge` parameter is optional but recommended.

Your user will be prompted to log in to OpenRouter and authorize your app. After authorization, they will be redirected back to your site with a `code` parameter in the URL:

![Alt text](https://prod.ferndocs.com/_next/image?url=https%3A%2F%2Ffiles.buildwithfern.com%2Fopenrouter.docs.buildwithfern.com%2Fdocs%2F2025-06-28T20%3A47%3A18.701Z%2Fcontent%2Fpages%2Fuse-cases%2Fauth-request.png&w=3840&q=75)

##### Use SHA-256 for Maximum Security

For maximum security, set `code_challenge_method` to `S256`, and set `code_challenge` to the base64 encoding of the sha256 hash of `code_verifier`.

For more info, [visit Auth0’s docs](https://auth0.com/docs/get-started/authentication-and-authorization-flow/call-your-api-using-the-authorization-code-flow-with-pkce#parameters).

#### How to Generate a Code Challenge

The following example leverages the Web Crypto API and the Buffer API to generate a code challenge for the S256 method. You will need a bundler to use the Buffer API in the web browser:

Generate Code Challenge

```code-block text-sm

1import { Buffer } from 'buffer';23async function createSHA256CodeChallenge(input: string) {4  const encoder = new TextEncoder();5  const data = encoder.encode(input);6  const hash = await crypto.subtle.digest('SHA-256', data);7  return Buffer.from(hash).toString('base64url');8}910const codeVerifier = 'your-random-string';11const generatedCodeChallenge = await createSHA256CodeChallenge(codeVerifier);
```

#### Localhost Apps

If your app is a local-first app or otherwise doesn’t have a public URL, it is recommended to test with `http://localhost:3000` as the callback and referrer URLs.

When moving to production, replace the localhost/private referrer URL with a public GitHub repo or a link to your project website.

### Step 2: Exchange the code for a user-controlled API key

After the user logs in with OpenRouter, they are redirected back to your site with a `code` parameter in the URL:

![Alt text](https://prod.ferndocs.com/_next/image?url=https%3A%2F%2Ffiles.buildwithfern.com%2Fopenrouter.docs.buildwithfern.com%2Fdocs%2F2025-06-28T20%3A47%3A18.701Z%2Fcontent%2Fpages%2Fuse-cases%2Fcode-challenge.png&w=3840&q=75)

Extract this code using the browser API:

Extract Code

```code-block text-sm

1const urlParams = new URLSearchParams(window.location.search);2const code = urlParams.get('code');
```

Then use it to make an API call to `https://openrouter.ai/api/v1/auth/keys` to exchange the code for a user-controlled API key:

Exchange Code

```code-block text-sm

1const response = await fetch('https://openrouter.ai/api/v1/auth/keys', {2  method: 'POST',3  headers: {4    'Content-Type': 'application/json',5  },6  body: JSON.stringify({7    code: '<CODE_FROM_QUERY_PARAM>',8    code_verifier: '<CODE_VERIFIER>', // If code_challenge was used9    code_challenge_method: '<CODE_CHALLENGE_METHOD>', // If code_challenge was used10  }),11});1213const { key } = await response.json();
```

And that’s it for the PKCE flow!

### Step 3: Use the API key

Store the API key securely within the user’s browser or in your own database, and use it to [make OpenRouter requests](https://openrouter.ai/docs/api-reference/completion).

Make an OpenRouter request

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    Authorization: 'Bearer <API_KEY>',5    'Content-Type': 'application/json',6  },7  body: JSON.stringify({8    model: 'openai/gpt-4o',9    messages: [10      {11        role: 'user',12        content: 'Hello!',13      },14    ],15  }),16});
```

## Error Codes

- `400 Invalid code_challenge_method`: Make sure you’re using the same code challenge method in step 1 as in step 2.
- `403 Invalid code or code_verifier`: Make sure your user is logged in to OpenRouter, and that `code_verifier` and `code_challenge_method` are correct.
- `405 Method Not Allowed`: Make sure you’re using `POST` and `HTTPS` for your request.

## External Tools

- [PKCE Tools](https://example-app.com/pkce)
- [Online PKCE Generator](https://tonyxu-io.github.io/pkce-generator/)