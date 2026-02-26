"""World Indices Dashboard — live prices, 52W metrics, 2-year daily close."""

import streamlit as st
st.set_page_config(page_title="World Indices", page_icon="🌍", layout="wide")

import pandas as pd
from datetime import datetime, timedelta

from config import INDICES, FX_PAIRS
from market_data import get_current_price, get_historical_prices

st.title("World Indices")

DATE_FMT = "%d-%m-%Y"

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

with st.spinner("Loading..."):
    rows = []
    for idx in INDICES:
        data = get_current_price(idx["ticker"])
        if data:
            rows.append({
                "Index": idx["display_name"],
                "Ticker": idx["ticker"],
                "Current Value": data["price"],
                "Daily %": data["change_pct"],
                "52W High": data["high_52w"],
                "52W Low": data["low_52w"],
                "52W %": data["change_52w"],
                "30D %": data["change_30d"],
                "7D %": data["change_7d"],
            })

if rows:
    df = pd.DataFrame(rows)
    # Keep Google Sheet order (no sorting)

    st.dataframe(
        df.drop(columns=["Ticker"]).style.format({
            "Current Value": "{:,.2f}",
            "Daily %": "{:+.2f}%",
            "52W High": "{:,.2f}",
            "52W Low": "{:,.2f}",
            "52W %": "{:+.2f}%",
            "30D %": "{:+.2f}%",
            "7D %": "{:+.2f}%",
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
    st.warning("Could not fetch index data. Please try again later.")

# ---------------------------------------------------------------------------
# Currency pairs
# ---------------------------------------------------------------------------

st.subheader("Currency Rates")

fx_rows = []
for pair in FX_PAIRS:
    data = get_current_price(pair["ticker"])
    if data:
        fx_rows.append({
            "Pair": pair["display_name"],
            "Rate": data["price"],
            "Daily %": data["change_pct"],
            "7D %": data["change_7d"],
            "30D %": data["change_30d"],
        })

if fx_rows:
    fx_df = pd.DataFrame(fx_rows)
    st.dataframe(
        fx_df.style.format({
            "Rate": "{:.6f}",
            "Daily %": "{:+.2f}%",
            "7D %": "{:+.2f}%",
            "30D %": "{:+.2f}%",
        }).map(
            lambda v: (
                "color: green" if isinstance(v, (int, float)) and v > 0
                else "color: red" if isinstance(v, (int, float)) and v < 0
                else ""
            ),
            subset=["Daily %", "7D %", "30D %"],
        ),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# 2-Year Daily Close History
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Daily Close — Last 2 Years")

start_2y = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

# Let user pick which index to view history for
index_names = [idx["display_name"] for idx in INDICES]
selected_name = st.selectbox("Select Index", index_names)
selected_idx = next(i for i in INDICES if i["display_name"] == selected_name)

with st.spinner("Loading..."):
    hist = get_historical_prices(selected_idx["ticker"], start_2y)

if not hist.empty:
    # Prepare table data
    hist_table = hist.copy()
    hist_table.index = hist_table.index.date
    hist_table = hist_table.sort_index(ascending=False)
    hist_table = hist_table.reset_index()
    hist_table.columns = ["Date", "Close"]
    hist_table["Date"] = hist_table["Date"].apply(lambda d: d.strftime(DATE_FMT))

    # Show chart
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["Close"],
        mode="lines", name=selected_name,
        line=dict(color="#1f77b4", width=1.5),
    ))
    fig.update_layout(
        yaxis_tickformat=",",
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Compact table
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
    st.warning(f"No history found for {selected_name}.")
