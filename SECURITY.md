# Security Policy

## Reporting a security issue

Please report suspected vulnerabilities privately. Use GitHub's **Report a vulnerability** option in this repository's Security tab if it is available. Otherwise, contact the maintainer privately through the repository owner's GitHub profile. Include the affected version, steps to reproduce, and potential impact. Do not post exploit details or credentials in a public issue.

## Protect your credentials

- Never commit an API key, including `JEV_API_KEY`, to this repository or paste one into an issue, log, or screenshot.
- Never commit a `.env` file. Keep your local `.env` private; `.env.example` is the public template and contains no key.
- If a key is exposed, revoke or rotate it with its provider and remove it from any shared configuration.

## MCP configuration

- Run the STDIO MCP server only from a trusted local checkout and Python environment. Review the configured `command`, `args`, and working directory before connecting a desktop client.
- Store MCP configuration files containing secrets privately. Prefer a local environment variable or private `.env` file for `JEV_API_KEY` rather than putting the key in a configuration file you may share.
- Grant the MCP connector access only to the tools and files it needs, and do not expose the local server to untrusted users.
