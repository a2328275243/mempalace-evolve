# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, please:

1. **Do NOT open a public issue** - this could expose the vulnerability to bad actors.
2. Email [security@dreamseed.dev] or use GitHub's **Private Vulnerability Reporting**.
3. Provide a detailed description, steps to reproduce, and potential impact.

We aim to respond within 48 hours and resolve critical issues within 7 days.

## Security Considerations for MemPalace Evolve

- **API Keys**: Never hardcode API keys. Use environment variables or the built-in key management.
- **Storage**: Memory data is stored locally in ChromaDB/SQLite. Ensure filesystem permissions are restrictive.
- **REST API**: When using `mempalace serve`, bind to localhost (default) unless you explicitly need remote access and have configured TLS.
- **Data Privacy**: Memories may contain sensitive information. Use `mempalace forget` to remove specific memories.
