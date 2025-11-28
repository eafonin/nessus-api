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

**What it demonstrates**:
- Connecting to MCP server
- Listing available tools
- Submitting a scan
- Checking scan status

**Usage**:

```bash
python client/examples/01_basic_usage.py
```

**Key Concepts**:
- `async with` context manager
- `submit_scan()` method
- `get_status()` method
- Basic error handling

**Output**:

```text
1. Pinging MCP server...
   ✓ Server is reachable

2. Listing available MCP tools...
   - run_untrusted_scan: Submit vulnerability scan
   - get_scan_status: Get scan task status
   ...

3. Submitting scan...
   ✓ Scan submitted: nessus-local-20251108-143022
   Status: queued
```

---

### 02_wait_for_completion.py

**What it demonstrates**:
- Polling scan status until completion
- Progress monitoring with callbacks
- Timeout handling
- Using existing task_id or submitting new scan

**Usage**:

```bash
# Wait for existing scan
python client/examples/02_wait_for_completion.py nessus-local-20251108-143022

# Or submit new scan and wait
python client/examples/02_wait_for_completion.py
```

**Key Concepts**:
- `wait_for_completion()` method
- Progress callbacks
- `TimeoutError` exception
- Long-running operations

**Output**:

```text
Monitoring existing scan: nessus-local-20251108-143022

Waiting for scan to complete...
(This may take 5-10 minutes for a real Nessus scan)

   Progress: 0% - Status: queued
   Progress: 25% - Status: running
   Progress: 50% - Status: running
   Progress: 75% - Status: running
   Progress: 100% - Status: running

✓ Scan completed!
   Status: completed
   Duration: 450 seconds
```

---

### 03_scan_and_wait.py

**What it demonstrates**:
- One-line scan submission and completion waiting
- Interactive user input
- Real-time progress bar
- Vulnerability summary

**Usage**:

```bash
python client/examples/03_scan_and_wait.py
```

**Key Concepts**:
- `scan_and_wait()` convenience method
- Progress bar visualization
- `get_vulnerability_summary()` helper

**Output**:

```text
Enter target IP (default: 192.168.1.1):
Enter scan name (default: Quick Scan):

Submitting scan: Quick Scan
Targets: 192.168.1.1

   [████████████████████████████████████████] 100% - completed

✓ Scan completed successfully!

Vulnerability Summary:
  Critical (4): 11
  High (3):     15
  Medium (2):   10
  Low (1):      4

Total vulnerabilities found: 40
```

---

### 04_get_critical_vulns.py

**What it demonstrates**:
- Retrieving scan results
- Filtering vulnerabilities
- Parsing JSON-NL format
- Schema profiles comparison
- Helper methods for critical vulnerabilities

**Usage**:

```bash
python client/examples/04_get_critical_vulns.py nessus-local-20251108-143022
```

**Key Concepts**:
- `get_results()` with filters
- `get_critical_vulnerabilities()` helper
- JSON-NL parsing
- Schema profiles (minimal, brief, full)
- Result filtering

**Output**:

```text
Method 1: Using helper method
------------------------------------------------------------
Found 11 critical vulnerabilities

1. Host: 192.168.1.1
   Plugin: Apache HTTP Server Multiple Vulnerabilities
   Severity: 4 (Critical)
   CVSS: 9.8
   CVE: CVE-2021-44228, CVE-2021-45046

Method 2: Using get_results with filters
------------------------------------------------------------
Found 8 EXPLOITABLE critical vulnerabilities

1. Host: 192.168.1.1
   Plugin ID: 12345
   Severity: 4
   CVSS: 10.0
   Exploit Available: True

Method 3: Schema profiles comparison
------------------------------------------------------------
Minimal schema size: 1523 bytes
Brief schema size: 3847 bytes
Size reduction: ~60%
```

---

### 05_full_workflow.py

**What it demonstrates**:
- Complete end-to-end workflow
- Comprehensive error handling
- Server health checks
- Scanner and queue information
- Result analysis
- Production-ready patterns

**Usage**:

```bash
python client/examples/05_full_workflow.py
```

**Key Concepts**:
- Multi-step workflow
- Error handling at each step
- `list_scanners()` method
- `get_queue_status()` method
- Comprehensive logging

**Output**:

```text
======================================================================
               NESSUS MCP CLIENT - FULL WORKFLOW
======================================================================

STEP 1: Server Health Check
----------------------------------------------------------------------
✓ MCP server is healthy

STEP 2: Available Scanners
----------------------------------------------------------------------
Registered scanners: 2
  - Nessus Professional (local): ✓ Enabled
  - Nessus Essentials (cloud): ✗ Disabled

STEP 3: Queue Status
----------------------------------------------------------------------
Main queue depth: 0
Dead letter queue: 0

STEP 4: Submit Scan
----------------------------------------------------------------------
Enter target IP/range (default: 192.168.1.1):
✓ Scan submitted successfully
  Task ID: nessus-local-20251108-143022
  Status: queued
  Idempotent: False

STEP 5: Monitor Scan Progress
----------------------------------------------------------------------
Waiting for scan to complete (timeout: 10 minutes)...

  [██████████████████████████████████████████████] 100% - completed

✓ Scan completed: completed

STEP 6: Analyze Results
----------------------------------------------------------------------
Vulnerability Summary by Severity:
  Critical (4): 11
  High (3):     15
  Medium (2):   10
  Low (1):      4
  Total:        40

Critical Vulnerabilities:

  1. Apache HTTP Server Multiple Vulnerabilities
     Host: 192.168.1.1
     CVSS: 9.8
     CVE: CVE-2021-44228, CVE-2021-45046
     ⚠ EXPLOIT AVAILABLE

======================================================================
                        WORKFLOW COMPLETE
======================================================================

✓ Successfully scanned 192.168.1.1
✓ Found 40 total vulnerabilities
✓ Task ID: nessus-local-20251108-143022
```

---

### 06_e2e_workflow_test.py

**What it demonstrates**:
- Automated E2E test workflow
- Validates complete scan cycle
- Asserts expected states
- Cleanup after test

**Usage**:

```bash
python client/examples/06_e2e_workflow_test.py
```

**Key Concepts**:
- Automated testing pattern
- State assertions
- Test cleanup
- CI/CD integration

---

## Code Patterns

### Pattern 1: Basic Scan Submission

```python
async with NessusFastMCPClient() as client:
    task = await client.submit_scan(
        targets="192.168.1.1",
        scan_name="My Scan"
    )
    task_id = task["task_id"]
```

### Pattern 2: Wait with Progress

```python
def progress(status):
    print(f"Progress: {status.get('progress', 0)}%")

final = await client.wait_for_completion(
    task_id=task_id,
    progress_callback=progress
)
```

### Pattern 3: Get Filtered Results

```python
results = await client.get_results(
    task_id=task_id,
    schema_profile="minimal",
    filters={"severity": "4"},
    page=0  # All data
)

for line in results.strip().split('\n'):
    data = json.loads(line)
    if data['type'] == 'vulnerability':
        print(data['host'], data['cvss_score'])
```

### Pattern 4: Error Handling

```python
try:
    task = await client.submit_scan(...)
except TimeoutError:
    print("Operation timed out")
except ConnectionError:
    print("Server unreachable")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8835/mcp` | MCP server endpoint |

**Note**: Inside Docker containers, use `http://mcp-api:8000/mcp`

---

## Troubleshooting

### Connection Error

```text
✗ Server unreachable: Connection refused
```

**Solution**: Start MCP server with `python tools/run_server.py`

### Timeout Error

```text
✗ Scan timed out after 600 seconds
```

**Solution**: Increase timeout or check scanner worker logs

### Task Not Found

```text
✗ Error: Task nessus-local-... not found
```

**Solution**: Verify task_id is correct with `python client/examples/01_basic_usage.py`

---

## Running All Examples

```bash
# Sequential execution
for i in 01 02 03 04 05; do
    python client/examples/${i}_*.py
done
```

---

## See Also

- [Client Library](../README.MD) - NessusFastMCPClient documentation
- [Client Implementation](../nessus_fastmcp_client.py) - Source code
- [Testing Guide](../../docs/TESTING.md) - Integration testing patterns
