"""NAV Chart — NAV, Investment, and Profit over time."""

import streamlit as st
st.set_page_config(page_title="NAV Chart", page_icon="📈", layout="wide")

import plotly.graph_objects as go

from sidebar import render_sidebar
render_sidebar()

from portfolio_calc import compute_nav_series

st.title("Portfolio NAV Over Time")

DATE_FMT = "%d-%m-%Y"

st.markdown(
    "**NAV** = End-of-day holdings value + Cash on hand (from sales).  \n"
    "**Investment** = Total new money injected.  \n"
    "**Profit** = NAV - Investment (unrealized + realized combined).  \n"
    "When a security is sold, proceeds stay as cash — NAV does not drop."
)

# ---------------------------------------------------------------------------
# Compute and plot
# ---------------------------------------------------------------------------

with st.spinner("Loading..."):
    nav_df = compute_nav_series()

if nav_df.empty:
    st.info("No transactions found. Add transactions to see the NAV chart.")
    st.stop()

nav_df["date_str"] = nav_df["date"].apply(
    lambda d: d.strftime(DATE_FMT) if hasattr(d, "strftime") else str(d)
)

fig = go.Figure()

# NAV line
fig.add_trace(go.Scatter(
    x=nav_df["date"], y=nav_df["nav"],
    mode="lines", name="NAV",
    line=dict(color="#1f77b4", width=2.5),
    hovertemplate="£%{y:,.0f}<extra>NAV</extra>",
))

# Holdings Market Value line
fig.add_trace(go.Scatter(
    x=nav_df["date"], y=nav_df["holdings_value"],
    mode="lines", name="Holdings Market Value",
    line=dict(color="#d62728", width=2),
    hovertemplate="£%{y:,.0f}<extra>Holdings MV</extra>",
))

# Investment line
fig.add_trace(go.Scatter(
    x=nav_df["date"], y=nav_df["investment"],
    mode="lines", name="Investment",
    line=dict(color="#ff7f0e", width=2, dash="dash"),
    hovertemplate="£%{y:,.0f}<extra>Investment</extra>",
))

# Cash line
fig.add_trace(go.Scatter(
    x=nav_df["date"], y=nav_df["cash_on_hand"],
    mode="lines", name="Cash In Hand",
    line=dict(color="#9467bd", width=2, dash="dot"),
    hovertemplate="£%{y:,.0f}<extra>Cash</extra>",
))

# Profit line
fig.add_trace(go.Scatter(
    x=nav_df["date"], y=nav_df["profit"],
    mode="lines", name="Profit (Unrealized + Realized)",
    line=dict(color="#2ca02c", width=2),
    hovertemplate="£%{y:,.0f}<extra>Profit</extra>",
))

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="GBP (£)",
    yaxis_tickprefix="£",
    yaxis_tickformat=",",
    hovermode="x unified",
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    margin=dict(l=20, r=20, t=50, b=20),
)

st.plotly_chart(fig, use_container_width=True)

if len(nav_df) >= 2:
    latest = nav_df.iloc[-1]
    prev = nav_df.iloc[-2]
    d_nav = latest["nav"] - prev["nav"]
    d_hold = latest["holdings_value"] - prev["holdings_value"]
    d_cash = latest["cash_on_hand"] - prev["cash_on_hand"]
    st.info(
        "Why NAV can fall even with large total profit: profit is cumulative since inception "
        "(NAV - total invested), while NAV itself moves daily with market prices. "
        f"Latest day move: NAV {d_nav:+,.2f} = Holdings {d_hold:+,.2f} + Cash {d_cash:+,.2f}."
    )

# ---------------------------------------------------------------------------
# NAV calculation view
# ---------------------------------------------------------------------------

st.subheader("NAV Calculation (EOD)")
calc_df = nav_df.copy()
calc_df["Date"] = calc_df["date_str"]
calc_df["Holdings Value (GBP)"] = calc_df["holdings_value"]
calc_df["Cash On Hand (GBP)"] = calc_df["cash_on_hand"]
calc_df["NAV (GBP)"] = calc_df["nav"]
calc_df["Investment (GBP)"] = calc_df["investment"]
calc_df["Profit (GBP)"] = calc_df["profit"]
calc_df["GBP/USD"] = calc_df["gbp_usd_rate"]
calc_df = calc_df.sort_values("date", ascending=False)

st.dataframe(
    calc_df[
        [
            "Date",
            "Holdings Value (GBP)",
            "Cash On Hand (GBP)",
            "NAV (GBP)",
            "Investment (GBP)",
            "Profit (GBP)",
            "GBP/USD",
        ]
    ].style.format(
        {
            "Holdings Value (GBP)": "£{:,.2f}",
            "Cash On Hand (GBP)": "£{:,.2f}",
            "NAV (GBP)": "£{:,.2f}",
            "Investment (GBP)": "£{:,.2f}",
            "Profit (GBP)": "£{:,.2f}",
            "GBP/USD": "{:.6f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
    height=420,
)

latest_row = calc_df.iloc[0]
st.caption(
    f"Latest formula: NAV = Holdings £{latest_row['Holdings Value (GBP)']:,.2f} + "
    f"Cash £{latest_row['Cash On Hand (GBP)']:,.2f} = £{latest_row['NAV (GBP)']:,.2f}"
)

# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

if len(nav_df) >= 2:
    latest = nav_df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current NAV", f"£{latest['nav']:,.2f}")
    col2.metric("Total Invested", f"£{latest['investment']:,.2f}")
    col3.metric(
        "Total Profit",
        f"£{latest['profit']:,.2f}",
        delta=(
            f"{latest['profit'] / latest['investment'] * 100:.1f}%"
            if latest["investment"] else None
        ),
    )
    col4.metric("Peak NAV", f"£{nav_df['nav'].max():,.2f}")
