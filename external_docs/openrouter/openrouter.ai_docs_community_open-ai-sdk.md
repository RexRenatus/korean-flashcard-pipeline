---
url: "https://openrouter.ai/docs/community/open-ai-sdk"
title: "OpenAI SDK Integration | OpenRouter SDK Support | OpenRouter | Documentation"
---

## Using the OpenAI SDK

- Using `pip install openai`: [github](https://github.com/OpenRouterTeam/openrouter-examples-python/blob/main/src/openai_test.py).
- Using `npm i openai`: [github](https://github.com/OpenRouterTeam/openrouter-examples/blob/main/examples/openai/index.ts).










You can also use
[Grit](https://app.grit.io/studio?key=RKC0n7ikOiTGTNVkI8uRS) to
automatically migrate your code. Simply run `npx @getgrit/launcher   openrouter`.


TypeScriptPython

```code-block text-sm

1import OpenAI from "openai"23const openai = new OpenAI({4  baseURL: "https://openrouter.ai/api/v1",5  apiKey: "${API_KEY_REF}",6  defaultHeaders: {7    ${getHeaderLines().join('\n        ')}8  },9})1011async function main() {12  const completion = await openai.chat.completions.create({13    model: "${Model.GPT_4_Omni}",14    messages: [15      { role: "user", content: "Say this is a test" }16    ],17  })1819  console.log(completion.choices[0].message)20}21main();
```