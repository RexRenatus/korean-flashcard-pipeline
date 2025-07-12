---
url: "https://openrouter.ai/docs/features/privacy-and-logging"
title: "Privacy, Logging, and Data Collection | Keeping your data safe | OpenRouter | Documentation"
---

When using AI through OpenRouter, whether via the chat interface or the API, your prompts and responses go through multiple touchpoints. You have control over how your data is handled at each step.

This page is designed to give a practical overview of how your data is handled, stored, and used. More information is available in the [privacy policy](https://openrouter.ai/privacy) and [terms of service](https://openrouter.ai/terms).

## Within OpenRouter

OpenRouter does not store your prompts or responses, _unless_ you have explicitly opted in to prompt logging in your account settings. It’s as simple as that.

OpenRouter samples a small number of prompts for categorization to power our reporting and model ranking. If you are not opted in to prompt logging, any categorization of your prompts is stored completely anonymously and never associated with your account or user ID. The categorization is done by model with a zero-data-retention policy.

OpenRouter does store metadata (e.g. number of prompt and completion tokens, latency, etc) for each request. This is used to power our reporting and model ranking, and your [activity feed](https://openrouter.ai/activity).

## Provider Policies

### Training on Prompts

Each provider on OpenRouter has its own data handling policies. We reflect those policies in structured data on each AI endpoint that we offer.

On your account settings page, you can set whether you would like to allow routing to providers that may train on your data (according to their own policies). There are separate settings for paid and free models.

Wherever possible, OpenRouter works with providers to ensure that prompts will not be trained on, but there are exceptions. If you opt out of training in your account settings, OpenRouter will not route to providers that train. This setting has no bearing on OpenRouter’s own policies and what we do with your prompts.

##### Data Policy Filtering

You can [restrict individual requests](https://openrouter.ai/docs/features/provider-routing#requiring-providers-to-comply-with-data-policies)
to only use providers with a certain data policy.

This is also available as an account-wide setting in [your privacy settings](https://openrouter.ai/settings/privacy).

### Data Retention & Logging

Providers also have their own data retention policies, often for compliance reasons. OpenRouter does not have routing rules that change based on data retention policies of providers, but the retention policies as reflected in each provider’s terms are shown below. Any user of OpenRouter can ignore providers that don’t meet their own data retention requirements.

The full terms of service for each provider are linked from the provider’s page, and aggregated in the [documentation](https://openrouter.ai/docs/features/provider-routing#terms-of-service).

| Provider | Data Retention | Train on Prompts |
| --- | --- | --- |
| Mistral | Retained for 30 days | ✓ Does not train |
| AionLabs | Unknown retention policy | ✓ Does not train |
| AtlasCloud | Zero retention | ✓ Does not train |
| Atoma | Zero retention | ✓ Does not train |
| Avian.io | Unknown retention policy | ✓ Does not train |
| Azure | Zero retention | ✓ Does not train |
| Cloudflare | Unknown retention policy | ✓ Does not train |
| Cohere | Retained for 30 days | ✓ Does not train |
| DeepSeek | Prompts are retained for unknown period | ✕ May train |
| Enfer | Unknown retention policy | ✓ Does not train |
| Featherless | Zero retention | ✓ Does not train |
| Friendli | Prompts are retained for unknown period | ✓ Does not train |
| OpenAI | Prompts are retained for unknown period | ✓ Does not train |
| OpenInference | Prompts are retained for unknown period | ✕ May train |
| Nebius AI Studio | Zero retention | ✓ Does not train |
| Groq | Zero retention | ✓ Does not train |
| Hyperbolic | Unknown retention policy | ✓ Does not train |
| Inception | Zero retention | ✓ Does not train |
| inference.net | Unknown retention policy | ✓ Does not train |
| Lambda | Unknown retention policy | ✓ Does not train |
| Liquid | Unknown retention policy | ✓ Does not train |
| Mancer (private) | Zero retention | ✓ Does not train |
| Minimax | Unknown retention policy | ✓ Does not train |
| nCompass | Unknown retention policy | ✓ Does not train |
| Stealth | Prompts are retained for unknown period | ✕ May train |
| Crusoe | Unknown retention policy | ✓ Does not train |
| Inflection | Retained for 30 days | ✓ Does not train |
| Chutes | Prompts are retained for unknown period | ✕ May train |
| DeepInfra | Zero retention | ✓ Does not train |
| CrofAI | Unknown retention policy | ✓ Does not train |
| AI21 | Unknown retention policy | ✓ Does not train |
| Alibaba | Unknown retention policy | ✓ Does not train |
| Amazon Bedrock | Zero retention | ✓ Does not train |
| Anthropic | Retained for 30 days | ✓ Does not train |
| Google Vertex | Retained for 1 days | ✓ Does not train |
| Google Vertex (free) | Prompts are retained for unknown period | ✕ May train |
| Fireworks | Zero retention | ✓ Does not train |
| NovitaAI | Unknown retention policy | ✓ Does not train |
| NextBit | Zero retention | ✓ Does not train |
| Nineteen | Unknown retention policy | ✓ Does not train |
| Baseten | Zero retention | ✓ Does not train |
| Cerebras | Zero retention | ✓ Does not train |
| GMICloud | Unknown retention policy | ✓ Does not train |
| Parasail | Prompts are retained for unknown period | ✓ Does not train |
| Perplexity | Unknown retention policy | ✓ Does not train |
| Phala | Zero retention | ✓ Does not train |
| SambaNova | Zero retention | ✓ Does not train |
| Ubicloud | Unknown retention policy | ✓ Does not train |
| Venice | Zero retention | ✓ Does not train |
| xAI | Retained for 30 days | ✓ Does not train |
| Meta | Retained for 30 days | ✓ Does not train |
| kluster.ai | Zero retention | ✓ Does not train |
| Targon | Prompts are retained for unknown period | ✕ May train |
| Infermatic | Zero retention | ✓ Does not train |
| Morph | Zero retention | ✓ Does not train |
| Google AI Studio | Retained for 55 days | ✓ Does not train |
| Google AI Studio (free) | Retained for 55 days | ✕ May train |
| Together | Zero retention | ✓ Does not train |
| Switchpoint | Unknown retention policy | ✓ Does not train |