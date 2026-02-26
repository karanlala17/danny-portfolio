"""Per-trade profitability — FIFO matched lots by ticker and broker."""

import streamlit as st
st.set_page_config(page_title="Trade Profitability", page_icon="📌", layout="wide")

import pandas as pd

from portfolio_calc import compute_trade_profitability

st.title("Per-Trade Profitability")
st.caption("FIFO matched buy/sell lots, grouped at ticker + broker level.")

rows = compute_trade_profitability()
if not rows:
    st.info("No closed trade lots found yet.")
    st.stop()

df = pd.DataFrame(rows)
df["buy_date"] = pd.to_datetime(df["buy_date"])
df["sell_date"] = pd.to_datetime(df["sell_date"])

col1, col2 = st.columns(2)
with col1:
    tickers = sorted(df["ticker"].unique().tolist())
    selected_tickers = st.multiselect("Filter by Ticker", options=tickers)
with col2:
    brokers = sorted(df["broker"].unique().tolist())
    selected_brokers = st.multiselect("Filter by Broker", options=brokers)

filtered = df.copy()
if selected_tickers:
    filtered = filtered[filtered["ticker"].isin(selected_tickers)]
if selected_brokers:
    filtered = filtered[filtered["broker"].isin(selected_brokers)]

display = filtered.copy()
display["Buy Date"] = display["buy_date"].dt.strftime("%d-%m-%Y")
display["Sell Date"] = display["sell_date"].dt.strftime("%d-%m-%Y")
display = display.rename(
    columns={
        "ticker": "Ticker",
        "display_name": "Name",
        "broker": "Broker",
        "currency": "Currency",
        "qty": "Qty",
        "buy_price": "Buy Px",
        "sell_price": "Sell Px",
        "holding_days": "Hold Days",
        "cost_native": "Cost (Txn Ccy)",
        "proceeds_native": "Proceeds (Txn Ccy)",
        "realized_pnl_native": "P&L (Txn Ccy)",
        "cost_gbp": "Cost (GBP)",
        "proceeds_gbp": "Proceeds (GBP)",
        "realized_pnl_gbp": "P&L (GBP)",
        "realized_pnl_pct": "P&L %",
        "annualized_return_pct": "Annualized %",
    }
)

def _color_pnl(v):
    if isinstance(v, str):
        if v.startswith("+"):
            return "color: green"
        if v.startswith("-"):
            return "color: red"
        return ""
    if isinstance(v, (int, float)):
        if v > 0:
            return "color: green"
        if v < 0:
            return "color: red"
    return ""

st.dataframe(
    display[
        [
            "Sell Date",
            "Buy Date",
            "Ticker",
            "Name",
            "Broker",
            "Currency",
            "Qty",
            "Buy Px",
            "Sell Px",
            "Hold Days",
            "Cost (Txn Ccy)",
            "Proceeds (Txn Ccy)",
            "P&L (Txn Ccy)",
            "Cost (GBP)",
            "Proceeds (GBP)",
            "P&L (GBP)",
            "P&L %",
            "Annualized %",
        ]
    ].style.format(
        {
            "Qty": "{:,.0f}",
            "Buy Px": "{:,.4f}",
            "Sell Px": "{:,.4f}",
            "Cost (Txn Ccy)": "{:,.2f}",
            "Proceeds (Txn Ccy)": "{:,.2f}",
            "P&L (Txn Ccy)": "{:+,.2f}",
            "Cost (GBP)": "£{:,.2f}",
            "Proceeds (GBP)": "£{:,.2f}",
            "P&L (GBP)": "£{:,.2f}",
            "P&L %": lambda v: f"{v:+.2f}%" if pd.notna(v) else "N/A",
            "Annualized %": lambda v: f"{v:+.2f}%" if pd.notna(v) else "N/A",
        }
    ).map(
        _color_pnl,
        subset=["P&L (Txn Ccy)", "P&L (GBP)", "P&L %", "Annualized %"],
    ),
    use_container_width=True,
    hide_index=True,
    height=520,
)

if not filtered.empty:
    total_pnl = filtered["realized_pnl_gbp"].sum()
    avg_return = filtered["realized_pnl_pct"].dropna().mean()
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Matched Lots", f"{len(filtered):,}")
    col_b.metric("Total Realized P&L", f"£{total_pnl:,.2f}")
    col_c.metric("Average Lot P&L %", f"{avg_return:.2f}%" if pd.notna(avg_return) else "N/A")
