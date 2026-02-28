"""Market data fetching via yfinance with Streamlit caching."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf
from db import cache_fx, get_cached_fx


# ---------------------------------------------------------------------------
# Cached fetchers (15-min TTL for live data)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def get_current_price(ticker: str) -> dict | None:
    """Return current price info for a single ticker.

    Returns dict with keys: price, prev_close, change_pct, high_52w, low_52w,
    change_52w, change_30d, change_7d, pe, eps, currency, name.
    """
    try:
        t = yf.Ticker(ticker)
        try:
            info = t.info or {}
        except Exception:
            info = {}

        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if price is None:
            hist = t.history(period="5d")
            if hist.empty:
                return None
            price = float(hist["Close"].iloc[-1])

        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        high_52w = info.get("fiftyTwoWeekHigh")
        low_52w = info.get("fiftyTwoWeekLow")

        # Percentage changes over periods
        hist_1y = t.history(period="1y")
        change_52w = _pct_change_over(hist_1y, 252)
        change_30d = _pct_change_over(hist_1y, 22)
        change_7d = _pct_change_over(hist_1y, 5)

        # Convert pence (GBp) to pounds (GBP) for LSE stocks
        # All .L tickers on yfinance are quoted in pence regardless of
        # what the currency field reports (sometimes "GBp", sometimes "GBP")
        reported_currency = info.get("currency", "")
        if ticker.endswith(".L") or reported_currency == "GBp":
            _GBP_PENCE_TICKERS.add(ticker)
            price = price / 100.0
            if prev_close:
                prev_close = prev_close / 100.0
            if high_52w:
                high_52w = high_52w / 100.0
            if low_52w:
                low_52w = low_52w / 100.0
            # Recalculate change_pct (percentages stay the same, but recalc for safety)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
            reported_currency = "GBP"

        return {
            "price": price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "change_52w": change_52w,
            "change_30d": change_30d,
            "change_7d": change_7d,
            "pe": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "currency": reported_currency,
            "name": info.get("shortName", ticker),
        }
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def get_multiple_prices(tickers: tuple) -> dict:
    """Fetch current price info for multiple tickers. Returns {ticker: info_dict}."""
    results = {}
    for t in tickers:
        data = get_current_price(t)
        if data:
            results[t] = data
    return results


# Tickers whose Yahoo Finance currency is GBp (pence) — needs /100 conversion
_GBP_PENCE_TICKERS: set[str] = set()


@st.cache_data(ttl=3600, show_spinner=False)
def get_historical_prices(ticker: str, start: str, end: str = None) -> pd.DataFrame:
    """Fetch daily historical close prices. Returns DataFrame with Date index and Close column."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end or datetime.now().strftime("%Y-%m-%d"))
        if hist.empty:
            return pd.DataFrame()
        df = hist[["Close"]].copy()
        df.index = df.index.tz_localize(None)
        # Convert pence to pounds for LSE stocks
        is_gbp_pence = ticker in _GBP_PENCE_TICKERS or ticker.endswith(".L")
        if not is_gbp_pence:
            try:
                is_gbp_pence = (t.info or {}).get("currency") == "GBp"
            except Exception:
                pass
        if is_gbp_pence:
            df["Close"] = df["Close"] / 100.0
            _GBP_PENCE_TICKERS.add(ticker)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rate(pair_ticker: str = "GBPUSD=X") -> float | None:
    """Get the latest FX rate for a yfinance currency pair ticker."""
    try:
        t = yf.Ticker(pair_ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_historical_fx(pair_ticker: str, start: str, end: str = None) -> pd.DataFrame:
    """Fetch historical FX rates. Returns DataFrame with Date index and Close column."""
    return get_historical_prices(pair_ticker, start, end)


@st.cache_data(ttl=86400, show_spinner=False)
def get_fx_rate_on_date(pair_ticker: str, fx_date: str) -> float | None:
    """Get FX close rate for a date (or prior trading day if market closed)."""
    cached = get_cached_fx(pair_ticker, fx_date)
    if cached:
        return float(cached)

    try:
        dt = datetime.strptime(fx_date, "%Y-%m-%d")
    except ValueError:
        return None

    start = (dt - timedelta(days=7)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    hist = get_historical_prices(pair_ticker, start=start, end=end)
    if hist.empty:
        return None

    target = dt.date()
    try:
        same_day = hist[hist.index.date == target]
        if not same_day.empty:
            rate = float(same_day["Close"].iloc[-1])
            cache_fx(pair_ticker, fx_date, rate)
            return rate
    except Exception:
        pass

    prior = hist[hist.index.date <= target]
    if prior.empty:
        return None
    rate = float(prior["Close"].iloc[-1])
    cache_fx(pair_ticker, fx_date, rate)
    return rate


@st.cache_data(ttl=900, show_spinner=False)
def get_ticker_news(ticker: str, limit: int = 5) -> list[dict]:
    """Get recent news items for a ticker using yfinance."""
    try:
        t = yf.Ticker(ticker)
        items = t.news or []
        out = []
        for item in items[:limit]:
            content = item.get("content", {}) if isinstance(item, dict) else {}
            pub_ts = content.get("pubDate")
            source = (content.get("provider") or {}).get("displayName", "")
            title = content.get("title", "") or item.get("title", "")
            link = (
                content.get("canonicalUrl", {}).get("url")
                or content.get("clickThroughUrl", {}).get("url")
                or item.get("link")
                or ""
            )
            out.append({
                "title": title,
                "source": source,
                "published": pub_ts,
                "link": link,
            })
        return out
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct_change_over(hist: pd.DataFrame, trading_days: int) -> float | None:
    """Calculate percentage change over N trading days from history."""
    if hist.empty or len(hist) < 2:
        return None
    current = float(hist["Close"].iloc[-1])
    idx = min(trading_days, len(hist) - 1)
    past = float(hist["Close"].iloc[-1 - idx])
    if past == 0:
        return None
    return (current - past) / past * 100


def usd_to_gbp(usd_amount: float, gbp_usd_rate: float | None = None) -> float:
    """Convert USD to GBP. If rate not provided, fetches live rate."""
    if gbp_usd_rate is None:
        gbp_usd_rate = get_fx_rate("GBPUSD=X")
    if gbp_usd_rate and gbp_usd_rate > 0:
        return usd_amount / gbp_usd_rate
    return usd_amount  # fallback: no conversion
