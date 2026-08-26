# Security Policy

## Supported versions

Only the latest release published on [PyPI](https://pypi.org/project/solucortex-mcp/)
and the hosted endpoint at `https://mcp.solucortex.ai/mcp` are supported.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Email **pablo@soluai.cl** with:

- A description of the issue and its impact
- Steps to reproduce
- Any relevant logs (never include real API keys)

You will get an acknowledgement within 72 hours. Please allow us a reasonable window
to ship a fix before any public disclosure.

## Scope notes

- This server stores **no tenant credentials**: in remote mode your API key travels
  with each request and is never persisted or logged (only a SHA-256 fingerprint
  appears in logs).
- Issues in the SoluCortex backend (`solucortex.ai`) are also welcome through the
  same channel.
