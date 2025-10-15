# Budget Tracker Configuration

## HPC Resource Rates Configuration

The HPC resource rates are now externalized in a configuration file for easy updates without code changes.

### Configuration File

**Location**: `Agent-shared/budget/hpc_resource_rates.json`

### Format

```json
{
  "rates": {
    "resource-group-name": {
      "gpu": <number_of_gpus>,
      "rate": <rate_per_second>,
      "description": "Optional description"
    }
  },
  "default": {
    "gpu": <default_gpu_count>,
    "rate": <default_rate>,
    "description": "Default rate when resource group not found"
  }
}
```

### Example

```json
{
  "rates": {
    "cx-small": {
      "gpu": 4,
      "rate": 0.007,
      "description": "Small compute resource"
    },
    "cx-large": {
      "gpu": 8,
      "rate": 0.010,
      "description": "Large compute resource"
    }
  },
  "default": {
    "gpu": 4,
    "rate": 0.007,
    "description": "Default compute resource rate"
  }
}
```

### Updating Rates

To update the HPC resource rates:

1. Edit the `hpc_resource_rates.json` file
2. Add, modify, or remove resource groups as needed
3. Save the file
4. The budget tracker will automatically load the new rates on the next run

### Fallback Behavior

If the configuration file is not found or cannot be parsed:
- The budget tracker will use built-in default rates
- A warning will be logged to help identify the issue
- The system will continue to operate with default values

### Error Handling

The budget tracker includes comprehensive error handling:
- **JSON parsing errors**: Logged with details, falls back to defaults
- **Missing file**: Warning logged, uses built-in defaults
- **I/O errors**: Error logged with details, falls back to defaults

All errors are logged with meaningful messages to help diagnose configuration issues.
