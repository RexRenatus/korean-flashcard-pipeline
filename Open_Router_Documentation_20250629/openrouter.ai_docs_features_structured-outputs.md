---
url: "https://openrouter.ai/docs/features/structured-outputs"
title: "Structured Outputs | Enforce JSON Schema in OpenRouter API Responses | OpenRouter | Documentation"
---

OpenRouter supports structured outputs for compatible models, ensuring responses follow a specific JSON Schema format. This feature is particularly useful when you need consistent, well-formatted responses that can be reliably parsed by your application.

## Overview

Structured outputs allow you to:

- Enforce specific JSON Schema validation on model responses
- Get consistent, type-safe outputs
- Avoid parsing errors and hallucinated fields
- Simplify response handling in your application

## Using Structured Outputs

To use structured outputs, include a `response_format` parameter in your request, with `type` set to `json_schema` and the `json_schema` object containing your schema:

```code-block text-sm

1{2  "messages": [3    { "role": "user", "content": "What's the weather like in London?" }4  ],5  "response_format": {6    "type": "json_schema",7    "json_schema": {8      "name": "weather",9      "strict": true,10      "schema": {11        "type": "object",12        "properties": {13          "location": {14            "type": "string",15            "description": "City or location name"16          },17          "temperature": {18            "type": "number",19            "description": "Temperature in Celsius"20          },21          "conditions": {22            "type": "string",23            "description": "Weather conditions description"24          }25        },26        "required": ["location", "temperature", "conditions"],27        "additionalProperties": false28      }29    }30  }31}

```

The model will respond with a JSON object that strictly follows your schema:

```code-block text-sm

1{2  "location": "London",3  "temperature": 18,4  "conditions": "Partly cloudy with light drizzle"5}
```

## Model Support

Structured outputs are supported by select models.

You can find a list of models that support structured outputs on the [models page](https://openrouter.ai/models?order=newest&supported_parameters=structured_outputs).

- OpenAI models (GPT-4o and later versions) [Docs](https://platform.openai.com/docs/guides/structured-outputs)
- All Fireworks provided models [Docs](https://docs.fireworks.ai/structured-responses/structured-response-formatting#structured-response-modes)

To ensure your chosen model supports structured outputs:

1. Check the model’s supported parameters on the [models page](https://openrouter.ai/models)
2. Set `require_parameters: true` in your provider preferences (see [Provider Routing](https://openrouter.ai/docs/features/provider-routing))
3. Include `response_format` and set `type: json_schema` in the required parameters

## Best Practices

1. **Include descriptions**: Add clear descriptions to your schema properties to guide the model

2. **Use strict mode**: Always set `strict: true` to ensure the model follows your schema exactly


## Example Implementation

Here’s a complete example using the Fetch API:

With TypeScriptWith Python

```code-block text-sm

1const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {2  method: 'POST',3  headers: {4    Authorization: 'Bearer <OPENROUTER_API_KEY>',5    'Content-Type': 'application/json',6  },7  body: JSON.stringify({8    model: 'openai/gpt-4',9    messages: [10      { role: 'user', content: 'What is the weather like in London?' },11    ],12    response_format: {13      type: 'json_schema',14      json_schema: {15        name: 'weather',16        strict: true,17        schema: {18          type: 'object',19          properties: {20            location: {21              type: 'string',22              description: 'City or location name',23            },24            temperature: {25              type: 'number',26              description: 'Temperature in Celsius',27            },28            conditions: {29              type: 'string',30              description: 'Weather conditions description',31            },32          },33          required: ['location', 'temperature', 'conditions'],34          additionalProperties: false,35        },36      },37    },38  }),39});4041const data = await response.json();42const weatherInfo = data.choices[0].message.content;

```

## Streaming with Structured Outputs

Structured outputs are also supported with streaming responses. The model will stream valid partial JSON that, when complete, forms a valid response matching your schema.

To enable streaming with structured outputs, simply add `stream: true` to your request:

```code-block text-sm

1{2  "stream": true,3  "response_format": {4    "type": "json_schema",5    // ... rest of your schema6  }7}
```

## Error Handling

When using structured outputs, you may encounter these scenarios:

1. **Model doesn’t support structured outputs**: The request will fail with an error indicating lack of support
2. **Invalid schema**: The model will return an error if your JSON Schema is invalid