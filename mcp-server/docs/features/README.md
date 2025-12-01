# Features Documentation

> Consolidated feature reference for the Nessus MCP Server

---

## Contents

- [FEATURES.md](./FEATURES.md) - Complete feature catalog with all capabilities

---

## Feature Categories

### MCP Tools (API)
- Scan submission (untrusted, authenticated)
- Status and monitoring
- Scanner management
- Results retrieval with filtering

### Scanner Integration
- Native async Nessus API client
- Multi-instance registry with pools
- Credential injection for authenticated scans
- Result validation with auth detection

### Queue & Task Management
- Redis-backed FIFO queue
- State machine with enforced transitions
- Idempotency for duplicate prevention
- Background worker processing

### Results Processing
- XML to JSON-NL transformation
- 4 schema profiles (minimal to full)
- Type-aware filtering engine
- Pagination support

### Observability
- Structured JSON logging
- Prometheus metrics (8 core + pool metrics)
- Health check endpoints

### Production Features
- Pool-based scanner isolation
- Load-based scanner selection
- Circuit breaker protection
- TTL housekeeping
- DLQ management CLI

---

## Quick Reference

See [FEATURES.md](./FEATURES.md) for detailed documentation of each feature including:
- Parameter specifications
- Response formats
- Configuration options
- Implementation status
