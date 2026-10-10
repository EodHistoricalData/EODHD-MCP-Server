# ASX Corporate Actions API

Status: complete
Source: financial-apis (ASX Australia Corporate Actions API)
Docs: https://eodhd.com/financial-apis/asx-corporate-actions
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /asx-corporate-actions
Method: GET
Auth: api_token (query)
Tool: get_asx_corporate_actions

## Purpose
Return structured corporate action data for ASX (Australian Securities Exchange) listed
securities: dividends, stock splits, bonus issues, rights issues, buybacks, capital returns,
and share purchase plans. Data is sourced from the official ASX ReferencePoint feed (E34)
and refreshed daily. Coverage is limited to ASX-listed securities — all tickers use the
`.AU` suffix.

## Parameters
- Required:
  - api_token: EODHD API key.
- Optional:
  - type: Corporate action category. One of `dividends`, `splits`, `bonus-issues`,
    `rights-issues`, `buybacks`, `capital-returns`, `spp`, `other`. Omit to return all types.
  - symbol: Ticker with `.AU` suffix (e.g. `PMV.AU`). Filters results to a single security.
  - date_from: Start date in YYYY-MM-DD (inclusive, applied to the event date).
  - date_to: End date in YYYY-MM-DD (inclusive, applied to the event date).
  - page[limit]: Page size, 1 to 1000 (default 100).
  - page[offset]: Zero-based pagination offset (default 0).
  - fmt: Response format. Currently only `json` is supported.

### Action types
Each `type` value groups one or more ASX ReferencePoint (E34) codes:

| Value | ASX Codes | Description |
|-------|-----------|-------------|
| dividends | DV | Cash dividends (including franked amounts and DRP details) |
| splits | RC | Stock splits and reconstructions |
| bonus-issues | BN | Bonus share issues |
| rights-issues | RR, NR, PR, XR | Rights issues, including non-renounceable variants |
| buybacks | BB | Share buyback programmes |
| capital-returns | CR | Return of capital to shareholders |
| spp | SP | Share Purchase Plans |
| other | AO, CC, CG, CL, CN, IN, OP | Other action types not covered above |

## Response (shape)
All responses share the same envelope. The `data` array contains records whose structure
depends on the requested type.

- data[]: array of type-specific corporate-action records.
- meta.total: integer total number of matching records.
- meta.page.offset / meta.page.limit: applied pagination.
- links.next: string or null — URL for the next page (null on the last page).

### Dividends
- code, date, value, unadjustedValue, period, currency, exchange.
- recordDate, paymentDate, declarationDate.
- _asx_extra: object with AU-specific tax/reinvestment fields:
  - isin, asx_ticker, corporate_action_id, transaction_type.
  - franked_amount_aud (number), franked_percent (0–100).
  - drp_indicator (int), drp_price_aud (number|null), drp_discount_rate (number).
  - bsp_indicator (int), special_indicator (Y/N), withholding_tax_rate (number).
  - tax_deferred_amount_aud, tax_advantaged_amount_aud, foreign_source_dividend_aud,
    special_dividend_amount_aud, comment.

### Splits
- code, date, split (e.g. `"2000:3"`), exchange.
- _asx_extra: asx_ticker, record_date, effective_date, new_security_code,
  calculation_method, corporate_action_id.

### Bonus issues
- code, date, ratio (e.g. `"4:21"`), exchange, pariPassu, recordDate, despatchDate.

### Rights issues
- code, date, type (e.g. `non-renounceable`), ratio, currency, exchange, pariPassu,
  recordDate, despatchDate, applicationPrice, applicationCloseDate.

### Capital returns
- code, date, value, currency, exchange, recordDate, paymentDate.

### Share Purchase Plan (SPP)
- code, price, currency, exchange, maxAmount, minAmount, recordDate, despatchDate,
  offerCloseDate.

## Example request
```bash
curl "https://eodhd.com/api/asx-corporate-actions?api_token=YOUR_API_KEY&type=dividends&symbol=PMV.AU&fmt=json"
```

### Example response
```json
{
  "data": [
    {
      "code": "PMV.AU",
      "date": "2026-08-03",
      "value": 0.45,
      "unadjustedValue": 0.45,
      "period": "Interim",
      "currency": "AUD",
      "exchange": "AU",
      "recordDate": "2026-08-04",
      "paymentDate": "2026-08-20",
      "declarationDate": null,
      "_asx_extra": {
        "isin": "AU000000PMV2",
        "asx_ticker": "PMV",
        "franked_amount_aud": 0.45,
        "franked_percent": 100,
        "drp_indicator": 4,
        "withholding_tax_rate": 0,
        "comment": "AUD 0.45 FRANKED, 30% CTR, DRP SUSP"
      }
    }
  ],
  "meta": { "total": 1, "page": { "offset": 0, "limit": 100 } },
  "links": { "next": null }
}
```

## Notes
- API call consumption: 1 call per request.
- Available on the Fundamentals and All-in-One plans (not the standalone Fundamental plan).
- ASX only — for other exchanges use the Splits/Dividends APIs
  (`get_historical_dividends`, `get_historical_splits`).
- Daily refresh from the ASX ReferencePoint feed; same-day changes may appear with up to
  a 24-hour delay.
- Buybacks and `other` categories are sparse — ASX publishes them less frequently.
- Pagination: when `links.next` is not null, increment `page[offset]` (or follow that URL)
  to fetch the next page.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Response includes `data`, `meta`, and `links`. |
| **401** | Unauthorized | Missing or invalid `api_token`. |
| **403** | Forbidden | Plan does not include access to this endpoint. |
| **422** | Unprocessable Entity | Validation error — invalid `type`, date format, or pagination range. |
| **429** | Too Many Requests | Rate limit exceeded. Slow down requests. |

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
        if e.response.status_code == 403:
            print("Error: Plan does not include the ASX Corporate Actions endpoint.")
        elif e.response.status_code == 422:
            print("Error: Invalid type, date format, or pagination range.")
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
- Walk `links.next` (or increment `page[offset]`) to page through large result sets
- Cache responses to reduce API calls — data only refreshes once per day
