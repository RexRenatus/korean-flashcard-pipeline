---
url: "https://docs.anthropic.com/en/api/beta-headers"
title: "Beta headers - Anthropic"
---

[Anthropic home page![light logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/light.svg)![dark logo](https://mintlify.s3.us-west-1.amazonaws.com/anthropic/logo/dark.svg)](https://docs.anthropic.com/)

English

Search...

Ctrl K

Search...

Navigation

Using the APIs

Beta headers

[Welcome](https://docs.anthropic.com/en/home) [Developer Guide](https://docs.anthropic.com/en/docs/intro) [API Guide](https://docs.anthropic.com/en/api/overview) [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/mcp) [Resources](https://docs.anthropic.com/en/resources/overview) [Release Notes](https://docs.anthropic.com/en/release-notes/overview)

Beta headers allow you to access experimental features and new model capabilities before they become part of the standard API.

These features are subject to change and may be modified or removed in future releases.

Beta headers are often used in conjunction with the [beta namespace in the client SDKs](https://docs.anthropic.com/en/api/client-sdks#beta-namespace-in-client-sdks)

## [​](https://docs.anthropic.com/en/api/beta-headers\#how-to-use-beta-headers)  How to use beta headers

To access beta features, include the `anthropic-beta` header in your API requests:

Copy

```http
POST /v1/messages

```

When using the SDK, you can specify beta headers in the request options:

Python

TypeScript

cURL

Copy

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[\
        {"role": "user", "content": "Hello, Claude"}\
    ],
    extra_headers={
        "anthropic-beta": "beta-feature-name"
    }
)

```

Beta features are experimental and may:

- Have breaking changes without notice
- Be deprecated or removed
- Have different rate limits or pricing
- Not be available in all regions

### [​](https://docs.anthropic.com/en/api/beta-headers\#multiple-beta-features)  Multiple beta features

To use multiple beta features in a single request, include all feature names in the header separated by commas:

Copy

```http

```

### [​](https://docs.anthropic.com/en/api/beta-headers\#version-naming-conventions)  Version naming conventions

Beta feature names typically follow the pattern: `feature-name-YYYY-MM-DD`, where the date indicates when the beta version was released. Always use the exact beta feature name as documented.

## [​](https://docs.anthropic.com/en/api/beta-headers\#error-handling)  Error handling

If you use an invalid or unavailable beta header, you’ll receive an error response:

Copy

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Unsupported beta header: invalid-beta-name"
  }
}

```

## [​](https://docs.anthropic.com/en/api/beta-headers\#getting-help)  Getting help

For questions about beta features:

1. Check the documentation for the specific feature
2. Review the [API changelog](https://docs.anthropic.com/en/api/versioning) for updates
3. Contact support for assistance with production usage

Remember that beta features are provided “as-is” and may not have the same SLA guarantees as stable API features.

Was this page helpful?

YesNo

[Handling stop reasons](https://docs.anthropic.com/en/api/handling-stop-reasons) [Messages](https://docs.anthropic.com/en/api/messages)

On this page

- [How to use beta headers](https://docs.anthropic.com/en/api/beta-headers#how-to-use-beta-headers)
- [Multiple beta features](https://docs.anthropic.com/en/api/beta-headers#multiple-beta-features)
- [Version naming conventions](https://docs.anthropic.com/en/api/beta-headers#version-naming-conventions)
- [Error handling](https://docs.anthropic.com/en/api/beta-headers#error-handling)
- [Getting help](https://docs.anthropic.com/en/api/beta-headers#getting-help)