---
url: "https://openrouter.ai/docs/api-reference/streaming"
title: "API Streaming | Real-time Model Responses in OpenRouter | OpenRouter | Documentation"
---

The OpenRouter API allows streaming responses from _any model_. This is useful for building chat interfaces or other applications where the UI should update as the model generates the response.

To enable streaming, you can set the `stream` parameter to `true` in your request. The model will then stream the response to the client in chunks, rather than returning the entire response at once.

Here is an example of how to stream a response, and process it:

PythonTypeScript

```code-block text-sm

1import requests2import json34question = "How would you build the tallest building ever?"56url = "https://openrouter.ai/api/v1/chat/completions"7headers = {8  "Authorization": f"Bearer <OPENROUTER_API_KEY>",9  "Content-Type": "application/json"10}1112payload = {13  "model": "openai/gpt-4o",14  "messages": [{"role": "user", "content": question}],15  "stream": True16}1718buffer = ""19with requests.post(url, headers=headers, json=payload, stream=True) as r:20  for chunk in r.iter_content(chunk_size=1024, decode_unicode=True):21    buffer += chunk22    while True:23      try:24        # Find the next complete SSE line25        line_end = buffer.find('\n')26        if line_end == -1:27          break2829        line = buffer[:line_end].strip()30        buffer = buffer[line_end + 1:]3132        if line.startswith('data: '):33          data = line[6:]34          if data == '[DONE]':35            break3637          try:38            data_obj = json.loads(data)39            content = data_obj["choices"][0]["delta"].get("content")40            if content:41              print(content, end="", flush=True)42          except json.JSONDecodeError:43            pass44      except Exception:45        break

```

### Additional Information

For SSE (Server-Sent Events) streams, OpenRouter occasionally sends comments to prevent connection timeouts. These comments look like:

```code-block text-sm

: OPENROUTER PROCESSING
```

Comment payload can be safely ignored per the [SSE specs](https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation). However, you can leverage it to improve UX as needed, e.g. by showing a dynamic loading indicator.

Some SSE client implementations might not parse the payload according to spec, which leads to an uncaught error when you `JSON.stringify` the non-JSON payloads. We recommend the following clients:

- [eventsource-parser](https://github.com/rexxars/eventsource-parser)
- [OpenAI SDK](https://www.npmjs.com/package/openai)
- [Vercel AI SDK](https://www.npmjs.com/package/ai)

### Stream Cancellation

Streaming requests can be cancelled by aborting the connection. For supported providers, this immediately stops model processing and billing.

###### Provider Support

**Supported**

- OpenAI, Azure, Anthropic
- Fireworks, Mancer, Recursal
- AnyScale, Lepton, OctoAI
- Novita, DeepInfra, Together
- Cohere, Hyperbolic, Infermatic
- Avian, XAI, Cloudflare
- SFCompute, Nineteen, Liquid
- Friendli, Chutes, DeepSeek

**Not Currently Supported**

- AWS Bedrock, Groq, Modal
- Google, Google AI Studio, Minimax
- HuggingFace, Replicate, Perplexity
- Mistral, AI21, Featherless
- Lynn, Lambda, Reflection
- SambaNova, Inflection, ZeroOneAI
- AionLabs, Alibaba, Nebius
- Kluster, Targon, InferenceNet

To implement stream cancellation:

PythonTypeScript

```code-block text-sm

1import requests2from threading import Event, Thread34def stream_with_cancellation(prompt: str, cancel_event: Event):5    with requests.Session() as session:6        response = session.post(7            "https://openrouter.ai/api/v1/chat/completions",8            headers={"Authorization": f"Bearer <OPENROUTER_API_KEY>"},9            json={"model": "openai/gpt-4o", "messages": [{"role": "user", "content": prompt}], "stream": True},10            stream=True11        )1213        try:14            for line in response.iter_lines():15                if cancel_event.is_set():16                    response.close()17                    return18                if line:19                    print(line.decode(), end="", flush=True)20        finally:21            response.close()2223# Example usage:24cancel_event = Event()25stream_thread = Thread(target=lambda: stream_with_cancellation("Write a story", cancel_event))26stream_thread.start()2728# To cancel the stream:29cancel_event.set()

```

Cancellation only works for streaming requests with supported providers. For
non-streaming requests or unsupported providers, the model will continue
processing and you will be billed for the complete response.