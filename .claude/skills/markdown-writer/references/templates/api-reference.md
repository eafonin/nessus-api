# API Reference: [Module Name]

> Complete API documentation for [module]

## Methods

### methodName()

Description of what the method does.

**Syntax**:

```javascript
methodName(param1, param2, options)
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param1` | `string` | Yes | Description |
| `param2` | `number` | No | Description |
| `options` | `Object` | No | Config options |

**Returns**: `Promise<Result>`

**Example**:

```javascript
const result = await methodName('value', 42, {
  timeout: 10000
});
```

**Errors**:

| Error | Cause | Resolution |
|-------|-------|------------|
| `InvalidParamError` | Invalid param1 | Check format |
| `TimeoutError` | Timeout exceeded | Increase timeout |

### anotherMethod()

Description of what this method does.

**Syntax**:

```javascript
anotherMethod(data)
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `data` | `Object` | Yes | Data to process |

**Returns**: `boolean`

**Example**:

```javascript
const success = anotherMethod({
  key: 'value'
});
```

## See Also

- [Quick Start Guide](./quickstart.md)
- [Configuration Reference](./configuration.md)
