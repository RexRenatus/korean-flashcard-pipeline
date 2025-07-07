---
url: "https://openrouter.ai/docs/api-reference/list-available-models"
title: "List available models | OpenRouter | Documentation"
---

Returns a list of models available through the API.
Note: `supported_parameters` is a union of all parameters supported by all providers for this model.
There may not be a single provider which offers all of the listed parameters for a model.
More documentation available [here](https://openrouter.ai/docs/models).

### Query parameters

categorystringOptional

Filter models by category (e.g. programming). Sorted from most to least used.

use\_rssbooleanOptionalDefaults to `false`

Return RSS XML feed instead of JSON (BETA)

use\_rss\_chat\_linksbooleanOptionalDefaults to `false`

Use chat URLs instead of model page URLs for RSS items (only applies when use\_rss=true) (BETA)

### Response

List of available models

datalist of objects

Show 12 properties