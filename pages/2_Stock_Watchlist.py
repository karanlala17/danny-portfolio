"""Stock Watchlist — tracked securities with daily moves, PE, EPS, 2-year history."""

import streamlit as st
st.set_page_config(page_title="Stock Watchlist", page_icon="📋", layout="wide")

import pandas as pd
from datetime import datetime, timedelta

from config import WATCHLIST_ORDER
from db import get_watchlist, add_to_watchlist, remove_from_watchlist, get_transactions
from market_data import get_current_price, get_historical_prices
from ui_access import is_admin_user

st.title("Stock Watchlist")

DATE_FMT = "%d-%m-%Y"
admin_mode = is_admin_user("watchlist")

# ---------------------------------------------------------------------------
# Add / Remove tickers (Admin only)
# ---------------------------------------------------------------------------

if admin_mode:
    with st.expander("Manage Watchlist"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_ticker = st.text_input("Yahoo Finance Ticker", placeholder="e.g. AAPL")
        with col2:
            new_name = st.text_input("Display Name", placeholder="e.g. Apple Inc")
        with col3:
            new_currency = st.selectbox("Currency", ["GBP", "USD"], index=1)

        if st.button("Add to Watchlist"):
            if new_ticker and new_name:
                add_to_watchlist(new_ticker.strip().upper(), new_name.strip(), new_currency)
                st.success(f"Added {new_ticker} to watchlist.")
                st.rerun()
            else:
                st.error("Please provide both ticker and display name.")

        watchlist = get_watchlist()
        if watchlist:
            remove_ticker = st.selectbox(
                "Remove a ticker",
                options=[""] + [w["ticker"] for w in watchlist],
                format_func=lambda x: f"{x}" if x else "Select...",
            )
            if remove_ticker and st.button("Remove"):
                remove_from_watchlist(remove_ticker)
                st.success(f"Removed {remove_ticker}.")
                st.rerun()

# ---------------------------------------------------------------------------
# Display watchlist summary
# ---------------------------------------------------------------------------

watchlist = get_watchlist()
if not watchlist:
    st.info("Watchlist is empty.")
    st.stop()

# Sort watchlist to match Google Sheet order
order_map = {t: i for i, t in enumerate(WATCHLIST_ORDER)}
watchlist_sorted = sorted(
    watchlist,
    key=lambda w: order_map.get(w["ticker"], 999),
)

with st.spinner("Loading..."):
    rows = []
    for w in watchlist_sorted:
        data = get_current_price(w["ticker"])
        if data:
            rows.append({
                "Ticker": w["ticker"],
                "Name": w["display_name"],
                "Currency": w["currency"],
                "Price": data["price"],
                "Daily %": data["change_pct"],
                "52W High": data["high_52w"],
                "52W Low": data["low_52w"],
                "52W %": data["change_52w"],
                "30D %": data["change_30d"],
                "7D %": data["change_7d"],
                "PE": data["pe"],
                "EPS": data["eps"],
            })

if rows:
    df = pd.DataFrame(rows)

    def fmt_or_na(val, fmt="{:.2f}"):
        if val is None:
            return "N/A"
        return fmt.format(val)

    st.dataframe(
        df.style.format({
            "Price": "{:,.4f}",
            "Daily %": "{:+.2f}%",
            "52W High": lambda v: fmt_or_na(v, "{:,.2f}"),
            "52W Low": lambda v: fmt_or_na(v, "{:,.2f}"),
            "52W %": lambda v: fmt_or_na(v, "{:+.2f}%"),
            "30D %": lambda v: fmt_or_na(v, "{:+.2f}%"),
            "7D %": lambda v: fmt_or_na(v, "{:+.2f}%"),
            "PE": lambda v: fmt_or_na(v, "{:.1f}"),
            "EPS": lambda v: fmt_or_na(v, "{:.2f}"),
        }).map(
            lambda v: (
                "color: green" if isinstance(v, (int, float)) and v > 0
                else "color: red" if isinstance(v, (int, float)) and v < 0
                else ""
            ),
            subset=["Daily %", "52W %", "30D %", "7D %"],
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.warning("Could not fetch stock data. Please try again later.")

# ---------------------------------------------------------------------------
# 2-Year Daily Close History
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Daily Close — Since Jan 2023")

start_2y = "2023-01-01"
ticker_options = [w["ticker"] for w in watchlist_sorted]
display_map = {w["ticker"]: f"{w['ticker']} — {w['display_name']}" for w in watchlist_sorted}

selected_ticker = st.selectbox(
    "Select Stock",
    options=ticker_options,
    format_func=lambda t: display_map.get(t, t),
)

if selected_ticker:
    with st.spinner("Loading..."):
        hist = get_historical_prices(selected_ticker, start_2y)

    if not hist.empty:
        hist_table = hist.copy()
        hist_table.index = hist_table.index.date
        hist_table = hist_table.sort_index(ascending=False)
        hist_table = hist_table.reset_index()
        hist_table.columns = ["Date", "Close"]
        hist_table["Date"] = hist_table["Date"].apply(lambda d: d.strftime(DATE_FMT))

        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"],
            mode="lines", name=selected_ticker,
            line=dict(color="#1f77b4", width=1.5),
        ))

        # Add horizontal line for current price
        current_data = get_current_price(selected_ticker)
        if current_data and current_data["price"] is not None:
            current_px = current_data["price"]
            fig.add_hline(
                y=current_px,
                line_dash="dash",
                line_color="orange",
                line_width=1,
                annotation_text=f"Current: {current_px:,.2f}",
                annotation_position="top right",
                annotation_font_color="orange",
            )

        # Add buy/sell transaction markers
        txns = get_transactions()
        if txns:
            ticker_txns = [dict(t) for t in txns if t["ticker"] == selected_ticker]
            buys = [t for t in ticker_txns if t["action"] == "BUY"]
            sells = [t for t in ticker_txns if t["action"] == "SELL"]

            if buys:
                buy_dates = [pd.Timestamp(t["date"]) for t in buys]
                buy_prices = [float(t["price_per_share"]) for t in buys]
                buy_qtys = [float(t["quantity"]) for t in buys]
                fig.add_trace(go.Scatter(
                    x=buy_dates, y=buy_prices,
                    mode="markers", name="Buy",
                    marker=dict(symbol="triangle-up", size=12, color="green", line=dict(width=1, color="darkgreen")),
                    hovertemplate="BUY<br>Date: %{x|%d-%m-%Y}<br>Price: %{y:,.4f}<br>Qty: %{customdata:,.0f}<extra></extra>",
                    customdata=buy_qtys,
                ))

            if sells:
                sell_dates = [pd.Timestamp(t["date"]) for t in sells]
                sell_prices = [float(t["price_per_share"]) for t in sells]
                sell_qtys = [float(t["quantity"]) for t in sells]
                fig.add_trace(go.Scatter(
                    x=sell_dates, y=sell_prices,
                    mode="markers", name="Sell",
                    marker=dict(symbol="triangle-down", size=12, color="red", line=dict(width=1, color="darkred")),
                    hovertemplate="SELL<br>Date: %{x|%d-%m-%Y}<br>Price: %{y:,.4f}<br>Qty: %{customdata:,.0f}<extra></extra>",
                    customdata=sell_qtys,
                ))

        fig.update_layout(
            yaxis_tickformat=",",
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            hist_table,
            column_config={
                "Date": st.column_config.TextColumn("Date", width=110),
                "Close": st.column_config.NumberColumn("Close", width=120, format="%.2f"),
            },
            use_container_width=False,
            hide_index=True,
            height=400,
        )
    else:
        st.warning(f"No history found for {selected_ticker}.")
