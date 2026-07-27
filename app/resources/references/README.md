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
| 2 | Endpoint Documentation | 1–64 | Per-endpoint API reference |
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

### Type 2 — Endpoint Documentation (ids 1–64)

| ID | Page |
|----|------|
| 1 | Bulk Fundamentals |
| 2 | CBOE Index Data |
| 3 | CBOE Indices List |
| 4 | Company News |
| 5 | Earnings Trends |
| 6 | Economic Events |
| 7 | Exchange Details |
| 8 | Exchange Tickers |
| 9 | Exchanges List |
| 10 | Fundamentals Data |
| 11 | Historical Market Cap |
| 12 | Historical Stock Prices |
| 13 | Index Components |
| 14 | Indices List |
| 15 | Insider Transactions |
| 16 | Intraday Historical Data |
| 17 | Investverte ESG List Companies |
| 18 | Investverte ESG List Countries |
| 19 | Investverte ESG List Sectors |
| 20 | Investverte ESG View Company |
| 21 | Investverte ESG View Country |
| 22 | Investverte ESG View Sector |
| 23 | Live Price Data |
| 24 | Macro Indicator |
| 25 | Marketplace Tick Data |
| 26 | News Word Weights |
| 27 | PRAAMS Bank Balance Sheet By ISIN |
| 28 | PRAAMS Bank Balance Sheet By Ticker |
| 29 | PRAAMS Bank Income Statement By ISIN |
| 30 | PRAAMS Bank Income Statement By Ticker |
| 31 | PRAAMS Bond Analyze By ISIN |
| 32 | PRAAMS Report Bond By ISIN |
| 33 | PRAAMS Report Equity By ISIN |
| 34 | PRAAMS Report Equity By Ticker |
| 35 | PRAAMS Risk Scoring By ISIN |
| 36 | PRAAMS Risk Scoring By Ticker |
| 37 | PRAAMS Smart Investment Screener Bond |
| 38 | PRAAMS Smart Investment Screener Equity |
| 39 | Sentiment Data |
| 40 | Stock Market Logos |
| 41 | Stock Market Logos SVG |
| 42 | Stock Screener Data |
| 43 | Stocks From Search |
| 44 | Symbol Change History |
| 45 | Technical Indicators |
| 46 | TradingHours List Markets |
| 47 | TradingHours Lookup Markets |
| 48 | TradingHours Market Details |
| 49 | TradingHours Market Status |
| 50 | Upcoming Dividends |
| 51 | Upcoming Earnings |
| 52 | Upcoming IPOs |
| 53 | Upcoming Splits |
| 54 | US Live Extended Quotes |
| 55 | US Options Contracts |
| 56 | US Options EOD |
| 57 | US Options Underlyings |
| 58 | US Tick Data |
| 59 | UST Bill Rates |
| 60 | UST Long-Term Rates |
| 61 | UST Real Yield Rates |
| 62 | UST Yield Rates |
| 63 | User Details |
| 64 | WebSockets Realtime |

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
