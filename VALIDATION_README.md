# Technical Indicator Validation Guide

This guide provides instructions for validating the technical indicators in the manusoptions project and fixing the export button issue.

## Export Button Fix

The export button error occurs because the code is trying to use the `.get()` method on a string object. The error message is:

```
AttributeError: 'str' object has no attribute 'get'
```

### How to Fix

1. Replace the `export_buttons.py` file in the `dashboard_utils` directory with the fixed version:

```bash
cp fixed_export_buttons.py dashboard_utils/export_buttons.py
```

2. The fix handles both string and dictionary types for the `selected_symbol` parameter:

```python
# Fix: Handle both string and dictionary types for selected_symbol
if isinstance(selected_symbol, dict):
    symbol = selected_symbol.get("symbol", "unknown")
elif isinstance(selected_symbol, str):
    symbol = selected_symbol
else:
    symbol = "unknown"
```

This change has been applied to all export callback functions in the file.

## Technical Indicator Validation

To validate that the technical indicators are calculating correctly from minute-level data, a comprehensive validation script has been created.

### What the Validation Script Does

1. Generates synthetic price data with known patterns (trend, oscillating, random)
2. Calculates technical indicators using the project's implementation
3. Validates the results against expected values calculated independently
4. Generates plots for visual inspection
5. Reports any discrepancies or issues found

### Indicators Validated

- Bollinger Bands
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Intraday Momentum Index (IMI)
- Money Flow Index (MFI)
- Fair Value Gaps (FVG)

### How to Run the Validation

1. Make sure the validation script is executable:

```bash
chmod +x validate_indicators.py
```

2. Run the validation script:

```bash
python validate_indicators.py
```

3. Check the results:
   - The script will output validation results to the console
   - Detailed logs are saved to `indicator_validation_results.log`
   - Visual plots are saved to `validation_plots_*` directories

### Interpreting the Results

- **PASSED**: The indicator is calculating correctly
- **FAILED**: There are discrepancies between the expected and actual values

If any validation fails, check the log file for detailed information about the issues.

## Validation Methodology

### Synthetic Data Generation

The script generates three types of synthetic data:

1. **Trend**: Uptrend followed by downtrend
2. **Oscillating**: Sine wave pattern
3. **Random**: Random walk

This variety of patterns ensures that the indicators are tested under different market conditions.

### Validation Checks

For each indicator, the script:

1. Calculates the indicator using the project's implementation
2. Independently calculates the expected values using the standard formulas
3. Compares the results using numpy's `allclose` function
4. Checks for proper handling of edge cases (e.g., NaN values at the beginning)

### Timeframe Resampling

The script also validates that indicators calculate correctly on resampled data:

- 5-minute
- 15-minute
- 30-minute
- 1-hour

This ensures that the aggregation and resampling logic works correctly.

## Visual Inspection

The script generates plots for each indicator, saved to the `validation_plots_*` directories. These plots can be used for visual inspection to confirm that the indicators are behaving as expected.

## Troubleshooting

If you encounter issues with the validation:

1. Check that all dependencies are installed
2. Verify that the technical_analysis.py file is in the correct location
3. Check the log file for detailed error messages

## Conclusion

By using this validation script, you can ensure that all technical indicators are calculating correctly from minute-level data. The script provides both numerical validation and visual confirmation of the indicators' behavior.

If all validations pass, you can be confident that the technical indicators are implemented correctly and are producing reliable results.

