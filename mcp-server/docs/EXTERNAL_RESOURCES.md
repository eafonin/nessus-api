# External Resources

> External documentation and resources for Nessus MCP Server development

## Framework Documentation

- **FastMCP Framework**: https://github.com/jlowin/fastmcp
  - Python framework for building MCP servers
  - Used for all MCP tool definitions and server implementation

- **MCP Protocol Spec**: https://spec.modelcontextprotocol.io/
  - Official Model Context Protocol specification
  - Defines tool calling, resources, and prompts

## Scanner APIs

- **Nessus API Docs**: https://developer.tenable.com/reference/navigate
  - Tenable Nessus REST API reference
  - Authentication, scan management, export endpoints

- **Tenable Developer Portal**: https://developer.tenable.com/
  - SDKs, guides, and API documentation

## Infrastructure

- **Redis Documentation**: https://redis.io/docs/
  - Queue implementation reference
  - Data structures and commands

- **Prometheus Python Client**: https://github.com/prometheus/client_python
  - Metrics instrumentation library
  - Counter, Gauge, Histogram types

## Python Libraries

- **httpx**: https://www.python-httpx.org/
  - Async HTTP client used by scanner implementations

- **structlog**: https://www.structlog.org/
  - Structured logging library

- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
  - Async test support

## Docker

- **Docker Compose Spec**: https://docs.docker.com/compose/compose-file/
  - Service definition reference

- **Multi-stage Builds**: https://docs.docker.com/build/building/multi-stage/
  - Production image optimization
