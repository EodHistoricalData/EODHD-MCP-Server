# app/models.py
"""
Pydantic models for EODHD MCP Server API responses.
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# --- Stock Price Models ---

class StockPrice(BaseModel):
    """End-of-day stock price data."""
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: Optional[float] = Field(None, alias="adjusted_close")
    volume: int


class LiveQuote(BaseModel):
    """Real-time or delayed quote."""
    code: str
    timestamp: int
    gmtoffset: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    previousClose: Optional[float] = None
    change: Optional[float] = None
    change_p: Optional[float] = None


class IntradayBar(BaseModel):
    """Intraday OHLCV bar."""
    timestamp: int
    gmtoffset: int
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: int


# --- Fundamentals Models ---

class CompanyGeneral(BaseModel):
    """Company general information."""
    Code: Optional[str] = None
    Type: Optional[str] = None
    Name: Optional[str] = None
    Exchange: Optional[str] = None
    CurrencyCode: Optional[str] = None
    CurrencyName: Optional[str] = None
    CurrencySymbol: Optional[str] = None
    CountryName: Optional[str] = None
    CountryISO: Optional[str] = None
    ISIN: Optional[str] = None
    CUSIP: Optional[str] = None
    CIK: Optional[str] = None
    Sector: Optional[str] = None
    Industry: Optional[str] = None
    Description: Optional[str] = None
    FullTimeEmployees: Optional[int] = None
    WebURL: Optional[str] = None
    LogoURL: Optional[str] = None
    Phone: Optional[str] = None
    Address: Optional[str] = None


class Highlights(BaseModel):
    """Company financial highlights."""
    MarketCapitalization: Optional[float] = None
    MarketCapitalizationMln: Optional[float] = None
    EBITDA: Optional[float] = None
    PERatio: Optional[float] = None
    PEGRatio: Optional[float] = None
    WallStreetTargetPrice: Optional[float] = None
    BookValue: Optional[float] = None
    DividendShare: Optional[float] = None
    DividendYield: Optional[float] = None
    EarningsShare: Optional[float] = None
    EPSEstimateCurrentYear: Optional[float] = None
    EPSEstimateNextYear: Optional[float] = None
    EPSEstimateNextQuarter: Optional[float] = None
    ProfitMargin: Optional[float] = None
    OperatingMarginTTM: Optional[float] = None
    ReturnOnAssetsTTM: Optional[float] = None
    ReturnOnEquityTTM: Optional[float] = None
    RevenueTTM: Optional[float] = None
    RevenuePerShareTTM: Optional[float] = None
    QuarterlyRevenueGrowthYOY: Optional[float] = None
    GrossProfitTTM: Optional[float] = None
    DilutedEpsTTM: Optional[float] = None
    QuarterlyEarningsGrowthYOY: Optional[float] = None


class Valuation(BaseModel):
    """Company valuation metrics."""
    TrailingPE: Optional[float] = None
    ForwardPE: Optional[float] = None
    PriceSalesTTM: Optional[float] = None
    PriceBookMRQ: Optional[float] = None
    EnterpriseValue: Optional[float] = None
    EnterpriseValueRevenue: Optional[float] = None
    EnterpriseValueEbitda: Optional[float] = None


# --- News Models ---

class NewsArticle(BaseModel):
    """News article."""
    date: str
    title: str
    content: Optional[str] = None
    link: Optional[str] = None
    symbols: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    sentiment: Optional[dict] = None


# --- Calendar Models ---

class EarningsEvent(BaseModel):
    """Earnings calendar event."""
    code: str
    report_date: Optional[str] = None
    date: Optional[str] = None
    before_after_market: Optional[str] = None
    currency: Optional[str] = None
    actual: Optional[float] = None
    estimate: Optional[float] = None
    difference: Optional[float] = None
    percent: Optional[float] = None


class IPOEvent(BaseModel):
    """IPO calendar event."""
    code: Optional[str] = None
    name: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    filing_date: Optional[str] = None
    amended_date: Optional[str] = None
    price_from: Optional[float] = None
    price_to: Optional[float] = None
    offer_price: Optional[float] = None
    shares: Optional[int] = None
    deal_type: Optional[str] = None


class DividendEvent(BaseModel):
    """Dividend calendar event."""
    code: str
    ex_date: Optional[str] = None
    payment_date: Optional[str] = None
    record_date: Optional[str] = None
    declaration_date: Optional[str] = None
    value: Optional[float] = None
    unadjusted_value: Optional[float] = None
    currency: Optional[str] = None


class SplitEvent(BaseModel):
    """Stock split event."""
    code: str
    date: Optional[str] = None
    split: Optional[str] = None
    optionable: Optional[str] = None


# --- Options Models ---

class OptionContract(BaseModel):
    """Option contract data."""
    contractName: Optional[str] = None
    contractSize: Optional[str] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    expirationDate: Optional[str] = None
    strike: Optional[float] = None
    lastPrice: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    change: Optional[float] = None
    changePercent: Optional[float] = None
    volume: Optional[int] = None
    openInterest: Optional[int] = None
    impliedVolatility: Optional[float] = None


# --- Exchange Models ---

class Exchange(BaseModel):
    """Exchange information."""
    Name: str
    Code: str
    Country: Optional[str] = None
    Currency: Optional[str] = None
    CountryISO2: Optional[str] = None
    CountryISO3: Optional[str] = None


class Ticker(BaseModel):
    """Ticker/symbol information."""
    Code: str
    Name: Optional[str] = None
    Country: Optional[str] = None
    Exchange: Optional[str] = None
    Currency: Optional[str] = None
    Type: Optional[str] = None
    ISIN: Optional[str] = None


# --- Technical Indicator Models ---

class TechnicalIndicator(BaseModel):
    """Technical indicator data point."""
    date: str
    value: Optional[float] = None
    values: Optional[dict[str, float]] = None


# --- Screener Models ---

class ScreenerResult(BaseModel):
    """Stock screener result."""
    code: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None


# --- Insider Trading Models ---

class InsiderTransaction(BaseModel):
    """Insider transaction record."""
    code: Optional[str] = None
    transaction_date: Optional[str] = None
    reported_date: Optional[str] = None
    owner_name: Optional[str] = None
    owner_title: Optional[str] = None
    transaction_type: Optional[str] = None
    securities_transacted: Optional[float] = None
    securities_owned: Optional[float] = None
    price: Optional[float] = None
    value: Optional[float] = None


# --- ESG Models ---

class ESGScore(BaseModel):
    """ESG score data."""
    code: Optional[str] = None
    total_score: Optional[float] = None
    environment_score: Optional[float] = None
    social_score: Optional[float] = None
    governance_score: Optional[float] = None
    controversy_level: Optional[int] = None


# --- Analyst Rating Models ---

class AnalystRating(BaseModel):
    """Analyst rating and price target."""
    code: Optional[str] = None
    date: Optional[str] = None
    firm: Optional[str] = None
    analyst: Optional[str] = None
    rating: Optional[str] = None
    rating_before: Optional[str] = None
    price_target: Optional[float] = None
    price_target_before: Optional[float] = None


# --- Response Wrapper ---

class APIResponse(BaseModel):
    """Generic API response wrapper."""
    data: Any = None
    error: Optional[str] = None
    meta: Optional[dict] = None

    class Config:
        extra = "allow"
