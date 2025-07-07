---
url: "https://docs.anthropic.com/en/api/claude-on-vertex-ai"
title: "Vertex AI API - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

3rd-party APIs

Vertex AI API

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

The Vertex API for accessing Claude is nearly-identical to the [Messages API](https://docs.anthropic.com/en/api/messages) and supports all of the same options, with two key differences:

- In Vertex, `model` is not passed in the request body. Instead, it is specified in the Google Cloud endpoint URL.
- In Vertex, `anthropic_version` is passed in the request body (rather than as a header), and must be set to the value `vertex-2023-10-16`.

Vertex is also supported by Anthropic’s official [client SDKs](https://docs.anthropic.com/en/api/client-sdks). This guide will walk you through the process of making a request to Claude on Vertex AI in either Python or TypeScript.

Note that this guide assumes you have already have a GCP project that is able to use Vertex AI. See [using the Claude 3 models from Anthropic](https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude) for more information on the setup required, as well as a full walkthrough.

## [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#install-an-sdk-for-accessing-vertex-ai)  Install an SDK for accessing Vertex AI

First, install Anthropic’s [client SDK](https://docs.anthropic.com/en/api/client-sdks) for your language of choice.

Python

TypeScript

Copy

```Python
pip install -U google-cloud-aiplatform "anthropic[vertex]"

```

## [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#accessing-vertex-ai)  Accessing Vertex AI

### [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#model-availability)  Model Availability

Note that Anthropic model availability varies by region. Search for “Claude” in the [Vertex AI Model Garden](https://cloud.google.com/model-garden) or go to [Use Claude 3](https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude) for the latest information.

#### [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#api-model-names)  API model names

| Model | Vertex AI API model name |
| --- | --- |
| Claude Opus 4 | claude-opus-4@20250514 |
| Claude Sonnet 4 | claude-sonnet-4@20250514 |
| Claude Sonnet 3.7 | claude-3-7-sonnet@20250219 |
| Claude Haiku 3.5 | claude-3-5-haiku@20241022 |
| Claude Sonnet 3.5 | claude-3-5-sonnet-v2@20241022 |
| Claude Opus 3 (Public Preview) | claude-3-opus@20240229 |
| Claude Sonnet 3 | claude-3-sonnet@20240229 |
| Claude Haiku 3 | claude-3-haiku@20240307 |

### [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#making-requests)  Making requests

Before running requests you may need to run `gcloud auth application-default login` to authenticate with GCP.

The following examples shows how to generate text from Claude on Vertex AI:

Python

TypeScript

Shell

Copy

```Python
from anthropic import AnthropicVertex

project_id = "MY_PROJECT_ID"
# Where the model is running
region = "us-east5"

client = AnthropicVertex(project_id=project_id, region=region)

message = client.messages.create(
    model="claude-opus-4@20250514",
    max_tokens=100,
    messages=[\
        {\
            "role": "user",\
            "content": "Hey Claude!",\
        }\
    ],
)
print(message)

```

See our [client SDKs](https://docs.anthropic.com/en/api/client-sdks) and the official [Vertex AI docs](https://cloud.google.com/vertex-ai/docs) for more details.

## [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#activity-logging)  Activity logging

Vertex provides a [request-response logging service](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/request-response-logging) that allows customers to log the prompts and completions associated with your usage.

Anthropic recommends that you log your activity on at least a 30-day rolling basis in order to understand your activity and investigate any potential misuse.

Turning on this service does not give Google or Anthropic any access to your content.

## [​](https://docs.anthropic.com/en/api/claude-on-vertex-ai\#feature-support)  Feature support

You can find all the features currently supported on Vertex [here](https://docs.anthropic.com/en/docs/build-with-claude/overview).

Was this page helpful?

YesNo

[Amazon Bedrock API](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock) [Versions](https://docs.anthropic.com/en/api/versioning)

On this page

- [Install an SDK for accessing Vertex AI](https://docs.anthropic.com/en/api/claude-on-vertex-ai#install-an-sdk-for-accessing-vertex-ai)
- [Accessing Vertex AI](https://docs.anthropic.com/en/api/claude-on-vertex-ai#accessing-vertex-ai)
- [Model Availability](https://docs.anthropic.com/en/api/claude-on-vertex-ai#model-availability)
- [API model names](https://docs.anthropic.com/en/api/claude-on-vertex-ai#api-model-names)
- [Making requests](https://docs.anthropic.com/en/api/claude-on-vertex-ai#making-requests)
- [Activity logging](https://docs.anthropic.com/en/api/claude-on-vertex-ai#activity-logging)
- [Feature support](https://docs.anthropic.com/en/api/claude-on-vertex-ai#feature-support)