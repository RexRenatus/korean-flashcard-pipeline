---
url: "https://openrouter.ai/docs/use-cases/byok"
title: "BYOK | Use Your Own Provider Keys with OpenRouter | OpenRouter | Documentation"
---

## Bring your own API Keys

OpenRouter supports both OpenRouter credits and the option to bring your own provider keys (BYOK).

When you use OpenRouter credits, your rate limits for each provider are managed by OpenRouter.

Using provider keys enables direct control over rate limits and costs via your provider account.

Your provider keys are securely encrypted and used for all requests routed through the specified provider.

Manage keys in your [account settings](https://openrouter.ai/settings/integrations).

The cost of using custom provider keys on OpenRouter is **5% of what the same model/provider would cost normally on OpenRouter** and will be deducted from your OpenRouter credits.

### Automatic Fallback

You can configure individual keys to act as fallbacks.

When “Use this key as a fallback” is enabled for a key, OpenRouter will prioritize using your credits. If it hits a rate limit or encounters a failure, it will then retry with your key.

Conversely, if “Use this key as a fallback” is disabled for a key, OpenRouter will prioritize using your key. If it hits a rate limit or encounters a failure, it will then retry with your credits.

### Azure API Keys

To use Azure AI Services with OpenRouter, you’ll need to provide your Azure API key configuration in JSON format. Each key configuration requires the following fields:

```code-block text-sm

1{2  "model_slug": "the-openrouter-model-slug",3  "endpoint_url": "https://<resource>.services.ai.azure.com/deployments/<model-id>/chat/completions?api-version=<api-version>",4  "api_key": "your-azure-api-key",5  "model_id": "the-azure-model-id"6}
```

You can find these values in your Azure AI Services resource:

1. **endpoint\_url**: Navigate to your Azure AI Services resource in the Azure portal. In the “Overview” section, you’ll find your endpoint URL. Make sure to append `/chat/completions` to the base URL. You can read more in the [Azure Foundry documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/model-inference/concepts/endpoints?tabs=python).

2. **api\_key**: In the same “Overview” section of your Azure AI Services resource, you can find your API key under “Keys and Endpoint”.

3. **model\_id**: This is the name of your model deployment in Azure AI Services.

4. **model\_slug**: This is the OpenRouter model identifier you want to use this key for.


Since Azure supports multiple model deployments, you can provide an array of configurations for different models:

```code-block text-sm

1[2  {3    "model_slug": "mistralai/mistral-large",4    "endpoint_url": "https://example-project.openai.azure.com/openai/deployments/mistral-large/chat/completions?api-version=2024-08-01-preview",5    "api_key": "your-azure-api-key",6    "model_id": "mistral-large"7  },8  {9    "model_slug": "openai/gpt-4o",10    "endpoint_url": "https://example-project.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview",11    "api_key": "your-azure-api-key",12    "model_id": "gpt-4o"13  }14]
```

Make sure to replace the url with your own project url. Also the url should end with /chat/completions with the api version that you would like to use.

### AWS Bedrock API Keys

To use Amazon Bedrock with OpenRouter, you’ll need to provide your AWS credentials in JSON format. The configuration requires the following fields:

```code-block text-sm

1{2  "accessKeyId": "your-aws-access-key-id",3  "secretAccessKey": "your-aws-secret-access-key",4  "region": "your-aws-region"5}
```

You can find these values in your AWS account:

1. **accessKeyId**: This is your AWS Access Key ID. You can create or find your access keys in the AWS Management Console under “Security Credentials” in your AWS account.

2. **secretAccessKey**: This is your AWS Secret Access Key, which is provided when you create an access key.

3. **region**: The AWS region where your Amazon Bedrock models are deployed (e.g., “us-east-1”, “us-west-2”).


Make sure your AWS IAM user or role has the necessary permissions to access Amazon Bedrock services. At minimum, you’ll need permissions for:

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream` (for streaming responses)

Example IAM policy:

```code-block text-sm

1{2  "Version": "2012-10-17",3  "Statement": [4    {5      "Effect": "Allow",6      "Action": [7        "bedrock:InvokeModel",8        "bedrock:InvokeModelWithResponseStream"9      ],10      "Resource": "*"11    }12  ]13}
```

For enhanced security, we recommend creating dedicated IAM users with limited permissions specifically for use with OpenRouter.

Learn more in the [AWS Bedrock Getting Started with the API](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api.html) documentation, [IAM Permissions Setup](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html) guide, or the [AWS Bedrock API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/welcome.html).