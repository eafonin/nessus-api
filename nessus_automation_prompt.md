# Nessus Automation Script Generation Prompt

## Context

I need help writing a Python automation script for Nessus Essentials using the pytenable library.

## Environment Details

- **Nessus URL**: `https://localhost:8834/`
- **Credentials**:
  - Username: `nessus`
  - Password: `nessus`
- **API Keys**:
  - Access Key: `abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405`
  - Secret Key: `06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837`
- **Library**: `pytenable`
- **Local pytenable source**: `.\env\Lib\site-packages\tenable\nessus\`

## Available Resources

- GitHub repository: https://github.com/tenable/pyTenable
- Documentation: https://pytenable.readthedocs.io
- Local source code for reference: `.\env\Lib\site-packages\tenable\nessus\`

## Request

Please help me write a Python script that does the following:

[**DESCRIBE YOUR SPECIFIC AUTOMATION TASK HERE**]

For example:
- List all available scan policies
- Create a new scan with specific targets
- Launch a scan and monitor its progress
- Export scan results in a specific format
- Generate reports from completed scans
- Manage scan schedules
- etc.

## Requirements

1. **Read the local pytenable source code** in `.\env\Lib\site-packages\tenable\nessus\` to understand:
   - Available methods and their parameters
   - Correct usage patterns
   - Return value structures
   - Error handling approaches

2. **Generate production-ready code** that includes:
   - Proper error handling
   - Clear comments and documentation
   - Connection management (SSL verification handling for localhost)
   - Logging where appropriate
   - Type hints where beneficial

3. **Provide examples** showing:
   - How to initialize the Nessus client
   - How to authenticate (API keys vs username/password)
   - How to handle common scenarios
   - How to parse and use the returned data

4. **Follow best practices**:
   - Don't hardcode credentials (show how to use environment variables or config files)
   - Handle SSL certificate issues for localhost
   - Include connection testing
   - Implement appropriate wait/polling mechanisms for async operations

## Sample Initialization Code

```python
from tenable.nessus import Nessus

# Initialize Nessus client
nessus = Nessus(
    url='https://localhost:8834',
    access_key='abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405',
    secret_key='06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837',
    ssl_verify=False  # For localhost/self-signed certs
)

# Test connection
# [Your code here]
```

## Additional Notes

- Please reference the actual source code in `.\env\Lib\site-packages\tenable\nessus\` to ensure accuracy
- If you find undocumented features in the source, please highlight them
- Suggest any security improvements or best practices specific to my use case
- Include example output or expected results where helpful

---

**Instructions for Claude**:
1. First, explore the local pytenable source code structure
2. Read relevant modules based on the requested functionality
3. Generate the custom automation script with inline documentation
4. Provide usage examples and expected output
5. Suggest improvements or alternative approaches if applicable
