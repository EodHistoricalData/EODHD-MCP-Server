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
| 2 | Endpoint Documentation | 1–72 | Per-endpoint API reference |
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

### Type 2 — Endpoint Documentation (ids 1–72)

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
| 13 | Illio Market Insights Best Worst |
| 14 | Illio Market Insights Beta Bands |
| 15 | Illio Market Insights Largest Volatility |
| 16 | Illio Market Insights Performance |
| 17 | Illio Market Insights Risk Return |
| 18 | Illio Market Insights Volatility |
| 19 | Illio Performance Insights |
| 20 | Illio Risk Insights |
| 21 | Index Components |
| 22 | Indices List |
| 23 | Insider Transactions |
| 24 | Intraday Historical Data |
| 25 | Investverte ESG List Companies |
| 26 | Investverte ESG List Countries |
| 27 | Investverte ESG List Sectors |
| 28 | Investverte ESG View Company |
| 29 | Investverte ESG View Country |
| 30 | Investverte ESG View Sector |
| 31 | Live Price Data |
| 32 | Macro Indicator |
| 33 | Marketplace Tick Data |
| 34 | News Word Weights |
| 35 | PRAAMS Bank Balance Sheet By ISIN |
| 36 | PRAAMS Bank Balance Sheet By Ticker |
| 37 | PRAAMS Bank Income Statement By ISIN |
| 38 | PRAAMS Bank Income Statement By Ticker |
| 39 | PRAAMS Bond Analyze By ISIN |
| 40 | PRAAMS Report Bond By ISIN |
| 41 | PRAAMS Report Equity By ISIN |
| 42 | PRAAMS Report Equity By Ticker |
| 43 | PRAAMS Risk Scoring By ISIN |
| 44 | PRAAMS Risk Scoring By Ticker |
| 45 | PRAAMS Smart Investment Screener Bond |
| 46 | PRAAMS Smart Investment Screener Equity |
| 47 | Sentiment Data |
| 48 | Stock Market Logos |
| 49 | Stock Market Logos SVG |
| 50 | Stock Screener Data |
| 51 | Stocks From Search |
| 52 | Symbol Change History |
| 53 | Technical Indicators |
| 54 | TradingHours List Markets |
| 55 | TradingHours Lookup Markets |
| 56 | TradingHours Market Details |
| 57 | TradingHours Market Status |
| 58 | Upcoming Dividends |
| 59 | Upcoming Earnings |
| 60 | Upcoming IPOs |
| 61 | Upcoming Splits |
| 62 | US Live Extended Quotes |
| 63 | US Options Contracts |
| 64 | US Options EOD |
| 65 | US Options Underlyings |
| 66 | US Tick Data |
| 67 | UST Bill Rates |
| 68 | UST Long-Term Rates |
| 69 | UST Real Yield Rates |
| 70 | UST Yield Rates |
| 71 | User Details |
| 72 | WebSockets Realtime |

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
