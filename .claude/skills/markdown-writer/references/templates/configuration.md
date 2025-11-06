# [Feature] Configuration

> Complete configuration reference for [feature]

## Configuration File

**Location**: `~/.config/app/config.json`

## Configuration Format

```json
{
  "option1": "value",
  "option2": 123,
  "option3": true
}
```

## Available Options

### option1

* **Type**: `string`
* **Default**: `"default-value"`
* **Required**: Yes

Description of what this option controls.

**Example**:

```json
{
  "option1": "custom-value"
}
```

### option2

* **Type**: `number`
* **Default**: `100`
* **Required**: No

Description of what this option controls.

**Example**:

```json
{
  "option2": 500
}
```

## Complete Example

```json
{
  "option1": "production",
  "option2": 500,
  "option3": true
}
```

## See Also

- [Quick Start Guide](./quickstart.md)
- [Troubleshooting](./troubleshooting.md)
