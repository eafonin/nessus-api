# X-API-Token Explanation and Solution

## Problem Summary

After docker rebuild ~2 weeks ago, all nessusAPIWrapper scripts that use Web UI endpoints stopped working with `IncompleteRead` errors and HTTP 412 "API is not available" responses.

## Root Cause

The `X-API-Token` changed when Nessus was rebuilt. This token is:

1. **Hardcoded in the Nessus Web UI JavaScript** (`/opt/nessus/var/nessus/www/nessus6.js`)
2. **Required for all Web UI endpoint operations** (launch, stop, edit scans)
3. **NOT returned in authentication responses** (only session token is returned)
4. **Static per Nessus installation** (doesn't change per session, only when Nessus is reinstalled)

### Evidence

From `nessus6.js`:
```javascript
{key:"getApiToken",value:function(){return"778F4A9C-D797-4817-B110-EC427B724486"}}
```

### Why It's Required

Testing confirms:
- ✅ Authentication works WITHOUT X-API-Token (HTTP 200)
- ❌ Operations (launch/stop/edit) FAIL without X-API-Token (HTTP 412)
- ✅ Operations succeed WITH correct X-API-Token (HTTP 200)

## Solution Options

### Option 1: Use the Token Extraction Utility (RECOMMENDED)

Use `get_api_token.py` to dynamically extract the current token:

```bash
# Get current token
python3 nessusAPIWrapper/get_api_token.py

# Export as environment variable
export NESSUS_API_TOKEN=$(python3 nessusAPIWrapper/get_api_token.py)

# Use in scripts
python3 nessusAPIWrapper/launch_scan_v2.py
```

**Advantages:**
- Automatically adapts to Nessus rebuilds
- No hardcoded values
- Single source of truth

**Disadvantages:**
- Requires one extra HTTP request to fetch nessus6.js
- Slightly more complex

### Option 2: Update Hardcoded Token After Rebuilds

When Nessus is rebuilt, update the token in all scripts:

```bash
# Extract new token
NEW_TOKEN=$(python3 nessusAPIWrapper/get_api_token.py)

# Update all scripts
sed -i "s/STATIC_API_TOKEN = '.*'/STATIC_API_TOKEN = '$NEW_TOKEN'/" nessusAPIWrapper/*.py
```

**Advantages:**
- Simple, no runtime overhead
- Works with current script structure

**Disadvantages:**
- Must remember to update after each rebuild
- Error-prone (easy to forget)

### Option 3: Fetch Token Once and Cache

Store the token in a config file or environment variable:

```bash
# One-time setup after Nessus rebuild
python3 nessusAPIWrapper/get_api_token.py > .nessus_api_token

# Scripts read from file
STATIC_API_TOKEN = open('.nessus_api_token').read().strip()
```

**Advantages:**
- Balance between dynamic and static approaches
- Easy to update

**Disadvantages:**
- Requires file management
- Must update file after rebuilds

## Current Token

**Current X-API-Token:** `778F4A9C-D797-4817-B110-EC427B724486`

**Previously used (now invalid):** `af824aba-e642-4e63-a49b-0810542ad8a5`

## Files Updated

The following files were updated with the correct token:
1. `edit_scan.py`
2. `edit_scan_v2.py`
3. `generate_api_keys.py`
4. `launch_scan.py`
5. `launch_scan_v2.py`
6. `manage_credentials.py`
7. `manage_scans.py`

## Testing Verification

```bash
# Test that scripts work with correct token
python3 nessusAPIWrapper/launch_scan_v2.py list
python3 nessusAPIWrapper/launch_scan_v2.py launch 8
```

## Recommendation

**For production use:** Implement Option 1 or Option 3 to avoid manual updates after Nessus rebuilds.

The current scripts (Option 2) will work but require manual token updates whenever Nessus is rebuilt/reinstalled.

## Technical Details

### Why Not Use Session Token Only?

Session tokens (from `/session` endpoint) are only valid for that session and are passed via `X-Cookie: token=<session_token>`. They authenticate the user but don't satisfy the X-API-Token requirement.

### Why Does Web UI Work?

The browser's JavaScript automatically includes the X-API-Token from the loaded `nessus6.js` file in all requests.

### Can We Bypass This?

No. The X-API-Token requirement is server-side validation. The only workaround is to use the official pytenable API, but that has Nessus Essentials limitations (can't launch scans, edit scans, etc).
