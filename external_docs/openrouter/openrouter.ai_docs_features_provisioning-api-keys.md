---
url: "https://openrouter.ai/docs/features/provisioning-api-keys"
title: "Provisioning API Keys | Programmatic Control of OpenRouter API Keys | OpenRouter | Documentation"
---

OpenRouter provides endpoints to programmatically manage your API keys, enabling key creation and management for applications that need to distribute or rotate keys automatically.

## Creating a Provisioning API Key

To use the key management API, you first need to create a Provisioning API key:

1. Go to the [Provisioning API Keys page](https://openrouter.ai/settings/provisioning-keys)
2. Click “Create New Key”
3. Complete the key creation process

Provisioning keys cannot be used to make API calls to OpenRouter’s completion endpoints - they are exclusively for key management operations.

## Use Cases

Common scenarios for programmatic key management include:

- **SaaS Applications**: Automatically create unique API keys for each customer instance
- **Key Rotation**: Regularly rotate API keys for security compliance
- **Usage Monitoring**: Track key usage and automatically disable keys that exceed limits

## Example Usage

All key management endpoints are under `/api/v1/keys` and require a Provisioning API key in the Authorization header.

PythonTypeScript

```code-block text-sm

1import requests23PROVISIONING_API_KEY = "your-provisioning-key"4BASE_URL = "https://openrouter.ai/api/v1/keys"56# List the most recent 100 API keys7response = requests.get(8    BASE_URL,9    headers={10        "Authorization": f"Bearer {PROVISIONING_API_KEY}",11        "Content-Type": "application/json"12    }13)1415# You can paginate using the offset parameter16response = requests.get(17    f"{BASE_URL}?offset=100",18    headers={19        "Authorization": f"Bearer {PROVISIONING_API_KEY}",20        "Content-Type": "application/json"21    }22)2324# Create a new API key25response = requests.post(26    f"{BASE_URL}/",27    headers={28        "Authorization": f"Bearer {PROVISIONING_API_KEY}",29        "Content-Type": "application/json"30    },31    json={32        "name": "Customer Instance Key",33        "label": "customer-123",34        "limit": 1000  # Optional credit limit35    }36)3738# Get a specific key39key_hash = "<YOUR_KEY_HASH>"40response = requests.get(41    f"{BASE_URL}/{key_hash}",42    headers={43        "Authorization": f"Bearer {PROVISIONING_API_KEY}",44        "Content-Type": "application/json"45    }46)4748# Update a key49response = requests.patch(50    f"{BASE_URL}/{key_hash}",51    headers={52        "Authorization": f"Bearer {PROVISIONING_API_KEY}",53        "Content-Type": "application/json"54    },55    json={56        "name": "Updated Key Name",57        "disabled": True,  # Disable the key58        "include_byok_in_limit": False  # Optional: control BYOK usage in limit59    }60)6162# Delete a key63response = requests.delete(64    f"{BASE_URL}/{key_hash}",65    headers={66        "Authorization": f"Bearer {PROVISIONING_API_KEY}",67        "Content-Type": "application/json"68    }69)

```

## Response Format

API responses return JSON objects containing key information:

```code-block text-sm

1{2  "data": [3    {4      "created_at": "2025-02-19T20:52:27.363244+00:00",5      "updated_at": "2025-02-19T21:24:11.708154+00:00",6      "hash": "<YOUR_KEY_HASH>",7      "label": "sk-or-v1-customkey",8      "name": "Customer Key",9      "disabled": false,10      "limit": 10,11      "usage": 012    }13  ]14}
```

When creating a new key, the response will include the key string itself.