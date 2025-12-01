<!-- README Navigation -->
<!-- L3: dev1/logs/ -->
<!-- Parent: ../README.MD -->
<!-- Purpose: Application log storage (currently unused) -->

# Logs Directory

> Application log storage (currently unused)

**↑ Parent**: [Development Environment](../README.MD) | **↑↑ Root**: [Nessus MCP Server](../../README.MD)

## Status

This directory is reserved for application logs but is **currently unused**. All service logs are output to stdout/stderr for Docker log aggregation.

## Viewing Logs

Use Docker Compose to view service logs:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f mcp-api
docker compose logs -f scanner-worker
docker compose logs -f redis
```

## Volume Mount

This directory is mounted into containers:

```yaml
# dev1/docker-compose.yml
volumes:
  - ./logs:/app/logs
```

## Future Use

This directory may be used for:
- File-based log rotation
- Structured log files (JSON)
- Audit logs
- Debug dumps

## See Also

- [Development Environment](../README.MD) - Parent directory documentation
- [Logging Configuration](../../mcp-server/core/README.MD#logging) - Logging setup
