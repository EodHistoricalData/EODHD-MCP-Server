# Insider Transactions API V2 — SEC Form 4

Status: complete
Source: financial-apis (Insider Transactions API V2 / SEC Form 4)
Docs: https://eodhd.com/financial-apis/insider-transactions-api
Provider: EODHD (data sourced from SEC EDGAR)
Base URL: https://eodhd.com/api
Path: /sec-filings/{symbol}/form4
Method: GET
Auth: api_token (query)
Tool: get_insider_transactions_form4

## Purpose
Return SEC Form 4 filings — the public disclosure of stock transactions by directors,
officers, and 10% owners of US-listed companies under Section 16 of the Securities Exchange
Act. Each filing exposes non-derivative transactions (common stock), derivative transactions
(stock options, RSUs, warrants), and the footnotes referenced from each row. Data is sourced
directly from SEC EDGAR and refreshed daily.

This is the richer V2 endpoint. For a flat, simpler list use the legacy
`get_insider_transactions` tool (`/api/insider-transactions`), which remains available for
backward compatibility.

## Parameters
- Required:
  - symbol (path): US ticker, e.g. `AAPL` or `AAPL.US`. Case-insensitive; the `.US` suffix
    is optional. Form 4 is filed by US-listed issuers only.
  - api_token: EODHD API key.
- Optional:
  - page[limit]: Page size, 1 to 100 (default 20).
  - page[offset]: Zero-based pagination offset (default 0).

## Transaction codes
The `transaction_code` field uses the SEC Section 16 reporting codes (shared by non-derivative
and derivative rows):

| Code | Description |
|------|-------------|
| P | Open-market or private purchase |
| S | Open-market or private sale |
| A | Grant/award/acquisition under an equity-based compensation plan |
| D | Disposition to the issuer under an equity-based compensation plan |
| F | Payment of exercise price or tax via withholding shares |
| M | Exercise or conversion of a derivative received under a comp plan |
| G | Bona fide gift |
| V | Voluntarily reported transaction |
| J | Other acquisition or disposition (described in a footnote) |
| L | Small acquisition under SEC Rule 16a-6 |
| C | Conversion of a derivative security |
| E | Expiration of a short derivative position |
| H | Expiration of a long derivative position with value received |
| O | Exercise of an out-of-the-money derivative |
| X | Exercise of an in-the-money or at-the-money derivative |

## Response (shape)
The envelope contains a `data` array of filings (sorted by `filed_at` descending), a `meta`
object with pagination info, and a `links` object. Only `links.next` is exposed.

- data[]: Form 4 filings, each with:
  - accession_number: string — unique SEC filing identifier.
  - filed_at: string (date) — submission date, YYYY-MM-DD.
  - period_of_report: string (date) — reporting period, YYYY-MM-DD.
  - non_derivative[]: direct stock transactions:
    - reporting_owner_cik, reporting_owner_name.
    - is_director, is_officer, is_ten_percent_owner, is_other (booleans).
    - officer_title (str|null), other_text (str|null).
    - security_title, transaction_date (ISO-8601 datetime), transaction_code.
    - acquired_or_disposed (`A`/`D`), shares_amount.
    - price_per_share (number|null), shares_owned_after, total_value (number|null).
  - derivative[]: option/RSU/warrant transactions (the above fields plus):
    - conversion_or_exercise_price (number|null).
    - underlying_security_title (str|null), underlying_shares (number|null).
    - exercise_date (datetime|null), expiration_date (datetime|null).
  - footnotes[]: { footnote_id (str), text (str) } referenced from transaction rows.
- meta.total: integer — total number of filings.
- meta.page.offset / meta.page.limit: applied pagination.
- links.next: string or null — URL for the next page (null on the last page).

## Example request
```bash
curl "https://eodhd.com/api/sec-filings/AAPL/form4?api_token=YOUR_API_KEY&page[limit]=20"
```

### Example response
```json
{
  "data": [
    {
      "accession_number": "0001140361-26-020871",
      "filed_at": "2026-05-12",
      "period_of_report": "2026-05-08",
      "non_derivative": [
        {
          "reporting_owner_cik": "0002100523",
          "reporting_owner_name": "Borders Ben",
          "is_officer": false,
          "officer_title": "Principal Accounting Officer",
          "security_title": "Common Stock",
          "transaction_date": "2026-05-08T00:00:00+00:00",
          "transaction_code": "S",
          "acquired_or_disposed": "D",
          "shares_amount": 1274,
          "price_per_share": 290,
          "shares_owned_after": 38713,
          "total_value": 369460
        }
      ],
      "derivative": [],
      "footnotes": [
        { "footnote_id": "F1", "text": "Transaction made pursuant to a Rule 10b5-1 trading plan." }
      ]
    }
  ],
  "meta": { "total": 594, "page": { "offset": 0, "limit": 20 } },
  "links": { "next": "https://eodhd.com/api/sec-filings/AAPL.US/form4?page%5Boffset%5D=20&page%5Blimit%5D=20" }
}
```

## Notes
- API call consumption: 10 calls per request.
- Available on the Fundamentals and All-in-One plans.
- US-only — non-US issuers without a US listing return 404.
- History depth varies by ticker. Large caps (AAPL, MSFT, NVDA, KO, GME) have 5–11 years of
  history; recently onboarded issuers and ADRs may expose ~12 months, with backfill ongoing.
- Daily refresh from SEC EDGAR. Insider activity clusters around earnings; the absence of
  filings during the 4–6 weeks before earnings (blackout periods) is expected.
- Forward-only pagination: only `links.next` is exposed. Increment `page[offset]` directly
  (using `meta.total`) to reach a specific page.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Response includes `data`, `meta`, and `links`. |
| **401** | Unauthorized | Missing or invalid `api_token`. |
| **403** | Forbidden | Plan does not include access to this endpoint. |
| **404** | Not Found | Symbol not in the Form 4 dataset (non-US issuer, typo, or unknown share class). |
| **422** | Unprocessable Entity | Validation error — `page[limit]` > 100, negative offset, or `page` passed as a scalar. |
| **429** | Too Many Requests | Rate limit exceeded. Slow down requests. |

### Error Response Format

When an error occurs, the API returns a JSON response with error details:

```json
{
  "error": "Error message description",
  "code": 404
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
            print("Error: Plan does not include the SEC Form 4 endpoint.")
        elif e.response.status_code == 404:
            print("Error: Symbol not found in the Form 4 dataset (US issuers only).")
        elif e.response.status_code == 422:
            print("Error: page[limit] > 100, negative offset, or page passed as a scalar.")
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
- Walk `links.next` (or increment `page[offset]`) to page through a company's filing history
- Cache responses to reduce API calls — each request consumes 10 API calls
