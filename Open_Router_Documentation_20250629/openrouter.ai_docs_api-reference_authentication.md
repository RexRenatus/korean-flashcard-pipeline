---
url: "https://openrouter.ai/docs/api-reference/authentication"
title: "API Authentication | OpenRouter OAuth and API Keys | OpenRouter | Documentation"
---

You can cover model costs with OpenRouter API keys.

Our API authenticates requests using Bearer tokens. This allows you to use `curl` or the [OpenAI SDK](https://platform.openai.com/docs/frameworks) directly with OpenRouter.

API keys on OpenRouter are more powerful than keys used directly for model APIs.

They allow users to set credit limits for apps, and they can be used in [OAuth](https://openrouter.ai/docs/use-cases/oauth-pkce) flows.

## Using an API key

To use an API key, [first create your key](https://openrouter.ai/keys). Give it a name and you can optionally set a credit limit.

If you’re calling the OpenRouter API directly, set the `Authorization` header to a Bearer token with your API key.

If you’re using the OpenAI Typescript SDK, set the `api_base` to `https://openrouter.ai/api/v1` and the `apiKey` to your API key.

TypeScript (Bearer Token)TypeScript (OpenAI SDK)PythonShell

```code-block text-sm

1fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    Authorization: 'Bearer <OPENROUTER_API_KEY>',5    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.6    'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.7    'Content-Type': 'application/json',8  },9  body: JSON.stringify({10    model: 'openai/gpt-4o',11    messages: [12      {13        role: 'user',14        content: 'What is the meaning of life?',15      },16    ],17  }),18});
```

To stream with Python, [see this example from OpenAI](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb).

## If your key has been exposed

You must protect your API keys and never commit them to public repositories.

OpenRouter is a GitHub secret scanning partner, and has other methods to detect exposed keys. If we determine that your key has been compromised, you will receive an email notification.

If you receive such a notification or suspect your key has been exposed, immediately visit [your key settings page](https://openrouter.ai/settings/keys) to delete the compromised key and create a new one.

Using environment variables and keeping keys out of your codebase is strongly recommended.