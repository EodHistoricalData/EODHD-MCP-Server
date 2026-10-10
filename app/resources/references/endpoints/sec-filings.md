# SEC Filings API

Status: complete
Source: financial-apis (SEC Filings API)
Docs: https://eodhd.com/financial-apis/sec-filings-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /sec-filings/{symbol}[/{form}]
Method: GET
Auth: api_token (query)

## Purpose

Returns parsed US SEC filing data for a single company. Four endpoints share the same base path:

- `/sec-filings/{symbol}` — **overview**: how many filings of each type exist and the latest of each.
- `/sec-filings/{symbol}/10k` — **annual reports (10-K)**, with parsed financial statements.
- `/sec-filings/{symbol}/10q` — **quarterly reports (10-Q)**, with parsed financial statements.
- `/sec-filings/{symbol}/8k` — **material events (8-K)**: item codes, sections, and exhibits.

Financial-statement fields are parsed from the filing itself, so any individual field may be
`null` when the filing does not report it. This dataset is distinct from the SEC Form 4
insider-transaction feed (see the Insider Transactions API).

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key for authentication |
| symbol (path) | Yes | string | US-listed ticker, e.g. `AAPL` or `AAPL.US`. The `.US` suffix is optional. |
| form (path) | No | string | Filing type segment: `10k`, `10q`, or `8k`. Omit for the overview. |
| page[offset] | No | integer | Pagination offset (default 0). List endpoints only. |
| page[limit] | No | integer | Records per page (default 20, maximum 100). List endpoints only. |

The overview endpoint (`form` omitted) is not paginated. Pagination uses bracket notation
(`page[offset]`, `page[limit]`); there are no other filter parameters.

## Response (shape)

### Overview — `/sec-filings/{symbol}`

```json
{
  "data": {
    "ticker": "AAPL.US",
    "exchange": "US",
    "name": "Apple Inc.",
    "cik": "0000320193",
    "filings": {
      "10k":   { "count": 12, "latest": "2024-11-01", "url": "https://eodhd.com/api/sec-filings/AAPL.US/10k" },
      "10q":   { "count": 36, "latest": "2025-08-01", "url": "https://eodhd.com/api/sec-filings/AAPL.US/10q" },
      "8k":    { "count": 88, "latest": "2025-09-15", "url": "https://eodhd.com/api/sec-filings/AAPL.US/8k" },
      "form4": { "count": 210, "latest": "2025-09-20", "url": "https://eodhd.com/api/sec-filings/AAPL.US/form4" }
    }
  },
  "meta": {},
  "links": {}
}
```

### Annual / Quarterly — `/sec-filings/{symbol}/10k` and `/10q`

```json
{
  "data": [
    {
      "accession_number": "0000320193-24-000123",
      "filed_at": "2024-11-01",
      "period_of_report": "2024-09-28",
      "fiscal_year_end": "2024-09-28",
      "revenue": 391035000000,
      "cost_of_revenue": 210352000000,
      "gross_profit": 180683000000,
      "operating_income": 123216000000,
      "net_income": 93736000000,
      "ebitda": 134661000000,
      "eps_basic": 6.11,
      "eps_diluted": 6.08,
      "total_assets": 364980000000,
      "total_liabilities": 308030000000,
      "stockholders_equity": 56950000000,
      "operating_cash_flow": 118254000000,
      "capital_expenditure": -9447000000,
      "free_cash_flow": 108807000000
    }
  ],
  "meta": { "total": 12, "page": { "offset": 0, "limit": 20 } },
  "links": { "next": "https://eodhd.com/api/sec-filings/AAPL.US/10k?page[offset]=20&page[limit]=20" }
}
```

The 10-Q payload is identical except the metadata carries `fiscal_quarter_end` (string) and
`fiscal_quarter` (integer, the calendar quarter) instead of `fiscal_year_end`.

**Metadata fields (10-K / 10-Q):** `accession_number`, `filed_at`, `period_of_report`,
`fiscal_year_end` (10-K) / `fiscal_quarter_end` + `fiscal_quarter` (10-Q).

**Parsed financial fields (integer unless noted; any may be null):** `revenue`,
`cost_of_revenue`, `gross_profit`, `research_and_development`, `selling_general_admin`,
`operating_expenses`, `operating_income`, `interest_expense`, `interest_income`,
`income_before_tax`, `income_tax_expense`, `net_income`, `ebitda`, `depreciation_amortization`,
`eps_basic` (number), `eps_diluted` (number), `weighted_avg_shares_basic`,
`weighted_avg_shares_diluted`, `shares_outstanding`, `cash_and_equivalents`,
`short_term_investments`, `accounts_receivable`, `inventory`, `total_current_assets`,
`property_plant_equipment`, `goodwill`, `intangible_assets`, `total_assets`, `accounts_payable`,
`short_term_debt`, `total_current_liabilities`, `long_term_debt`, `total_liabilities`,
`common_stock`, `retained_earnings`, `stockholders_equity`, `total_equity`,
`operating_cash_flow`, `capital_expenditure`, `free_cash_flow`, `investing_cash_flow`,
`financing_cash_flow`, `dividends_paid`, `share_repurchase`.

### Material events — `/sec-filings/{symbol}/8k`

```json
{
  "data": [
    {
      "accession_number": "0000320193-25-000098",
      "filed_at": "2025-09-15",
      "period_of_report": "2025-09-15",
      "items": ["2.02", "9.01"],
      "item_sections": [
        { "item": "2.02", "title": "Results of Operations and Financial Condition", "text": "..." }
      ],
      "exhibits": [
        { "number": "99.1", "description": "Press release dated September 15, 2025" }
      ]
    }
  ],
  "meta": { "total": 88, "page": { "offset": 0, "limit": 20 } },
  "links": { "next": "https://eodhd.com/api/sec-filings/AAPL.US/8k?page[offset]=20&page[limit]=20" }
}
```

**8-K data item fields:** `accession_number`, `filed_at`, `period_of_report`, `items` (list of
item codes), `item_sections` (list of `{item, title, text}`), `exhibits` (list of
`{number, description}`).

## Example Requests

```
# Overview — what has Apple filed?
https://eodhd.com/api/sec-filings/AAPL.US?api_token=YOUR_TOKEN

# Latest annual report (10-K)
https://eodhd.com/api/sec-filings/AAPL.US/10k?api_token=YOUR_TOKEN&page[limit]=1

# Recent quarterly reports (10-Q)
https://eodhd.com/api/sec-filings/AAPL.US/10q?api_token=YOUR_TOKEN

# Recent material events (8-K), first 5
https://eodhd.com/api/sec-filings/AAPL.US/8k?api_token=YOUR_TOKEN&page[limit]=5
```

## Notes

- The `.US` suffix on the symbol is optional; `AAPL` and `AAPL.US` both work.
- The overview endpoint is not paginated; `page[offset]`/`page[limit]` apply only to `10k`/`10q`/`8k`.
- Parsed financial fields are extracted from the filing and may be `null` when a filing does not
  report a given line item.
- Form 4 insider transactions are a separate product — use the Insider Transactions API for those.
- API call consumption: 10 calls per request.
- Access requires the All-in-One plan.

## HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 200 | OK | Request succeeded. Body carries data (object for overview, array for list endpoints), meta, and links. |
| 401 | Unauthorized | Missing or invalid `api_token`. |
| 403 | Forbidden | Plan does not include SEC Filings (requires All-in-One). |
| 404 | Not Found | Unknown symbol or filing type. |
| 422 | Unprocessable Entity | Invalid parameter — page[limit] out of range or non-integer pagination value. |
| 429 | Too Many Requests | Exceeded rate limit. |
