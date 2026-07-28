# EODHD Documentation — Global README

This is the global help page for the `retrieve_description_by_id` tool. It provides structured access to all EODHD documentation pages organized by type.

## How to Use

Call `retrieve_description_by_id` with a **type** and an **id** to retrieve a specific documentation page.

- **No parameters** or **type=0** → this global README
- **type=X, id=0** → the README for resource group X
- **type=X, id=N** → a specific documentation page within group X

## Available Types

| Type | Category | ID Range | Description |
|------|----------|----------|-------------|
| 0 | Global README | — | This help page |
| 1 | Subscription Plans | 1–7 | EODHD subscription tiers and features |
| 2 | Endpoint Documentation | 1–82 | Per-endpoint API reference |
| 3 | General Reference | 1–28 | Authentication, formats, guides, FAQ |

## Quick Reference

### Type 1 — Subscription Plans (ids 1–7)

| ID | Page |
|----|------|
| 1 | Free |
| 2 | EOD Historical Data All World |
| 3 | EOD Intraday All World Extended |
| 4 | Fundamentals Data Feed |
| 5 | All-In-One |
| 6 | All-In-One Extended Fundamentals |
| 7 | Calendar Feed |

### Type 2 — Endpoint Documentation (ids 1–82)

| ID | Page |
|----|------|
| 1 | Bulk Fundamentals |
| 2 | CBOE Index Data |
| 3 | CBOE Indices List |
| 4 | Company News |
| 5 | Credit CDS Market Aggregates |
| 6 | Credit Corporate CMDI |
| 7 | Credit Corporate HQM Yields |
| 8 | Credit Sovereign CDS Spreads |
| 9 | Credit Sovereign Credit Ratings |
| 10 | Credit Sovereign Default Spreads |
| 11 | Credit Sovereign Risk Premium |
| 12 | Earnings Trends |
| 13 | Economic Events |
| 14 | Exchange Details |
| 15 | Exchange Tickers |
| 16 | Exchanges List |
| 17 | Fundamentals Data |
| 18 | Historical Market Cap |
| 19 | Historical Stock Prices |
| 20 | Index Components |
| 21 | Indices List |
| 22 | Insider Transactions |
| 23 | Intraday Historical Data |
| 24 | Investverte ESG List Companies |
| 25 | Investverte ESG List Countries |
| 26 | Investverte ESG List Sectors |
| 27 | Investverte ESG View Company |
| 28 | Investverte ESG View Country |
| 29 | Investverte ESG View Sector |
| 30 | Live Price Data |
| 31 | Macro Indicator |
| 32 | Marketplace Tick Data |
| 33 | News Word Weights |
| 34 | PRAAMS Bank Balance Sheet By ISIN |
| 35 | PRAAMS Bank Balance Sheet By Ticker |
| 36 | PRAAMS Bank Income Statement By ISIN |
| 37 | PRAAMS Bank Income Statement By Ticker |
| 38 | PRAAMS Bond Analyze By ISIN |
| 39 | PRAAMS Report Bond By ISIN |
| 40 | PRAAMS Report Equity By ISIN |
| 41 | PRAAMS Report Equity By Ticker |
| 42 | PRAAMS Risk Scoring By ISIN |
| 43 | PRAAMS Risk Scoring By Ticker |
| 44 | PRAAMS Smart Investment Screener Bond |
| 45 | PRAAMS Smart Investment Screener Equity |
| 46 | Rates Funding Stress |
| 47 | Rates Policy Rates |
| 48 | Rates Reference Rates |
| 49 | Real Estate Countries |
| 50 | Real Estate Detailed Prices |
| 51 | Real Estate Detailed Series |
| 52 | Real Estate Selected Prices |
| 53 | Sanctions Entities |
| 54 | Sanctions Programs |
| 55 | Sanctions Sources |
| 56 | Sanctions Vessels |
| 57 | Sentiment Data |
| 58 | Stock Market Logos |
| 59 | Stock Market Logos SVG |
| 60 | Stock Screener Data |
| 61 | Stocks From Search |
| 62 | Symbol Change History |
| 63 | Technical Indicators |
| 64 | TradingHours List Markets |
| 65 | TradingHours Lookup Markets |
| 66 | TradingHours Market Details |
| 67 | TradingHours Market Status |
| 68 | Upcoming Dividends |
| 69 | Upcoming Earnings |
| 70 | Upcoming IPOs |
| 71 | Upcoming Splits |
| 72 | US Live Extended Quotes |
| 73 | US Options Contracts |
| 74 | US Options EOD |
| 75 | US Options Underlyings |
| 76 | US Tick Data |
| 77 | User Details |
| 78 | UST Bill Rates |
| 79 | UST Long-Term Rates |
| 80 | UST Real Yield Rates |
| 81 | UST Yield Rates |
| 82 | WebSockets Realtime |

### Type 3 — General Reference (ids 1–28)

| ID | Page |
|----|------|
| 1 | API Authentication Demo Access |
| 2 | Authentication |
| 3 | Crypto Data Notes |
| 4 | Data Adjustment Guide |
| 5 | Delisted Tickers Guide |
| 6 | Exchanges |
| 7 | Financial Ratios Calculation Guide |
| 8 | Forex Data Notes |
| 9 | Fundamentals API |
| 10 | Fundamentals Common Stock |
| 11 | Fundamentals Crypto Currency |
| 12 | Fundamentals ETF |
| 13 | Fundamentals ETF Metrics |
| 14 | Fundamentals FAQ |
| 15 | Fundamentals Fund |
| 16 | Fundamentals Ratios |
| 17 | General Data FAQ |
| 18 | Glossary |
| 19 | Indices Data Notes |
| 20 | Pricing And Plans |
| 21 | Primary Tickers Guide |
| 22 | Rate Limits |
| 23 | SDKs And Integrations |
| 24 | Special Exchanges Guide |
| 25 | Stock Types Ticker Suffixes Guide |
| 26 | Symbol Format |
| 27 | Update Times |
| 28 | Versioning |

## Fallback Behavior

If you provide an invalid `type` or `id`, the tool returns this global README with `"fallback": true` in the JSON response. This lets you know you received help text instead of the requested page.

## Examples

```
retrieve_description_by_id()                    → this global README
retrieve_description_by_id(type=0)              → this global README
retrieve_description_by_id(type=1, id=0)        → subscriptions README
retrieve_description_by_id(type=2, id=10)       → Fundamentals Data endpoint docs
retrieve_description_by_id(type=3, id=2)        → Authentication guide
retrieve_description_by_id(type=99, id=1)       → this global README (fallback)
```
