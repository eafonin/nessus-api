# Client Examples

> Progressive examples demonstrating NessusFastMCPClient usage

## Prerequisites

- MCP server running at `http://localhost:8835/mcp`
- Scanner worker running
- Nessus scanner accessible

## Example Progression

| Example | Complexity | Duration | Focus |
|---------|------------|----------|-------|
| `01_basic_usage.py` | Basic | ~5s | Connect, submit, check status |
| `02_wait_for_completion.py` | Basic | ~5min | Polling until completion |
| `03_scan_and_wait.py` | Intermediate | ~5min | Combined workflow |
| `04_get_critical_vulns.py` | Intermediate | ~5min | Result filtering |
| `05_full_workflow.py` | Advanced | ~10min | Complete production workflow |
| `06_e2e_workflow_test.py` | Testing | ~10min | E2E test validation |

## Quick Start

```bash
cd mcp-server

# Run first example
python client/examples/01_basic_usage.py

# Continue with returned task_id
python client/examples/02_wait_for_completion.py <task_id>
```

## Example Details

### 01_basic_usage.py

Connect and submit scan:

```python
async with NessusFastMCPClient(url="...", debug=True) as client:
    await client.ping()
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
    status = await client.get_status(task["task_id"])
```

### 02_wait_for_completion.py

Poll until scan completes:

```python
status = await client.wait_for_completion(task_id, timeout=600)
# status["status"] == "completed"
```

### 03_scan_and_wait.py

Combined submit + wait:

```python
task = await client.submit_scan(...)
status = await client.wait_for_completion(task["task_id"])
```

### 04_get_critical_vulns.py

Filter results by severity:

```python
results = await client.get_results(
    task_id,
    schema_profile="brief",
    filters={"severity": "4"}  # Critical only
)
```

### 05_full_workflow.py

Production workflow with:
- Scanner pool selection
- Progress monitoring
- Result pagination
- Error handling

### 06_e2e_workflow_test.py

Automated E2E test:
- Validates complete workflow
- Asserts expected states
- Cleanup after test

## Running All Examples

```bash
# Sequential execution
for i in 01 02 03 04 05; do
    python client/examples/${i}_*.py
done
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8835/mcp` | MCP server endpoint |
