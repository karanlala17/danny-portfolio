"""Danny Portfolio Dashboard — main entry point."""

import streamlit as st

st.set_page_config(page_title="Portfolio Dashboard", page_icon="📊", layout="wide")

from db import init_db, is_seeded
from seed_data import seed_all

# ---------------------------------------------------------------------------
# Auto-init and seed on first run
# ---------------------------------------------------------------------------

init_db()

if not is_seeded():
    with st.spinner("First run — seeding database with existing transactions..."):
        seed_all()

# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------

st.title("Danny Jatania's Portfolio Dashboard")
st.caption("Prepared by Karan Lala")
st.markdown("---")

st.markdown("""
Welcome to your portfolio dashboard. Use the sidebar to navigate:

- **World Indices** — Live prices for major global indices and currency rates
- **Stock Watchlist** — Track daily moves for securities of interest
- **Portfolio Summary** — Broker-wise and currency-wise holdings with P&L and XIRR
- **Transactions** — View buy/sell transactions
- **NAV Chart** — Portfolio net asset value over time
- **Trade Profitability** — FIFO matched per-trade results by ticker and broker
- **News** — Ticker-wise watchlist news and summaries

USD positions are converted to GBP.
Dates are displayed in dd-mm-yyyy format.
""")

# Quick stats
st.subheader("Quick Overview")

from portfolio_calc import compute_holdings, compute_cash_on_hand, compute_portfolio_xirr, compute_nav_series

def compact_gbp(value: float) -> str:
    sign = "-" if value < 0 else ""
    n = abs(value)
    if n >= 1_000_000:
        return f"{sign}£{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{sign}£{n / 1_000:.1f}K"
    return f"{sign}£{n:,.2f}"

holdings = compute_holdings()
if holdings:
    import pandas as pd

    df = pd.DataFrame(holdings)
    total_mv = df["market_value_gbp"].sum()
    total_ur = df["unrealized_pnl_gbp"].sum()
    total_re = df["realized_pnl_gbp"].sum()
    active = df[df["quantity"] > 0]
    num_active = len(active["ticker"].unique())
    cash = compute_cash_on_hand()
    portfolio_xirr = compute_portfolio_xirr()
    xirr_pct = (portfolio_xirr * 100) if portfolio_xirr is not None else None

    # Compute daily change: live NAV (holdings + cash) vs last historical NAV
    # NAV series uses historical EOD prices which don't include today's live moves,
    # so we compare live market value + cash against the most recent NAV series entry.
    nav_df = compute_nav_series()
    today_nav = total_mv + cash  # live holdings value + current cash
    daily_change_gbp = 0.0
    daily_change_pct = 0.0
    if not nav_df.empty:
        prev_nav = nav_df.iloc[-1]["nav"]  # last EOD NAV from historical prices
        daily_change_gbp = today_nav - prev_nav
        daily_change_pct = (daily_change_gbp / prev_nav * 100) if prev_nav > 0 else 0.0

    # --- Row 1: Key metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Holdings", num_active)
    col2.metric("Market Value (GBP)", compact_gbp(total_mv))
    col3.metric(
        "Daily Change",
        compact_gbp(daily_change_gbp),
        delta=f"{daily_change_pct:+.2f}%",
    )
    col4.metric(
        "Portfolio XIRR",
        f"{xirr_pct:+.2f}%" if xirr_pct is not None else "N/A",
    )

    # --- Row 2: P&L and cash ---
    total_cost = df["total_cost_gbp"].sum()
    total_pnl = total_ur + total_re
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
    ur_pct = (total_ur / total_cost * 100) if total_cost else 0.0

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Unrealized P&L", compact_gbp(total_ur), delta=f"{ur_pct:+.2f}%")
    col6.metric("Realized P&L", compact_gbp(total_re))
    col7.metric("Total P&L", compact_gbp(total_pnl), delta=f"{total_pnl_pct:+.2f}%")
    col8.metric("Cash in Hand (GBP)", compact_gbp(cash))
else:
    st.info("No transactions yet. Go to **Transactions** to add your first trade.")
