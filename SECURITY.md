# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of the Korean Flashcard Pipeline seriously. If you have discovered a security vulnerability, please follow these steps:

### How to Report

1. **Do NOT** open a public issue
2. Email security concerns to: security@flashcard-pipeline.dev
3. Include the following information:
   - Type of vulnerability
   - Full paths of source file(s) related to the issue
   - Location of affected source code (tag/branch/commit or direct URL)
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the issue

### What to Expect

- Acknowledgment of your report within 48 hours
- Regular updates on our progress
- Credit for responsible disclosure (unless you prefer to remain anonymous)

### Security Best Practices

When using this application:

1. **API Keys**: 
   - Never commit API keys to version control
   - Use environment variables for all credentials
   - Rotate keys regularly

2. **Database Security**:
   - Keep SQLite database files secure
   - Don't expose database files via web servers
   - Use appropriate file permissions

3. **Input Validation**:
   - The application validates all user inputs
   - Report any bypasses immediately

4. **Dependencies**:
   - Keep all dependencies up to date
   - Monitor for security advisories
   - Use `pip-audit` for Python dependencies
   - Use `cargo audit` for Rust dependencies

## Security Features

The application includes:
- Input sanitization for all user data
- SQL injection prevention via parameterized queries
- Rate limiting to prevent API abuse
- Circuit breakers for fault tolerance
- Secure credential storage practices

## Known Security Considerations

- OpenRouter API keys must be kept secure
- Database contains processed text data - ensure compliance with data regulations
- Log files may contain sensitive information - secure appropriately

Thank you for helping keep the Korean Flashcard Pipeline secure!