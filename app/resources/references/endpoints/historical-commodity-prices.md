# Commodities API (Historical Prices)

Status: complete
Source: financial-apis (Commodities API)
Docs: https://eodhd.com/financial-apis/commodities-api
Provider: EODHD (data sourced from FRED — Federal Reserve Economic Data)
Base URL: https://eodhd.com/api
Path: /commodities/historical/{CODE}
Method: GET
Auth: api_token (query)
Tool: get_historical_commodity_prices

## Purpose
Return historical price data for a commodity series — energy, metals, agriculturals, and
broad commodity indices — sourced from FRED (Federal Reserve Economic Data). The API covers
23 series with daily, weekly, monthly, quarterly, and annual intervals, going back decades
for major energy commodities.

## Parameters
- Required:
  - CODE (path): Commodity code (e.g. `WTI`, `BRENT`, `URANIUM`) or `ALL_COMMODITIES` for
    the global index. Case-insensitive; the tool normalizes it to upper case.
  - api_token: EODHD API key.
- Optional:
  - interval: Data frequency — `daily`, `weekly`, `monthly` (default), `quarterly`, `annual`.
    Not all commodities support all intervals (daily is energy-only; metals and
    agriculturals are typically monthly).

## Available commodity codes
| Category | Codes |
|----------|-------|
| Energy | WTI, BRENT, NATURAL_GAS, GASOLINE_US, DIESEL_USGULF, HEATING_OIL_NYH, JET_FUEL_USGULF, PROPANE_MBTX, COAL_AU, URANIUM |
| Metals | ALUMINUM, COPPER |
| Agricultural | WHEAT, CORN, SUGAR, COTTON, COFFEE_MILD_ARABICA, COFFEE_ROBUSTAS |
| Indices | ALL_COMMODITIES, ALL_COMMODITIES_PRODUCER, ENERGY_INDEX, NATGAS_EU, LNG_ASIA |

## Response (shape)
The API returns a JSON object with two sections: `meta` (commodity metadata) and `data`
(price history, newest-first).

- meta.name: string — full commodity name from FRED.
- meta.interval: string — data frequency (daily, weekly, monthly, quarterly, annual).
- meta.unit: string — measurement unit (e.g. `Dollars per Barrel`, `Index 2016 = 100`).
- meta.total: integer — total number of data points available.
- data[].date: string — YYYY-MM-DD.
- data[].value: number — price or index value.

## Example request
```bash
curl "https://eodhd.com/api/commodities/historical/WTI?api_token=YOUR_API_KEY&interval=monthly"
```

### Example response
```json
{
  "meta": {
    "name": "Crude Oil Prices: West Texas Intermediate (WTI) - Cushing, Oklahoma",
    "interval": "monthly",
    "unit": "Dollars per Barrel",
    "total": 484
  },
  "data": [
    { "date": "2026-04-01", "value": 108.64 },
    { "date": "2026-03-01", "value": 102.86 },
    { "date": "2026-02-01", "value": 66.96 }
  ]
}
```

## Notes
- API call consumption: 5 calls per request.
- Available across all plans, including the free plan.
- The `demo` API key only returns WTI; requests for any other code return 403.
- Data freshness depends on FRED's upstream providers (EIA, IMF):
  - Daily energy series are published by the EIA in weekly batches (typically Tuesdays),
    so the latest available data point may be up to ~1 week old.
  - Weekly gasoline is published every Monday (available next day).
  - Monthly metals, agriculturals, indices, coal, and uranium lag 2–3 weeks after the
    reference month ends.
- Precious metals (Gold/Silver/Platinum/Palladium) have been discontinued by FRED.
- Major energy series go back to 1986; most metals and agriculturals to the 1990s.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up. Upgrade plan or wait for limit reset. |
| **403** | Forbidden | Invalid API key, or the `demo` key used for a non-WTI code. |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

When an error occurs, the API returns a JSON response with error details:

```json
{
  "error": "Error message description",
  "code": 403
}
```

### Handling Errors

**Python Example**:
```python
import requests

def make_api_request(url, params):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises HTTPError for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 402:
            print("Error: API limit exceeded. Please upgrade your plan.")
        elif e.response.status_code == 403:
            print("Error: Invalid API key, or demo key used for a non-WTI commodity.")
        elif e.response.status_code == 429:
            print("Error: Rate limit exceeded. Please slow down your requests.")
        else:
            print(f"HTTP Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
```

**Best Practices**:
- Always check status codes before processing response data
- Implement exponential backoff for 429 errors
- Choose an interval the commodity actually supports (daily is energy-only)
- Cache responses to reduce API calls — monthly series only update once a month
