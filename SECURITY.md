# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

MemPalace Evolve handles local memory data. If you discover a security vulnerability, please do NOT open a public issue.

Instead, send a description of the vulnerability to the project maintainers via GitHub Issues with the label `security`. We will acknowledge receipt within 48 hours and provide an estimated timeline for a fix.

Please include:
- Type of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Data Safety

MemPalace Evolve stores all data locally by default. No data is sent to external servers. The package does not phone home, collect telemetry, or require any cloud account.

## Best Practices

- Keep your mempalace database path (`~/.mempalace`) secure
- Do not store passwords, API keys, or secrets directly in memory content
- Review memory content before sharing your mempalace database with others
