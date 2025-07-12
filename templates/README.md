# Templates Directory

This directory contains templates for various outputs and configurations in the flashcard pipeline system.

## Overview

Templates provide consistent formatting for:
- Export file formats
- Configuration examples
- Prompt templates
- Report layouts
- Email notifications

## Directory Structure

```
templates/
├── export/              # Export format templates
│   ├── anki.html       # Anki card template
│   ├── csv_header.txt  # CSV export header
│   ├── markdown.md     # Markdown template
│   └── json_schema.json # JSON structure
├── prompts/            # AI prompt templates
│   ├── flashcard_generation.txt
│   ├── semantic_analysis.txt
│   └── difficulty_assessment.txt
├── config/             # Configuration templates
│   ├── config.yaml.template
│   ├── .env.template
│   └── docker-compose.template.yml
├── reports/            # Report templates
│   ├── daily_summary.html
│   ├── error_report.txt
│   └── performance_report.md
└── emails/             # Email templates
    ├── welcome.html
    ├── error_notification.txt
    └── completion_notice.html
```

## Template Types

### Export Templates

#### Anki Card Template (`export/anki.html`)
```html
<div class="card">
  <div class="front">
    <div class="korean">{{Korean}}</div>
    <div class="type">{{Type}}</div>
  </div>
  <div class="back">
    <div class="english">{{English}}</div>
    <div class="romanization">{{Romanization}}</div>
    <div class="examples">{{Examples}}</div>
    <div class="notes">{{Notes}}</div>
  </div>
</div>

<style>
.card {
  font-family: Arial, sans-serif;
  text-align: center;
  padding: 20px;
}
.korean {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 10px;
}
.english {
  font-size: 24px;
  margin-bottom: 15px;
}
.romanization {
  font-style: italic;
  color: #666;
}
</style>
```

#### CSV Export Template (`export/csv_header.txt`)
```
korean,english,romanization,type,difficulty,tags,examples,notes,created_date
```

### Prompt Templates

#### Flashcard Generation (`prompts/flashcard_generation.txt`)
```
You are creating a Korean language flashcard for a {{difficulty_level}} learner.

Vocabulary Item:
- Korean: {{korean}}
- English: {{english}}
- Type: {{type}}

Please generate a comprehensive flashcard with:
1. Clear, concise English meaning
2. Romanization with pronunciation guide
3. Common usage example with translation
4. Grammar notes if applicable
5. Cultural context when relevant
6. Memory aids or mnemonics

Format the response as JSON with these fields:
- front: The Korean term
- back: Complete learning information
- examples: Array of example sentences
- tags: Relevant tags for categorization
- difficulty: 1-10 scale
```

### Configuration Templates

#### Application Config (`config/config.yaml.template`)
```yaml
# Flashcard Pipeline Configuration Template
# Copy to config.yaml and customize

api:
  provider: openrouter
  model: anthropic/claude-3-sonnet
  api_key: ${OPENROUTER_API_KEY}  # Set via environment
  timeout: 30
  max_retries: 3
  rate_limit: 60  # requests per minute

processing:
  batch_size: 50
  max_concurrent: 10
  cache_enabled: true
  cache_ttl: 86400  # 24 hours in seconds

database:
  path: ./flashcards.db
  backup_enabled: true
  backup_schedule: "0 3 * * *"  # Daily at 3 AM

output:
  default_format: json
  directory: ./output
  filename_pattern: "flashcards_{date}_{time}"
  
logging:
  level: INFO
  file: ./logs/flashcard.log
  max_size: 10485760  # 10MB
  backup_count: 5

features:
  auto_romanization: true
  difficulty_detection: true
  example_generation: true
  spaced_repetition: false
```

#### Environment Template (`config/.env.template`)
```bash
# API Configuration
OPENROUTER_API_KEY=your_api_key_here

# Database
DATABASE_URL=sqlite:///flashcards.db

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Features
ENABLE_CACHE=true
CACHE_REDIS_URL=redis://localhost:6379

# Monitoring
SENTRY_DSN=
PROMETHEUS_PORT=9090
```

### Report Templates

#### Daily Summary (`reports/daily_summary.html`)
```html
<!DOCTYPE html>
<html>
<head>
    <title>Daily Flashcard Summary - {{date}}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ddd; }
        .metric .value { font-size: 24px; font-weight: bold; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    </style>
</head>
<body>
    <h1>Daily Summary - {{date}}</h1>
    
    <div class="metrics">
        <div class="metric">
            <div class="label">Total Processed</div>
            <div class="value">{{total_processed}}</div>
        </div>
        <div class="metric">
            <div class="label">Success Rate</div>
            <div class="value">{{success_rate}}%</div>
        </div>
        <div class="metric">
            <div class="label">API Calls</div>
            <div class="value">{{api_calls}}</div>
        </div>
        <div class="metric">
            <div class="label">Cache Hit Rate</div>
            <div class="value">{{cache_hit_rate}}%</div>
        </div>
    </div>
    
    <h2>Processing Details</h2>
    <table>
        <tr>
            <th>Time</th>
            <th>Batch</th>
            <th>Items</th>
            <th>Duration</th>
            <th>Status</th>
        </tr>
        {{#each batches}}
        <tr>
            <td>{{this.time}}</td>
            <td>{{this.batch_id}}</td>
            <td>{{this.item_count}}</td>
            <td>{{this.duration}}s</td>
            <td>{{this.status}}</td>
        </tr>
        {{/each}}
    </table>
</body>
</html>
```

## Using Templates

### In Code
```python
from pathlib import Path
import jinja2

# Load template
template_dir = Path("templates")
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_dir)
)

# Render template
template = env.get_template("reports/daily_summary.html")
html = template.render(
    date="2024-01-09",
    total_processed=1250,
    success_rate=98.5,
    api_calls=125,
    cache_hit_rate=87.3,
    batches=batch_data
)

# Save report
with open("output/daily_summary.html", "w") as f:
    f.write(html)
```

### Template Variables
```python
# Common template variables
TEMPLATE_VARS = {
    "app_name": "Korean Flashcard Pipeline",
    "version": "1.0.0",
    "support_email": "support@example.com",
    "documentation_url": "https://docs.example.com"
}
```

## Best Practices

### Template Design
1. Keep templates simple and focused
2. Use meaningful variable names
3. Include comments for complex sections
4. Provide default values
5. Make templates customizable

### Variable Naming
```
Good: {{user_name}}, {{total_items}}, {{creation_date}}
Bad: {{un}}, {{t}}, {{d}}
```

### Escaping
```html
<!-- HTML templates -->
{{variable|e}}  <!-- Escape HTML -->

<!-- JSON templates -->
"{{variable|json}}"  <!-- JSON escape -->

<!-- SQL templates -->
'{{variable|sqlsafe}}'  <!-- SQL escape -->
```

## Customization

Users can customize templates by:
1. Copying template to user directory
2. Modifying as needed
3. Configuring app to use custom template

```python
# Support custom templates
custom_template = Path.home() / ".flashcards" / "templates" / "anki.html"
if custom_template.exists():
    template_path = custom_template
else:
    template_path = Path("templates") / "export" / "anki.html"
```

## DO NOT

- Hardcode values in templates
- Include sensitive information
- Make templates too complex
- Forget to escape user input
- Mix logic with presentation

## Template Testing

```python
# Test template rendering
def test_template_render():
    template = load_template("export/anki.html")
    data = {
        "Korean": "안녕하세요",
        "English": "Hello",
        "Type": "phrase"
    }
    result = template.render(data)
    assert "안녕하세요" in result
    assert "Hello" in result
```