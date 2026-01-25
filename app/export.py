# app/export.py
"""
Data export utilities for EODHD MCP Server.
"""

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


def to_csv(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    include_bom: bool = True
) -> str:
    """
    Convert list of dicts to CSV string.

    Args:
        data: List of dictionaries to convert
        columns: Optional list of columns to include (default: all)
        include_bom: Include UTF-8 BOM for Excel compatibility

    Returns:
        CSV string
    """
    if not data:
        return ""

    output = io.StringIO()

    if include_bom:
        output.write('\ufeff')

    # Determine columns
    if columns:
        fieldnames = columns
    else:
        fieldnames = list(data[0].keys())

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    for row in data:
        # Convert nested dicts/lists to JSON strings
        flat_row = {}
        for key in fieldnames:
            value = row.get(key)
            if isinstance(value, (dict, list)):
                flat_row[key] = json.dumps(value)
            else:
                flat_row[key] = value
        writer.writerow(flat_row)

    return output.getvalue()


def to_json(
    data: Any,
    include_metadata: bool = True,
    indent: int = 2
) -> str:
    """
    Convert data to JSON string with optional metadata.

    Args:
        data: Data to convert
        include_metadata: Include export metadata
        indent: JSON indentation

    Returns:
        JSON string
    """
    if include_metadata:
        result = {
            "metadata": {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "record_count": len(data) if isinstance(data, list) else 1,
                "format": "json"
            },
            "data": data
        }
    else:
        result = data

    return json.dumps(result, indent=indent, default=str)


def export_price_data(
    data: List[Dict[str, Any]],
    format: str = "json",
    ticker: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export price data (EOD/intraday) in specified format.

    Args:
        data: Price data list
        format: Output format ('json' or 'csv')
        ticker: Optional ticker symbol for metadata

    Returns:
        Dict with export result
    """
    columns = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]

    if format == "csv":
        content = to_csv(data, columns=columns)
        return {
            "format": "csv",
            "ticker": ticker,
            "rows": len(data),
            "content": content
        }
    else:
        content = to_json(data)
        return {
            "format": "json",
            "ticker": ticker,
            "rows": len(data),
            "content": content
        }


def export_fundamentals(
    data: Dict[str, Any],
    sections: Optional[List[str]] = None,
    format: str = "json"
) -> Dict[str, Any]:
    """
    Export fundamentals data.

    Args:
        data: Fundamentals data dict
        sections: Optional list of sections to include
        format: Output format

    Returns:
        Dict with export result
    """
    if sections:
        filtered = {k: v for k, v in data.items() if k in sections}
    else:
        filtered = data

    if format == "json":
        content = to_json(filtered)
    else:
        # Flatten for CSV
        flat_data = []
        for section, values in filtered.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    flat_data.append({
                        "section": section,
                        "field": key,
                        "value": value
                    })
        content = to_csv(flat_data)

    return {
        "format": format,
        "sections": list(filtered.keys()),
        "content": content
    }


def export_screener_results(
    data: List[Dict[str, Any]],
    format: str = "json",
    columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Export stock screener results.

    Args:
        data: Screener results list
        format: Output format
        columns: Optional columns to include

    Returns:
        Dict with export result
    """
    default_columns = [
        "code", "name", "exchange", "sector", "industry",
        "market_capitalization", "pe_ratio", "dividend_yield"
    ]

    cols = columns or default_columns

    if format == "csv":
        content = to_csv(data, columns=cols)
    else:
        content = to_json(data)

    return {
        "format": format,
        "rows": len(data),
        "columns": cols,
        "content": content
    }
