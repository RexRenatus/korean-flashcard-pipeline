---
url: "https://openrouter.ai/docs/community/vercel-ai-sdk"
title: "Vercel AI SDK Integration | OpenRouter SDK Support | OpenRouter | Documentation"
---

## Vercel AI SDK

You can use the [Vercel AI SDK](https://www.npmjs.com/package/ai) to integrate OpenRouter with your Next.js app. To get started, install [@openrouter/ai-sdk-provider](https://github.com/OpenRouterTeam/ai-sdk-provider):

```code-block text-sm

$npm install @openrouter/ai-sdk-provider
```

And then you can use [streamText()](https://sdk.vercel.ai/docs/reference/ai-sdk-core/stream-text) API to stream text from OpenRouter.

TypeScript

```code-block text-sm

1import { createOpenRouter } from '@openrouter/ai-sdk-provider';2import { streamText } from 'ai';3import { z } from 'zod';45export const getLasagnaRecipe = async (modelName: string) => {6  const openrouter = createOpenRouter({7    apiKey: '${API_KEY_REF}',8  });910  const response = streamText({11    model: openrouter(modelName),12    prompt: 'Write a vegetarian lasagna recipe for 4 people.',13  });1415  await response.consumeStream();16  return response.text;17};1819export const getWeather = async (modelName: string) => {20  const openrouter = createOpenRouter({21    apiKey: '${API_KEY_REF}',22  });2324  const response = streamText({25    model: openrouter(modelName),26    prompt: 'What is the weather in San Francisco, CA in Fahrenheit?',27    tools: {28      getCurrentWeather: {29        description: 'Get the current weather in a given location',30        parameters: z.object({31          location: z32            .string()33            .describe('The city and state, e.g. San Francisco, CA'),34          unit: z.enum(['celsius', 'fahrenheit']).optional(),35        }),36        execute: async ({ location, unit = 'celsius' }) => {37          // Mock response for the weather38          const weatherData = {39            'Boston, MA': {40              celsius: '15°C',41              fahrenheit: '59°F',42            },43            'San Francisco, CA': {44              celsius: '18°C',45              fahrenheit: '64°F',46            },47          };4849          const weather = weatherData[location];50          if (!weather) {51            return `Weather data for ${location} is not available.`;52          }5354          return `The current weather in ${location} is ${weather[unit]}.`;55        },56      },57    },58  });5960  await response.consumeStream();61  return response.text;62};

```