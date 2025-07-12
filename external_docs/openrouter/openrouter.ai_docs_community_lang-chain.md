---
url: "https://openrouter.ai/docs/community/lang-chain"
title: "LangChain Integration | OpenRouter SDK Support | OpenRouter | Documentation"
---

## Using LangChain

- Using [LangChain for Python](https://github.com/langchain-ai/langchain): [github](https://github.com/alexanderatallah/openrouter-streamlit/blob/main/pages/2_Langchain_Quickstart.py)
- Using [LangChain.js](https://github.com/langchain-ai/langchainjs): [github](https://github.com/OpenRouterTeam/openrouter-examples/blob/main/examples/langchain/index.ts)
- Using [Streamlit](https://streamlit.io/): [github](https://github.com/alexanderatallah/openrouter-streamlit)

TypeScriptPython

```code-block text-sm

1const chat = new ChatOpenAI(2  {3    modelName: '<model_name>',4    temperature: 0.8,5    streaming: true,6    openAIApiKey: '${API_KEY_REF}',7  },8  {9    basePath: 'https://openrouter.ai/api/v1',10    baseOptions: {11      headers: {12        'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.13        'X-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.14      },15    },16  },17);
```