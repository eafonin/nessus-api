# FastMCP Documentation Index

> Quick reference guide for developing MCP servers, clients, and HTTP transport integrations

This index helps you quickly find the right documentation for your task. Documentation is organized into Quick Start guides for common tasks, followed by comprehensive topic references.

---

## 🚀 Quick Start: Common Tasks

### Building a New MCP Server
1. **Start here**: [`server.md`](server.md) - Server basics, creating tools/resources/prompts
2. **Add functionality**: [`tools.md`](tools.md), [`resources.md`](resources.md), [`prompts.md`](prompts.md)
3. **Deploy**: [`deployment/http-deployment.md`](deployment/http-deployment.md) - Make server accessible over HTTP

### HTTP Transport Integration
1. **Deployment**: [`deployment/http-deployment.md`](deployment/http-deployment.md) - HTTP server setup, mounting, authentication
2. **Client connection**: [`clients/transports.md`](clients/transports.md) - Connecting to HTTP servers
3. **Authentication**: [`authentication/bearer.md`](authentication/bearer.md) - Securing HTTP endpoints

### Building an MCP Client
1. **Start here**: [`clients/client.md`](clients/client.md) - Client basics, connection lifecycle
2. **Transports**: [`clients/transports.md`](clients/transports.md) - HTTP, STDIO, in-memory connections
3. **Operations**: [`clients/tools.md`](clients/tools.md), [`clients/resources.md`](clients/resources.md), [`clients/prompts.md`](clients/prompts.md)

### Testing and Development
1. **Testing**: [`patterns/testing.md`](patterns/testing.md) - Writing tests for servers
2. **CLI tools**: [`patterns/cli.md`](patterns/cli.md) - Command-line interface development

### Organizing Workflows
1. **Server composition**: [`advanced/composition.md`](advanced/composition.md) - Combining multiple servers
2. **Middleware**: [`advanced/middleware.md`](advanced/middleware.md) - Request/response processing
3. **Storage**: [`advanced/storage-backends.md`](advanced/storage-backends.md) - Data persistence

---

## 📚 Detailed Topic Reference

### Server Core Components

#### `server.md`
**Summary**: Core FastMCP server class for building MCP applications with tools, resources, and prompts
**Key Topics**: Server creation, components (tools/resources/prompts), tag filtering, running servers, custom routes, composition, proxying, OpenAPI integration, configuration
**Keywords**: FastMCP, server creation, mcp.tool, mcp.resource, mcp.prompt, tag filtering, server composition, custom routes

#### `tools.md`
**Summary**: Expose functions as executable capabilities for MCP clients
**Key Topics**: @tool decorator, arguments, type annotations, return values, structured outputs, output schemas, error handling, disabling tools, MCP annotations, notifications
**Keywords**: tools, @tool decorator, function execution, parameters, validation, structured content, output schema, error handling, annotations

#### `resources.md`
**Summary**: Expose data sources and dynamic content generators to MCP clients
**Key Topics**: @resource decorator, static resources, resource templates, URI templates, return values, RFC 6570, query parameters, error handling, notifications
**Keywords**: resources, @resource decorator, data sources, URI templates, resource templates, parameterized resources, query parameters

#### `prompts.md`
**Summary**: Create reusable, parameterized prompt templates for MCP clients
**Key Topics**: @prompt decorator, argument types, return values, message templates, required vs optional parameters, disabling prompts, async prompts
**Keywords**: prompts, @prompt decorator, message templates, LLM prompts, prompt arguments, PromptMessage

### Advanced Server Features

#### `advanced/composition.md`
**Summary**: Combine multiple FastMCP servers into a single application using mounting and importing
**Key Topics**: import_server (static), mount (dynamic), prefixing, conflict resolution, tag filtering with composition, resource prefix formats, performance
**Keywords**: server composition, mount, import_server, multi-server, modular servers, prefix, tag filtering

#### `advanced/context.md`
**Summary**: Access MCP capabilities like logging, progress, and resources within MCP objects
**Key Topics**: Context object, dependency injection, logging, progress reporting, resource access, LLM sampling, state management, request information
**Keywords**: Context, ctx, dependency injection, logging, progress, sampling, state management, get_context

#### `advanced/server-elicitation.md`
**Summary**: Request structured input from users during tool execution through MCP context
**Key Topics**: Elicitation, ctx.elicit(), scalar types, constrained options, structured responses, multi-turn elicitation, ElicitationResult
**Keywords**: elicitation, user input, interactive tools, ctx.elicit, structured input, dataclass responses

#### `advanced/icons.md`
**Summary**: Add visual icons to servers, tools, resources, and prompts
**Key Topics**: Icon format, server icons, component icons, data URIs, MCP Icon type
**Keywords**: icons, visual representation, images, MCP Icon, data URI, SVG

#### `advanced/server-logging.md`
**Summary**: Send log messages back to MCP clients through the context
**Key Topics**: Logging methods (debug/info/warning/error), structured logging with extra, server logs, log levels
**Keywords**: logging, ctx.debug, ctx.info, ctx.warning, ctx.error, structured logs, extra data

#### `advanced/middleware.md`
**Summary**: Add cross-cutting functionality to MCP server with middleware
**Key Topics**: Middleware hooks, on_message, on_request, on_call_tool, component access, tool denial, timing, caching, rate limiting, error handling
**Keywords**: middleware, hooks, request processing, on_call_tool, on_read_resource, caching, rate limiting

#### `advanced/server-progress.md`
**Summary**: Update clients on progress of long-running operations through MCP context
**Key Topics**: ctx.report_progress(), percentage-based progress, absolute progress, indeterminate progress, multi-stage operations
**Keywords**: progress, ctx.report_progress, long-running operations, progress indicators, multi-stage

#### `advanced/server-sampling.md`
**Summary**: Request LLM text generation from client or configured provider through MCP context
**Key Topics**: ctx.sample(), sampling handler, model preferences, system prompts, fallback handler, sampling behavior
**Keywords**: sampling, LLM requests, ctx.sample, text generation, model preferences, sampling handler

#### `advanced/storage-backends.md`
**Summary**: Configure persistent and distributed storage for caching and OAuth state management
**Key Topics**: In-memory storage, disk storage, Redis, py-key-value-aio, OAuth token storage, response caching
**Keywords**: storage, caching, persistence, Redis, disk storage, OAuth tokens, key-value store

### Deployment

#### `deployment/http-deployment.md`
**Summary**: Deploy FastMCP server over HTTP for remote access
**Key Topics**: HTTP server approach, ASGI application, custom paths, authentication, health checks, CORS, mounting, production deployment, OAuth token security
**Keywords**: HTTP deployment, remote server, ASGI, Uvicorn, authentication, CORS, production, OAuth mounting

#### `deployment/server-configuration.md`
**Summary**: Use fastmcp.json for portable, declarative project configuration
**Key Topics**: Configuration file structure, source configuration, environment configuration, deployment configuration, CLI usage, environment variables
**Keywords**: fastmcp.json, configuration, declarative config, environment setup, dependencies, deployment settings

### Clients

#### `clients/client.md`
**Summary**: Programmatic client for interacting with MCP servers through well-typed interface
**Key Topics**: Client creation, transport inference, connection lifecycle, operations (tools/resources/prompts), configuration, callback handlers
**Keywords**: Client, FastMCP Client, programmatic access, transport, connection, callbacks

#### `clients/transports.md`
**Summary**: Configure how FastMCP Clients connect to and communicate with servers
**Key Topics**: STDIO transport, remote transports (HTTP/SSE), in-memory transport, MCP JSON configuration, environment isolation, session persistence
**Keywords**: transport, STDIO, HTTP, SSE, connection, environment variables, StreamableHttpTransport

#### `clients/tools.md`
**Summary**: Discover and execute server-side tools with FastMCP client
**Key Topics**: list_tools(), call_tool(), CallToolResult, structured data access, .data property, error handling, primitive unwrapping
**Keywords**: call_tool, list_tools, tool execution, CallToolResult, structured output, deserialization

#### `clients/resources.md`
**Summary**: Access static and templated resources from MCP servers
**Key Topics**: list_resources(), list_resource_templates(), read_resource(), text resources, binary resources, multi-server clients
**Keywords**: read_resource, list_resources, resource templates, URI, text content, binary content

#### `clients/prompts.md`
**Summary**: Use server-side prompt templates with automatic argument serialization
**Key Topics**: list_prompts(), get_prompt(), automatic serialization, complex arguments, GetPromptResult, multi-server clients
**Keywords**: get_prompt, list_prompts, prompt templates, argument serialization, messages

#### `clients/client-elicitation.md`
**Summary**: Handle server-initiated user input requests with structured schemas
**Key Topics**: Elicitation handler, response_type, ElicitResult, action types (accept/decline/cancel), dataclass conversion
**Keywords**: elicitation handler, user input, response handling, ElicitResult, structured responses

#### `clients/client-logging.md`
**Summary**: Receive and handle log messages from MCP servers
**Key Topics**: log_handler, LogMessage, structured logs, logging integration, default log handling
**Keywords**: log_handler, LogMessage, server logs, logging integration, structured logging

#### `clients/client-progress.md`
**Summary**: Handle progress notifications from long-running server operations
**Key Topics**: progress_handler, per-call progress handler, progress monitoring
**Keywords**: progress_handler, progress monitoring, long-running operations, progress notifications

#### `clients/client-sampling.md`
**Summary**: Handle server-initiated LLM sampling requests
**Key Topics**: sampling_handler, SamplingMessage, SamplingParams, model preferences, system prompt, include context
**Keywords**: sampling_handler, LLM sampling, SamplingMessage, model preferences, text generation

#### `clients/client-messages.md`
**Summary**: Handle MCP messages, requests, and notifications with custom message handlers
**Key Topics**: MessageHandler class, on_tool_list_changed, on_resource_list_changed, on_prompt_list_changed, notification handling
**Keywords**: message_handler, MessageHandler, notifications, list_changed, event handling

#### `clients/roots.md`
**Summary**: Provide local context and resource boundaries to MCP servers
**Key Topics**: Static roots, dynamic roots callback, RequestContext
**Keywords**: roots, client context, resource boundaries, roots callback

### Authentication

#### `authentication/bearer.md`
**Summary**: Authenticate FastMCP client with Bearer token
**Key Topics**: BearerAuth, token authentication, Authorization header, custom headers, httpx.Auth
**Keywords**: Bearer token, authentication, Authorization header, BearerAuth, JWT, access token

### Integrations

#### `integrations/chatgpt.md`
**Summary**: Connect FastMCP servers to ChatGPT in Chat and Deep Research modes
**Key Topics**: Chat mode, Deep Research mode, Developer Mode, search/fetch tools, connector setup, skip confirmations
**Keywords**: ChatGPT, OpenAI, Chat mode, Deep Research, search tools, fetch tools, readOnlyHint

#### `integrations/mcp-json-configuration.md`
**Summary**: Generate standard MCP configuration files for any compatible client
**Key Topics**: MCP JSON standard, mcpServers format, command/args/env fields, fastmcp install mcp-json, clipboard integration
**Keywords**: MCP JSON, mcpServers, configuration, command, args, env, install

#### `integrations/openai.md`
**Summary**: Connect FastMCP servers to OpenAI API
**Key Topics**: Responses API, MCP connector, tool integration, authentication with OpenAI, JWT tokens
**Keywords**: OpenAI, Responses API, MCP connector, tools, authentication, JWT

#### `integrations/anthropic.md`
**Summary**: Connect FastMCP servers to Anthropic API
**Key Topics**: Messages API, MCP connector, tool integration, authentication, mcp_servers parameter
**Keywords**: Anthropic, Messages API, Claude, MCP connector, authentication, mcp_servers

#### `integrations/fastapi.md`
**Summary**: Integrate FastMCP with FastAPI applications
**Key Topics**: from_fastapi(), mounting MCP server, route mapping, authentication, combining APIs, lifespan management
**Keywords**: FastAPI, OpenAPI, from_fastapi, mounting, ASGI, route maps, lifespan

### Patterns & Best Practices

#### `patterns/tool-transformation.md`
**Summary**: Create enhanced tool variants with modified schemas, argument mappings, and custom behavior
**Key Topics**: Tool.from_tool(), ArgTransform, hiding arguments, renaming, default values, transform_fn, forward(), exposing client methods
**Keywords**: tool transformation, ArgTransform, from_tool, hiding arguments, default values, transform_fn, forward

#### `patterns/decorating-methods.md`
**Summary**: Properly use instance methods, class methods, and static methods with FastMCP decorators
**Key Topics**: Instance methods, class methods, static methods, decorator order, bound methods, registration patterns
**Keywords**: methods, decorators, instance methods, class methods, static methods, bound methods

#### `patterns/cli.md`
**Summary**: Learn how to use the FastMCP command-line interface
**Key Topics**: fastmcp run, fastmcp dev, fastmcp install, fastmcp inspect, entrypoints, factory functions, configuration files
**Keywords**: CLI, command-line, fastmcp run, fastmcp dev, fastmcp install, fastmcp inspect, MCP Inspector

#### `patterns/testing.md`
**Summary**: Testing FastMCP servers with pytest and inline snapshots
**Key Topics**: Pytest fixtures, Client usage in tests, inline-snapshot, parametrize, testing tools/resources/prompts
**Keywords**: testing, pytest, fixtures, Client, inline-snapshot, unit tests, integration tests

---

## 🔍 Search Tips

**Looking for HTTP deployment?** → [`deployment/http-deployment.md`](deployment/http-deployment.md)

**Need to authenticate?** → [`authentication/bearer.md`](authentication/bearer.md) or [`deployment/http-deployment.md`](deployment/http-deployment.md#authentication)

**Building tools/resources?** → [`tools.md`](tools.md), [`resources.md`](resources.md)

**Client connection issues?** → [`clients/transports.md`](clients/transports.md)

**Want to combine servers?** → [`advanced/composition.md`](advanced/composition.md)

**Need caching or storage?** → [`advanced/storage-backends.md`](advanced/storage-backends.md)

**Working with FastAPI?** → [`integrations/fastapi.md`](integrations/fastapi.md)

**Testing servers?** → [`patterns/testing.md`](patterns/testing.md)

---

## 📋 File Organization

```
docs/fastMCPServer/
├── INDEX.md (this file)
│
├── Core Server
│   ├── server.md
│   ├── tools.md
│   ├── resources.md
│   └── prompts.md
│
├── advanced/
│   ├── composition.md
│   ├── context.md
│   ├── server-elicitation.md
│   ├── icons.md
│   ├── server-logging.md
│   ├── middleware.md
│   ├── server-progress.md
│   ├── server-sampling.md
│   └── storage-backends.md
│
├── deployment/
│   ├── http-deployment.md
│   └── server-configuration.md
│
├── clients/
│   ├── client.md
│   ├── transports.md
│   ├── tools.md
│   ├── resources.md
│   ├── prompts.md
│   ├── client-elicitation.md
│   ├── client-logging.md
│   ├── client-progress.md
│   ├── client-sampling.md
│   ├── client-messages.md
│   └── roots.md
│
├── authentication/
│   └── bearer.md
│
├── integrations/
│   ├── chatgpt.md
│   ├── mcp-json-configuration.md
│   ├── openai.md
│   ├── anthropic.md
│   └── fastapi.md
│
└── patterns/
    ├── tool-transformation.md
    ├── decorating-methods.md
    ├── cli.md
    └── testing.md
```
