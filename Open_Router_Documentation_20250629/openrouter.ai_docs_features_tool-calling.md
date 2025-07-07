---
url: "https://openrouter.ai/docs/features/tool-calling"
title: "Tool & Function Calling | Use Tools with OpenRouter | OpenRouter | Documentation"
---

Tool calls (also known as function calls) give an LLM access to external tools. The LLM does not call the tools directly. Instead, it suggests the tool to call. The user then calls the tool separately and provides the results back to the LLM. Finally, the LLM formats the response into an answer to the user’s original question.

OpenRouter standardizes the tool calling interface across models and providers.

For a primer on how tool calling works in the OpenAI SDK, please see [this article](https://platform.openai.com/docs/guides/function-calling?api-mode=chat), or if you prefer to learn from a full end-to-end example, keep reading.

### Tool Calling Example

Here is Python code that gives LLMs the ability to call an external API — in this case Project Gutenberg, to search for books.

First, let’s do some basic setup:

PythonTypeScript

```code-block text-sm

1import json, requests2from openai import OpenAI34OPENROUTER_API_KEY = f"<OPENROUTER_API_KEY>"56# You can use any model that supports tool calling7MODEL = "google/gemini-2.0-flash-001"89openai_client = OpenAI(10  base_url="https://openrouter.ai/api/v1",11  api_key=OPENROUTER_API_KEY,12)1314task = "What are the titles of some James Joyce books?"1516messages = [17  {18    "role": "system",19    "content": "You are a helpful assistant."20  },21  {22    "role": "user",23    "content": task,24  }25]

```

### Define the Tool

Next, we define the tool that we want to call. Remember, the tool is going to get _requested_ by the LLM, but the code we are writing here is ultimately responsible for executing the call and returning the results to the LLM.

PythonTypeScript

```code-block text-sm

1def search_gutenberg_books(search_terms):2    search_query = " ".join(search_terms)3    url = "https://gutendex.com/books"4    response = requests.get(url, params={"search": search_query})56    simplified_results = []7    for book in response.json().get("results", []):8        simplified_results.append({9            "id": book.get("id"),10            "title": book.get("title"),11            "authors": book.get("authors")12        })1314    return simplified_results1516tools = [17  {18    "type": "function",19    "function": {20      "name": "search_gutenberg_books",21      "description": "Search for books in the Project Gutenberg library based on specified search terms",22      "parameters": {23        "type": "object",24        "properties": {25          "search_terms": {26            "type": "array",27            "items": {28              "type": "string"29            },30            "description": "List of search terms to find books in the Gutenberg library (e.g. ['dickens', 'great'] to search for books by Dickens with 'great' in the title)"31          }32        },33        "required": ["search_terms"]34      }35    }36  }37]3839TOOL_MAPPING = {40    "search_gutenberg_books": search_gutenberg_books41}

```

Note that the “tool” is just a normal function. We then write a JSON “spec” compatible with the OpenAI function calling parameter. We’ll pass that spec to the LLM so that it knows this tool is available and how to use it. It will request the tool when needed, along with any arguments. We’ll then marshal the tool call locally, make the function call, and return the results to the LLM.

### Tool use and tool results

Let’s make the first OpenRouter API call to the model:

PythonTypeScript

```code-block text-sm

1request_1 = {2    "model": google/gemini-2.0-flash-001,3    "tools": tools,4    "messages": messages5}67response_1 = openai_client.chat.completions.create(**request_1).message
```

The LLM responds with a finish reason of tool\_calls, and a tool\_calls array. In a generic LLM response-handler, you would want to check the finish reason before processing tool calls, but here we will assume it’s the case. Let’s keep going, by processing the tool call:

PythonTypeScript

```code-block text-sm

1# Append the response to the messages array so the LLM has the full context2# It's easy to forget this step!3messages.append(response_1)45# Now we process the requested tool calls, and use our book lookup tool6for tool_call in response_1.tool_calls:7    '''8    In this case we only provided one tool, so we know what function to call.9    When providing multiple tools, you can inspect `tool_call.function.name`10    to figure out what function you need to call locally.11    '''12    tool_name = tool_call.function.name13    tool_args = json.loads(tool_call.function.arguments)14    tool_response = TOOL_MAPPING[tool_name](**tool_args)15    messages.append({16      "role": "tool",17      "tool_call_id": tool_call.id,18      "name": tool_name,19      "content": json.dumps(tool_response),20    })
```

The messages array now has:

1. Our original request
2. The LLM’s response (containing a tool call request)
3. The result of the tool call (a json object returned from the Project Gutenberg API)

Now, we can make a second OpenRouter API call, and hopefully get our result!

PythonTypeScript

```code-block text-sm

1request_2 = {2  "model": MODEL,3  "messages": messages,4  "tools": tools5}67response_2 = openai_client.chat.completions.create(**request_2)89print(response_2.choices[0].message.content)
```

The output will be something like:

```code-block text-sm

Here are some books by James Joyce:*   *Ulysses**   *Dubliners**   *A Portrait of the Artist as a Young Man**   *Chamber Music**   *Exiles: A Play in Three Acts*
```

We did it! We’ve successfully used a tool in a prompt.

## A Simple Agentic Loop

In the example above, the calls are made explicitly and sequentially. To handle a wide variety of user inputs and tool calls, you can use an agentic loop.

Here’s an example of a simple agentic loop (using the same `tools` and initial `messages` as above):

PythonTypeScript

```code-block text-sm

1def call_llm(msgs):2    resp = openai_client.chat.completions.create(3        model=google/gemini-2.0-flash-001,4        tools=tools,5        messages=msgs6    )7    msgs.append(resp.choices[0].message.dict())8    return resp910def get_tool_response(response):11    tool_call = response.choices[0].message.tool_calls[0]12    tool_name = tool_call.function.name13    tool_args = json.loads(tool_call.function.arguments)1415    # Look up the correct tool locally, and call it with the provided arguments16    # Other tools can be added without changing the agentic loop17    tool_result = TOOL_MAPPING[tool_name](**tool_args)1819    return {20        "role": "tool",21        "tool_call_id": tool_call.id,22        "name": tool_name,23        "content": tool_result,24    }2526while True:27    resp = call_llm(_messages)2829    if resp.choices[0].message.tool_calls is not None:30        messages.append(get_tool_response(resp))31    else:32        break3334print(messages[-1]['content'])

```