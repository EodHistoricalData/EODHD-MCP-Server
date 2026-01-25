# app/tools/export_data.py
"""
Tool for exporting stock data in various formats.
"""

import json
import csv
import io
from typing import Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def export_stock_data(
        ticker: str,
        data_type: str = "eod",
        format: str = "json",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Export stock data in CSV or JSON format.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US')
            data_type: Type of data - 'eod', 'intraday', 'fundamentals'. Default is 'eod'.
            format: Output format - 'json' or 'csv'. Default is 'json'.
            start_date: Optional start date in YYYY-MM-DD format (for eod/intraday)
            end_date: Optional end date in YYYY-MM-DD format (for eod/intraday)

        Returns:
            Data in requested format (JSON or CSV string)
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        # Build URL based on data type
        if data_type == "eod":
            url = f"{EODHD_API_BASE}/eod/{ticker}?fmt=json"
            if start_date:
                url += f"&from={start_date}"
            if end_date:
                url += f"&to={end_date}"
        elif data_type == "intraday":
            url = f"{EODHD_API_BASE}/intraday/{ticker}?fmt=json&interval=5m"
            if start_date:
                url += f"&from={start_date}"
            if end_date:
                url += f"&to={end_date}"
        elif data_type == "fundamentals":
            url = f"{EODHD_API_BASE}/fundamentals/{ticker}"
        else:
            return json.dumps({"error": f"Invalid data_type: {data_type}"}, indent=2)

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        if isinstance(data, dict) and data.get("error"):
            return json.dumps(data, indent=2)

        # Format output
        if format == "csv":
            if isinstance(data, list) and len(data) > 0:
                output = io.StringIO()
                # Add UTF-8 BOM for Excel compatibility
                output.write('\ufeff')

                if isinstance(data[0], dict):
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    writer = csv.writer(output)
                    for row in data:
                        writer.writerow([row] if not isinstance(row, (list, tuple)) else row)

                return json.dumps({
                    "format": "csv",
                    "ticker": ticker,
                    "data_type": data_type,
                    "rows": len(data),
                    "csv": output.getvalue()
                }, indent=2)
            else:
                return json.dumps({"error": "Data is not in a format suitable for CSV export."}, indent=2)

        # Default JSON format
        return json.dumps({
            "format": "json",
            "ticker": ticker,
            "data_type": data_type,
            "rows": len(data) if isinstance(data, list) else 1,
            "data": data
        }, indent=2)
