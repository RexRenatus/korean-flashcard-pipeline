---
url: "https://docs.anthropic.com/en/api/service-tiers"
title: "Service tiers - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Using the APIs

Service tiers

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

We offer three service tiers:

- **Priority Tier:** Best for workflows deployed in production where time, availability, and predictable pricing are important
- **Standard:** Best for bursty traffic, or for when you’re trying a new idea
- **Batch:** Best for asynchronous workflows which can wait or benefit from being outside your normal capacity

## [​](https://docs.anthropic.com/en/api/service-tiers\#standard-tier)  Standard Tier

The standard tier is the default service tier for all API requests. Requests in this tier are prioritized alongside all other requests and observe best-effort availability.

## [​](https://docs.anthropic.com/en/api/service-tiers\#priority-tier)  Priority Tier

Requests in this tier are prioritized over all other requests to Anthropic. This prioritization helps minimize [“server overloaded” errors](https://docs.anthropic.com/en/api/errors#http-errors), even during peak times.

For more information, see [Get started with Priority Tier](https://docs.anthropic.com/en/api/service-tiers#get-started-with-priority-tier)

## [​](https://docs.anthropic.com/en/api/service-tiers\#how-requests-get-assigned-tiers)  How requests get assigned tiers

When handling a request, Anthropic decides to assign a request to Priority Tier in the following scenarios:

- Your organization has sufficient priority tier capacity **input** tokens per minute
- Your organization has sufficient priority tier capacity **output** tokens per minute

Anthropic counts usage against Priority Tier capacity as follows:

**Input Tokens**

- Cache reads as 0.1 tokens per token read from the cache
- Cache writes as 1.25 tokens per token written to the cache with a 5 minute TTL
- Cache writes as 2.00 tokens per token written to the cache with a 1 hour TTL
- All other input tokens are 1 token per token

**Output Tokens**

- 1 token per token

Otherwise, requests proceed at standard tier.

Requests assigned Priority Tier pull from both the Priority Tier capacity and the regular rate limits.
If servicing the request would exceed the rate limits, the request is declined.

## [​](https://docs.anthropic.com/en/api/service-tiers\#using-service-tiers)  Using service tiers

You can control which service tiers can be used for a request by setting the `service_tier` parameter:

Copy

```python
message = client.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude!"}],
    service_tier="auto"  # Automatically use Priority Tier when available, fallback to standard
)

```

The `service_tier` parameter accepts the following values:

- `"auto"` (default) - Uses the Priority Tier capacity if available, falling back to your other capacity if not
- `"standard_only"` \- Only use standard tier capacity, useful if you don’t want to use your Priority Tier capacity

The response `usage` object also includes the service tier assigned to the request:

Copy

```json
{
  "usage": {
    "input_tokens": 410,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "output_tokens": 585,
    "service_tier": "priority"
  }
}

```

This allows you to determine which service tier was assigned to the request.

When requesting `service_tier="auto"` with a model with a Priority Tier committment, these response headers provide insights:

Copy

```
anthropic-priority-input-tokens-limit: 10000
anthropic-priority-input-tokens-remaining: 9618
anthropic-priority-input-tokens-reset: 2025-01-12T23:11:59Z
anthropic-priority-output-tokens-limit: 10000
anthropic-priority-output-tokens-remaining: 6000
anthropic-priority-output-tokens-reset: 2025-01-12T23:12:21Z

```

You can use the presence of these headers to detect if your request was eligible for Priority Tier, even if it was over the limit.

## [​](https://docs.anthropic.com/en/api/service-tiers\#get-started-with-priority-tier)  Get started with Priority Tier

You may want to commit to Priority Tier capacity if you are interested in:

- **Higher availability**: Target 99.9% uptime with prioritized computational resources
- **Cost Control**: Predictable spend and discounts for longer commitments
- **Flexible overflow**: Automatically falls back to standard tier when you exceed your committed capacity

Committing to Priority Tier will involve deciding:

- A number of input tokens per minute
- A number of output tokens per minute
- A commitment duration (1, 3, 6, or 12 months)
- A specific model version

The ratio of input to output tokens you purchase matters. Sizing your Priority Tier capacity to align with your actual traffic patterns helps you maximize utilization of your purchased tokens.

### [​](https://docs.anthropic.com/en/api/service-tiers\#supported-models)  Supported models

Priority Tier is supported by:

- Claude Opus 4
- Claude Sonnet 4
- Claude Sonnet 3.7
- Claude Sonnet 3.5 (both versions)
- Claude Haiku 3.5

Check the [model overview page](https://docs.anthropic.com/en/docs/about-claude/models/overview) for more details on our models.

### [​](https://docs.anthropic.com/en/api/service-tiers\#how-to-access-priority-tier)  How to access Priority Tier

To begin using Priority Tier:

1. [Contact sales](https://www.anthropic.com/contact-sales/priority-tier) to complete provisioning
2. (Optional) Update your API requests to optionally set the `service_tier` parameter to `auto`
3. Monitor your usage through response headers and the Anthropic Console

Was this page helpful?

YesNo

[Rate limits](https://docs.anthropic.com/en/api/rate-limits) [Errors](https://docs.anthropic.com/en/api/errors)

On this page

- [Standard Tier](https://docs.anthropic.com/en/api/service-tiers#standard-tier)
- [Priority Tier](https://docs.anthropic.com/en/api/service-tiers#priority-tier)
- [How requests get assigned tiers](https://docs.anthropic.com/en/api/service-tiers#how-requests-get-assigned-tiers)
- [Using service tiers](https://docs.anthropic.com/en/api/service-tiers#using-service-tiers)
- [Get started with Priority Tier](https://docs.anthropic.com/en/api/service-tiers#get-started-with-priority-tier)
- [Supported models](https://docs.anthropic.com/en/api/service-tiers#supported-models)
- [How to access Priority Tier](https://docs.anthropic.com/en/api/service-tiers#how-to-access-priority-tier)