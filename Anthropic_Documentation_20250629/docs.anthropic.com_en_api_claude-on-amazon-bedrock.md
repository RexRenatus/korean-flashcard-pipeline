---
url: "https://docs.anthropic.com/en/api/claude-on-amazon-bedrock"
title: "Amazon Bedrock API - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

3rd-party APIs

Amazon Bedrock API

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

Calling Claude through Bedrock slightly differs from how you would call Claude when using Anthropic’s client SDK’s. This guide will walk you through the process of completing an API call to Claude on Bedrock in either Python or TypeScript.

Note that this guide assumes you have already signed up for an [AWS account](https://portal.aws.amazon.com/billing/signup) and configured programmatic access.

## [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#install-and-configure-the-aws-cli)  Install and configure the AWS CLI

1. [Install a version of the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html) at or newer than version `2.13.23`
2. Configure your AWS credentials using the AWS configure command (see [Configure the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)) or find your credentials by navigating to “Command line or programmatic access” within your AWS dashboard and following the directions in the popup modal.
3. Verify that your credentials are working:

Shell

Copy

```bash
aws sts get-caller-identity

```

## [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#install-an-sdk-for-accessing-bedrock)  Install an SDK for accessing Bedrock

Anthropic’s [client SDKs](https://docs.anthropic.com/en/api/client-sdks) support Bedrock. You can also use an AWS SDK like `boto3` directly.

Python

TypeScript

Boto3 (Python)

Copy

```Python
pip install -U "anthropic[bedrock]"

```

## [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#accessing-bedrock)  Accessing Bedrock

### [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#subscribe-to-anthropic-models)  Subscribe to Anthropic models

Go to the [AWS Console > Bedrock > Model Access](https://console.aws.amazon.com/bedrock/home?region=us-west-2#/modelaccess) and request access to Anthropic models. Note that Anthropic model availability varies by region. See [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html) for latest information.

#### [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#api-model-names)  API model names

| Model | Bedrock API model name |
| --- | --- |
| Claude Opus 4 | anthropic.claude-opus-4-20250514-v1:0 |
| Claude Sonnet 4 | anthropic.claude-sonnet-4-20250514-v1:0 |
| Claude Sonnet 3.7 | anthropic.claude-3-7-sonnet-20250219-v1:0 |
| Claude Haiku 3.5 | anthropic.claude-3-5-haiku-20241022-v1:0 |
| Claude Sonnet 3.5 | anthropic.claude-3-5-sonnet-20241022-v2:0 |
| Claude Opus 3 | anthropic.claude-3-opus-20240229-v1:0 |
| Claude Sonnet 3 | anthropic.claude-3-sonnet-20240229-v1:0 |
| Claude Haiku 3 | anthropic.claude-3-haiku-20240307-v1:0 |

### [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#list-available-models)  List available models

The following examples show how to print a list of all the Claude models available through Bedrock:

AWS CLI

Boto3 (Python)

Copy

```bash
aws bedrock list-foundation-models --region=us-west-2 --by-provider anthropic --query "modelSummaries[*].modelId"

```

### [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#making-requests)  Making requests

The following examples shows how to generate text from Claude on Bedrock:

Python

TypeScript

Boto3 (Python)

Copy

```Python
from anthropic import AnthropicBedrock

client = AnthropicBedrock(
    # Authenticate by either providing the keys below or use the default AWS credential providers, such as
    # using ~/.aws/credentials or the "AWS_SECRET_ACCESS_KEY" and "AWS_ACCESS_KEY_ID" environment variables.
    aws_access_key="<access key>",
    aws_secret_key="<secret key>",
    # Temporary credentials can be used with aws_session_token.
    # Read more at https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html.
    aws_session_token="<session_token>",
    # aws_region changes the aws region to which the request is made. By default, we read AWS_REGION,
    # and if that's not present, we default to us-east-1. Note that we do not read ~/.aws/config for the region.
    aws_region="us-west-2",
)

message = client.messages.create(
    model="anthropic.claude-opus-4-20250514-v1:0",
    max_tokens=256,
    messages=[{"role": "user", "content": "Hello, world"}]
)
print(message.content)

```

See our [client SDKs](https://docs.anthropic.com/en/api/client-sdks) for more details, and the official Bedrock docs [here](https://docs.aws.amazon.com/bedrock/).

## [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#activity-logging)  Activity logging

Bedrock provides an [invocation logging service](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) that allows customers to log the prompts and completions associated with your usage.

Anthropic recommends that you log your activity on at least a 30-day rolling basis in order to understand your activity and investigate any potential misuse.

Turning on this service does not give AWS or Anthropic any access to your content.

## [​](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock\#feature-support)  Feature support

You can find all the features currently supported on Bedrock [here](https://docs.anthropic.com/en/docs/build-with-claude/overview).

Was this page helpful?

YesNo

[Message Batches examples](https://docs.anthropic.com/en/api/messages-batch-examples) [Vertex AI API](https://docs.anthropic.com/en/api/claude-on-vertex-ai)

On this page

- [Install and configure the AWS CLI](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#install-and-configure-the-aws-cli)
- [Install an SDK for accessing Bedrock](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#install-an-sdk-for-accessing-bedrock)
- [Accessing Bedrock](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#accessing-bedrock)
- [Subscribe to Anthropic models](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#subscribe-to-anthropic-models)
- [API model names](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#api-model-names)
- [List available models](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#list-available-models)
- [Making requests](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#making-requests)
- [Activity logging](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#activity-logging)
- [Feature support](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock#feature-support)