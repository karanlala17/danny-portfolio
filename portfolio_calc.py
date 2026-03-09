"""Portfolio calculations: holdings aggregation, P&L, XIRR, NAV time series."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

import pandas as pd
import streamlit as st
from pyxirr import xirr

from db import get_transactions
from market_data import (
    get_current_price,
    get_fx_rate,
    get_historical_prices,
    get_historical_fx,
)


def _to_gbp(amount, currency, fx_rate):
    """Convert amount to GBP. For GBP, return as-is. For USD, divide by GBP/USD rate."""
    if currency == "GBP":
        return amount
    return amount / fx_rate if fx_rate else amount


def _to_date(value):
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    return value


def _txn_sort_key(txn: dict):
    return (_to_date(txn["date"]), int(txn.get("id", 0)))


# ---------------------------------------------------------------------------
# Specific transaction matching overrides (bypass FIFO)
# Maps sell_transaction_id -> buy_transaction_id
# ---------------------------------------------------------------------------
MATCHED_TRANSACTIONS: dict[int, int] = {
    96: 95,  # NVIDIA: 35-share sell (ID 96) matched against 35-share buy (ID 95)
}


# ---------------------------------------------------------------------------
# Holdings aggregation
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def compute_holdings() -> list[dict]:
    """Compute current holdings from all transactions (FIFO, per ticker+broker)."""
    txns = get_transactions()
    if not txns:
        return []

    txn_list = sorted([dict(t) for t in txns], key=_txn_sort_key)
    gbp_usd = get_fx_rate("GBPUSD=X") or 1.27

    groups = defaultdict(list)
    for t in txn_list:
        groups[(t["ticker"], t["broker"])].append(t)

    price_cache = {}
    holdings = []

    for (ticker, broker), lot_txns in groups.items():
        buys = []
        realized_pnl_gbp = 0.0
        realized_cost_gbp = 0.0
        realized_proceeds_gbp = 0.0
        realized_cost_native = 0.0
        realized_proceeds_native = 0.0
        realized_pnl_native = 0.0

        display_name = lot_txns[0]["display_name"]
        currency = lot_txns[0]["currency"]

        for t in lot_txns:
            qty = float(t["quantity"])
            price = float(t["price_per_share"])
            fx = float(t["exchange_rate_to_gbp"] or 1.0)

            if t["action"] == "BUY":
                buys.append({
                    "qty": qty,
                    "price": price,
                    "fx": fx,
                    "date": t["date"],
                    "id": int(t.get("id", 0)),
                })
                continue

            sell_id = int(t.get("id", 0))
            sell_qty = qty

            # Check for specific transaction matching override
            matched_buy_id = MATCHED_TRANSACTIONS.get(sell_id)
            if matched_buy_id is not None:
                for i, buy in enumerate(buys):
                    if buy["id"] == matched_buy_id:
                        matched = min(sell_qty, buy["qty"])

                        cost_n = matched * buy["price"]
                        proceeds_n = matched * price
                        cost_gbp = _to_gbp(cost_n, currency, buy["fx"])
                        proceeds_gbp = _to_gbp(proceeds_n, currency, fx)

                        realized_cost_native += cost_n
                        realized_proceeds_native += proceeds_n
                        realized_pnl_native += (proceeds_n - cost_n)
                        realized_cost_gbp += cost_gbp
                        realized_proceeds_gbp += proceeds_gbp
                        realized_pnl_gbp += (proceeds_gbp - cost_gbp)

                        buy["qty"] -= matched
                        sell_qty -= matched
                        if buy["qty"] <= 0:
                            buys.pop(i)
                        break

            # Standard FIFO for remaining sell quantity
            while sell_qty > 0 and buys:
                buy = buys[0]
                matched = min(sell_qty, buy["qty"])

                cost_n = matched * buy["price"]
                proceeds_n = matched * price
                cost_gbp = _to_gbp(cost_n, currency, buy["fx"])
                proceeds_gbp = _to_gbp(proceeds_n, currency, fx)

                realized_cost_native += cost_n
                realized_proceeds_native += proceeds_n
                realized_pnl_native += (proceeds_n - cost_n)
                realized_cost_gbp += cost_gbp
                realized_proceeds_gbp += proceeds_gbp
                realized_pnl_gbp += (proceeds_gbp - cost_gbp)

                buy["qty"] -= matched
                sell_qty -= matched
                if buy["qty"] <= 0:
                    buys.pop(0)

        total_qty = sum(b["qty"] for b in buys)
        if total_qty <= 0 and realized_pnl_gbp == 0:
            continue

        if ticker not in price_cache:
            info = get_current_price(ticker)
            price_cache[ticker] = float(info["price"]) if info else 0.0
        current_price = price_cache[ticker]

        current_fx_rate = gbp_usd if currency == "USD" else 1.0

        if total_qty > 0:
            total_cost_native = sum(b["qty"] * b["price"] for b in buys)
            total_cost_gbp = sum(_to_gbp(b["qty"] * b["price"], currency, b["fx"]) for b in buys)
            avg_cost_native = total_cost_native / total_qty
            avg_cost_gbp = total_cost_gbp / total_qty

            market_value_native = total_qty * current_price
            current_price_gbp = _to_gbp(current_price, currency, current_fx_rate)
            market_value_gbp = total_qty * current_price_gbp

            unrealized_pnl_native = market_value_native - total_cost_native
            # Convert txn-currency P&L to GBP at current rate (not cost-GBP minus value-GBP)
            unrealized_pnl_gbp = _to_gbp(unrealized_pnl_native, currency, current_fx_rate)
            unrealized_pnl_pct = (unrealized_pnl_native / total_cost_native * 100) if total_cost_native else 0.0
        else:
            total_cost_native = 0.0
            total_cost_gbp = 0.0
            avg_cost_native = 0.0
            avg_cost_gbp = 0.0
            market_value_native = 0.0
            current_price_gbp = 0.0
            market_value_gbp = 0.0
            unrealized_pnl_native = 0.0
            unrealized_pnl_gbp = 0.0
            unrealized_pnl_pct = 0.0

        realized_pnl_pct = (realized_pnl_native / realized_cost_native * 100) if realized_cost_native else None
        xirr_val = _compute_xirr_native(lot_txns, current_price, total_qty)

        holdings.append({
            "ticker": ticker,
            "display_name": display_name,
            "broker": broker,
            "currency": currency,
            "quantity": total_qty,
            # Native values
            "avg_cost": avg_cost_native,
            "total_cost": total_cost_native,
            "current_price": current_price,
            "market_value": market_value_native,
            "unrealized_pnl": unrealized_pnl_native,
            # GBP values
            "avg_cost_gbp": avg_cost_gbp,
            "total_cost_gbp": total_cost_gbp,
            "current_price_gbp": current_price_gbp,
            "market_value_gbp": market_value_gbp,
            "unrealized_pnl_gbp": unrealized_pnl_gbp,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "realized_cost_native": realized_cost_native,
            "realized_proceeds_native": realized_proceeds_native,
            "realized_pnl_native": realized_pnl_native,
            "realized_cost_gbp": realized_cost_gbp,
            "realized_proceeds_gbp": realized_proceeds_gbp,
            "realized_pnl_gbp": realized_pnl_gbp,
            "realized_pnl_pct": realized_pnl_pct,
            "xirr": xirr_val,
            "current_fx_rate": current_fx_rate,
        })

    return holdings


# ---------------------------------------------------------------------------
# Per-trade profitability (FIFO, per ticker+broker)
# ---------------------------------------------------------------------------

def compute_trade_profitability() -> list[dict]:
    """Return matched BUY/SELL lots with FIFO profitability per ticker and broker."""
    txns = get_transactions()
    if not txns:
        return []

    txn_list = sorted([dict(t) for t in txns], key=_txn_sort_key)
    groups = defaultdict(list)
    for t in txn_list:
        groups[(t["ticker"], t["broker"])].append(t)

    rows = []
    for (ticker, broker), lot_txns in groups.items():
        buys = []
        currency = lot_txns[0]["currency"]
        display_name = lot_txns[0]["display_name"]

        for t in lot_txns:
            qty = float(t["quantity"])
            price = float(t["price_per_share"])
            fx = float(t["exchange_rate_to_gbp"] or 1.0)
            txn_date = _to_date(t["date"])

            if t["action"] == "BUY":
                buys.append({
                    "qty": qty,
                    "price": price,
                    "fx": fx,
                    "date": txn_date,
                    "id": int(t.get("id", 0)),
                })
                continue

            sell_id = int(t.get("id", 0))
            sell_qty = qty

            # Check for specific transaction matching override
            matched_buy_id = MATCHED_TRANSACTIONS.get(sell_id)
            if matched_buy_id is not None:
                for i, buy in enumerate(buys):
                    if buy["id"] == matched_buy_id:
                        matched = min(sell_qty, buy["qty"])
                        cost_native = matched * buy["price"]
                        proceeds_native = matched * price
                        pnl_native = proceeds_native - cost_native
                        cost_gbp = _to_gbp(cost_native, currency, buy["fx"])
                        proceeds_gbp = _to_gbp(proceeds_native, currency, fx)
                        pnl_gbp = proceeds_gbp - cost_gbp
                        pnl_pct = (pnl_native / cost_native * 100) if cost_native else None

                        hold_days = max((txn_date - buy["date"]).days, 1)
                        annualized_pct = None
                        if cost_native > 0 and proceeds_native > 0:
                            gross = proceeds_native / cost_native
                            annualized_pct = (gross ** (365 / hold_days) - 1) * 100

                        rows.append({
                            "ticker": ticker,
                            "display_name": display_name,
                            "broker": broker,
                            "currency": currency,
                            "buy_date": buy["date"],
                            "sell_date": txn_date,
                            "holding_days": hold_days,
                            "qty": matched,
                            "buy_price": buy["price"],
                            "sell_price": price,
                            "cost_native": cost_native,
                            "proceeds_native": proceeds_native,
                            "realized_pnl_native": pnl_native,
                            "cost_gbp": cost_gbp,
                            "proceeds_gbp": proceeds_gbp,
                            "realized_pnl_gbp": pnl_gbp,
                            "realized_pnl_pct": pnl_pct,
                            "annualized_return_pct": annualized_pct,
                        })

                        buy["qty"] -= matched
                        sell_qty -= matched
                        if buy["qty"] <= 0:
                            buys.pop(i)
                        break

            # Standard FIFO for remaining sell quantity
            while sell_qty > 0 and buys:
                buy = buys[0]
                matched = min(sell_qty, buy["qty"])

                cost_native = matched * buy["price"]
                proceeds_native = matched * price
                pnl_native = proceeds_native - cost_native
                cost_gbp = _to_gbp(cost_native, currency, buy["fx"])
                proceeds_gbp = _to_gbp(proceeds_native, currency, fx)
                pnl_gbp = proceeds_gbp - cost_gbp
                pnl_pct = (pnl_native / cost_native * 100) if cost_native else None

                hold_days = max((txn_date - buy["date"]).days, 1)
                annualized_pct = None
                if cost_native > 0 and proceeds_native > 0:
                    gross = proceeds_native / cost_native
                    annualized_pct = (gross ** (365 / hold_days) - 1) * 100

                rows.append({
                    "ticker": ticker,
                    "display_name": display_name,
                    "broker": broker,
                    "currency": currency,
                    "buy_date": buy["date"],
                    "sell_date": txn_date,
                    "holding_days": hold_days,
                    "qty": matched,
                    "buy_price": buy["price"],
                    "sell_price": price,
                    "cost_native": cost_native,
                    "proceeds_native": proceeds_native,
                    "realized_pnl_native": pnl_native,
                    "cost_gbp": cost_gbp,
                    "proceeds_gbp": proceeds_gbp,
                    "realized_pnl_gbp": pnl_gbp,
                    "realized_pnl_pct": pnl_pct,
                    "annualized_return_pct": annualized_pct,
                })

                buy["qty"] -= matched
                sell_qty -= matched
                if buy["qty"] <= 0:
                    buys.pop(0)

    rows.sort(key=lambda r: (r["sell_date"], r["ticker"], r["broker"]), reverse=True)
    return rows


# ---------------------------------------------------------------------------
# XIRR
# ---------------------------------------------------------------------------

def _compute_xirr_native(txns, current_price, current_qty):
    """Compute XIRR in transaction currency for one (ticker, broker)."""
    dates = []
    amounts = []

    for t in sorted(txns, key=_txn_sort_key):
        d = _to_date(t["date"])
        value = float(t["quantity"]) * float(t["price_per_share"])
        amounts.append(-value if t["action"] == "BUY" else value)
        dates.append(d)

    if current_qty > 0 and current_price > 0:
        amounts.append(current_qty * current_price)
        dates.append(date.today())

    if len(dates) < 2:
        return None
    try:
        return xirr(dates, amounts)
    except Exception:
        return None


def compute_cash_on_hand() -> float:
    """Compute current cash on hand from all transactions (GBP).

    BUY reduces cash (or increases investment if cash is insufficient).
    SELL adds cash.
    """
    txns = get_transactions()
    if not txns:
        return 0.0

    txn_list = sorted([dict(t) for t in txns], key=_txn_sort_key)
    cash = 0.0

    for t in txn_list:
        fx = float(t["exchange_rate_to_gbp"] or 1.0)
        amount_gbp = _to_gbp(
            float(t["quantity"]) * float(t["price_per_share"]),
            t["currency"],
            fx,
        )
        if t["action"] == "BUY":
            if cash >= amount_gbp:
                cash -= amount_gbp
            else:
                cash = 0.0
        else:
            cash += amount_gbp

    return cash


def compute_portfolio_xirr() -> float | None:
    """Compute portfolio-level XIRR across all transactions."""
    txns = get_transactions()
    if not txns:
        return None

    txn_list = sorted([dict(t) for t in txns], key=_txn_sort_key)
    dates = []
    amounts = []

    for t in txn_list:
        d = _to_date(t["date"])
        value = _to_gbp(
            float(t["quantity"]) * float(t["price_per_share"]),
            t["currency"],
            float(t["exchange_rate_to_gbp"] or 1.0),
        )
        amounts.append(-value if t["action"] == "BUY" else value)
        dates.append(d)

    terminal_value = sum(
        h["market_value_gbp"] for h in compute_holdings() if float(h["quantity"]) > 0
    )
    if terminal_value > 0:
        amounts.append(float(terminal_value))
        dates.append(date.today())

    if len(dates) < 2:
        return None
    try:
        return xirr(dates, amounts)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# NAV Time Series  (cash-aware, investment tracking)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def compute_nav_series() -> pd.DataFrame:
    """Compute daily NAV components from first transaction date to today."""
    txns = get_transactions()
    if not txns:
        return pd.DataFrame(
            columns=[
                "date",
                "holdings_value",
                "cash_on_hand",
                "nav",
                "investment",
                "profit",
                "gbp_usd_rate",
            ]
        )

    txn_list = sorted([dict(t) for t in txns], key=_txn_sort_key)

    first_date = _to_date(txn_list[0]["date"])
    all_tickers = list({t["ticker"] for t in txn_list})
    ticker_currencies = {t["ticker"]: t["currency"] for t in txn_list}

    start_str = first_date.strftime("%Y-%m-%d")
    price_history = {}
    for ticker in all_tickers:
        hist = get_historical_prices(ticker, start_str)
        if not hist.empty:
            price_history[ticker] = hist["Close"]

    fx_history = get_historical_fx("GBPUSD=X", start_str)
    fx_series = fx_history["Close"] if not fx_history.empty else pd.Series(dtype=float)

    date_range = pd.bdate_range(start=first_date, end=date.today())

    records = []
    holdings = defaultdict(float)       # ticker -> qty
    cost_basis = defaultdict(float)     # ticker -> total cost in native currency
    cost_basis_fx = defaultdict(float)  # ticker -> weighted avg FX at purchase
    cash_on_hand = 0.0
    total_investment = 0.0
    txn_idx = 0

    for d in date_range:
        d_date = d.date()

        while txn_idx < len(txn_list):
            t = txn_list[txn_idx]
            t_date = _to_date(t["date"])
            if t_date > d_date:
                break

            fx = float(t["exchange_rate_to_gbp"] or 1.0)
            qty = float(t["quantity"])
            price = float(t["price_per_share"])
            amount_gbp = _to_gbp(qty * price, t["currency"], fx)

            if t["action"] == "BUY":
                # Track cost basis for fallback pricing
                old_qty = holdings[t["ticker"]]
                old_cost = cost_basis[t["ticker"]]
                holdings[t["ticker"]] += qty
                cost_basis[t["ticker"]] += qty * price
                new_qty = holdings[t["ticker"]]
                if new_qty > 0:
                    cost_basis_fx[t["ticker"]] = (
                        (old_qty * cost_basis_fx.get(t["ticker"], fx) + qty * fx)
                        / new_qty
                    )

                if cash_on_hand >= amount_gbp:
                    cash_on_hand -= amount_gbp
                else:
                    total_investment += (amount_gbp - cash_on_hand)
                    cash_on_hand = 0.0
            else:
                if holdings[t["ticker"]] > 0:
                    # Reduce cost basis proportionally
                    sell_frac = min(qty / holdings[t["ticker"]], 1.0)
                    cost_basis[t["ticker"]] *= (1 - sell_frac)
                holdings[t["ticker"]] -= qty
                cash_on_hand += amount_gbp

            txn_idx += 1

        gbp_usd_rate = _get_rate_on_date(fx_series, d) or 1.27
        holdings_value = 0.0

        for ticker, qty in holdings.items():
            if qty <= 0:
                continue
            price = _get_price_on_date(price_history.get(ticker), d)
            if price is not None:
                holdings_value += _to_gbp(
                    qty * price,
                    ticker_currencies.get(ticker, "USD"),
                    gbp_usd_rate,
                )
            else:
                # Fallback: use cost basis when no market price available
                fallback_fx = cost_basis_fx.get(ticker, gbp_usd_rate)
                holdings_value += _to_gbp(
                    cost_basis.get(ticker, 0.0),
                    ticker_currencies.get(ticker, "USD"),
                    fallback_fx,
                )

        nav = holdings_value + cash_on_hand
        profit = nav - total_investment

        records.append({
            "date": d_date,
            "holdings_value": holdings_value,
            "cash_on_hand": cash_on_hand,
            "nav": nav,
            "investment": total_investment,
            "profit": profit,
            "gbp_usd_rate": gbp_usd_rate,
        })

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_price_on_date(series, d):
    """Get price on date, forward-filling from last available."""
    if series is None or series.empty:
        return None
    try:
        mask = (
            series.index.date == d.date()
            if hasattr(d, "date") else series.index.date == d
        )
        vals = series[mask]
        if not vals.empty:
            return float(vals.iloc[0])
    except Exception:
        pass
    try:
        before = series[series.index <= d]
        if not before.empty:
            return float(before.iloc[-1])
    except Exception:
        pass
    return None


def _get_rate_on_date(series, d):
    """Get FX rate on date, forward-filling."""
    return _get_price_on_date(series, d)


# ---------------------------------------------------------------------------
# Portfolio risk metrics
# ---------------------------------------------------------------------------

def compute_max_drawdown(nav_df: pd.DataFrame = None) -> float | None:
    """Compute maximum drawdown from peak as a percentage."""
    if nav_df is None:
        nav_df = compute_nav_series()
    if nav_df.empty or len(nav_df) < 2:
        return None

    nav = nav_df["nav"]
    running_max = nav.cummax()
    drawdown = (nav - running_max) / running_max * 100
    return float(drawdown.min())


def compute_sharpe_ratio(nav_df: pd.DataFrame = None, risk_free_annual: float = 0.04) -> float | None:
    """Compute annualized Sharpe ratio from daily NAV returns.

    risk_free_annual: annualized risk-free rate (default 4% ~ UK gilts).
    """
    if nav_df is None:
        nav_df = compute_nav_series()
    if nav_df.empty or len(nav_df) < 30:
        return None

    nav = nav_df["nav"]
    daily_returns = nav.pct_change().dropna()
    if daily_returns.std() == 0:
        return None

    daily_rf = (1 + risk_free_annual) ** (1 / 252) - 1
    excess_returns = daily_returns - daily_rf
    sharpe = (excess_returns.mean() / excess_returns.std()) * (252 ** 0.5)
    return float(sharpe)
