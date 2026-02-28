"""Portfolio Summary — broker-wise, currency-wise summary matching Google Sheet layout."""

import streamlit as st
st.set_page_config(page_title="Portfolio Summary", page_icon="💼", layout="wide")

import pandas as pd

from config import WATCHLIST_ORDER
from portfolio_calc import compute_holdings, compute_portfolio_xirr
from market_data import get_fx_rate

st.title("Portfolio Summary")


def compact_gbp(value: float) -> str:
    sign = "-" if value < 0 else ""
    n = abs(value)
    if n >= 1_000_000:
        return f"{sign}£{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{sign}£{n / 1_000:.1f}K"
    return f"{sign}£{n:,.2f}"


def color_signed(v):
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


# ---------------------------------------------------------------------------
# Ordering helpers
# ---------------------------------------------------------------------------

BROKER_ORDER = {"JB": 0, "DBS": 1}
CURRENCY_ORDER = {"GBP": 0, "USD": 1}
order_map = {t: i for i, t in enumerate(WATCHLIST_ORDER)}

# ---------------------------------------------------------------------------
# Compute holdings
# ---------------------------------------------------------------------------

with st.spinner("Loading..."):
    holdings = compute_holdings()
    portfolio_xirr = compute_portfolio_xirr()
    gbp_usd = get_fx_rate("GBPUSD=X") or 1.27

if not holdings:
    st.info("No holdings found. Add transactions first.")
    st.stop()

df = pd.DataFrame(holdings)

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------

total_market_value = df["market_value_gbp"].sum()
total_cost = df["total_cost_gbp"].sum()
total_unrealized = df["unrealized_pnl_gbp"].sum()
total_realized = df["realized_pnl_gbp"].sum()
total_pnl = total_unrealized + total_realized
portfolio_return_pct = (total_pnl / total_cost * 100) if total_cost else None

portfolio_xirr_pct = (portfolio_xirr * 100) if portfolio_xirr is not None else None
ur_pct = (total_unrealized / total_cost * 100) if total_cost else 0.0
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0.0

# Row 1
col1, col2, col3, col4 = st.columns(4)
col1.metric("Market Value (GBP)", compact_gbp(total_market_value))
col2.metric("Total Cost (GBP)", compact_gbp(total_cost))
col3.metric("Unrealized P&L", compact_gbp(total_unrealized), delta=f"{ur_pct:+.2f}%")
col4.metric("Realized P&L", compact_gbp(total_realized))

# Row 2
col5, col6, col7, col8 = st.columns(4)
col5.metric("Total P&L", compact_gbp(total_pnl), delta=f"{total_pnl_pct:+.2f}%")
col6.metric(
    "Portfolio Return %",
    f"{portfolio_return_pct:+.2f}%" if portfolio_return_pct is not None else "N/A",
)
col7.metric(
    "Portfolio XIRR",
    f"{portfolio_xirr_pct:+.2f}%" if portfolio_xirr_pct is not None else "N/A",
)
col8.metric("GBP/USD Rate", f"{gbp_usd:.4f}")

st.caption("USD BUY/SELL transactions use stored transaction-date FX rates; current USD holdings are converted at current GBP/USD.")
st.divider()

# ---------------------------------------------------------------------------
# Holdings grouped by Broker (JB → DBS) then Currency (GBP → USD)
# ---------------------------------------------------------------------------

brokers = sorted(df["broker"].unique(), key=lambda b: BROKER_ORDER.get(b, 99))

for broker in brokers:
    st.subheader(f"Broker: {broker}")
    broker_df = df[df["broker"] == broker].copy()

    currencies = sorted(
        broker_df["currency"].unique(),
        key=lambda c: CURRENCY_ORDER.get(c, 99),
    )

    for currency in currencies:
        curr_df = broker_df[broker_df["currency"] == currency].copy()

        # Sort by watchlist order
        curr_df["_sort"] = curr_df["ticker"].map(lambda t: order_map.get(t, 999))
        curr_df = curr_df.sort_values("_sort").drop(columns=["_sort"])

        active = curr_df[curr_df["quantity"] > 0].copy()
        closed = curr_df[curr_df["quantity"] <= 0].copy()

        ccy_sym = "£" if currency == "GBP" else "$"

        # --- Active Holdings ---
        if not active.empty:
            st.markdown(f"**Active Holdings — {currency}**")

            cols = {
                "Ticker": active["ticker"].values,
                "Name": active["display_name"].values,
                "Qty": active["quantity"].values,
            }

            fmt = {"Qty": "{:,.0f}"}

            if currency == "GBP":
                cols["Avg Cost (GBP)"] = active["avg_cost_gbp"].values
                cols["Price (GBP)"] = active["current_price_gbp"].values
                cols["Mkt Val (GBP)"] = active["market_value_gbp"].values
                cols["Cost (GBP)"] = active["total_cost_gbp"].values
                cols["Unreal P&L (GBP)"] = active["unrealized_pnl_gbp"].values
                cols["Unreal %"] = active["unrealized_pnl_pct"].values
                cols["Real P&L (GBP)"] = active["realized_pnl_gbp"].values

                fmt["Avg Cost (GBP)"] = "£{:,.4f}"
                fmt["Price (GBP)"] = "£{:,.4f}"
                fmt["Mkt Val (GBP)"] = "£{:,.2f}"
                fmt["Cost (GBP)"] = "£{:,.2f}"
                fmt["Unreal P&L (GBP)"] = "£{:,.2f}"
                fmt["Unreal %"] = "{:+.2f}%"
                fmt["Real P&L (GBP)"] = "£{:,.2f}"
            else:
                # USD: show native columns, then Unreal P&L (GBP) derived from native, no Cost (GBP)
                cols[f"Avg Cost ({currency})"] = active["avg_cost"].values
                cols[f"Price ({currency})"] = active["current_price"].values
                cols[f"Mkt Val ({currency})"] = active["market_value"].values
                cols[f"Cost ({currency})"] = active["total_cost"].values
                cols[f"Unreal P&L ({currency})"] = active["unrealized_pnl"].values
                cols["Unreal %"] = active["unrealized_pnl_pct"].values
                cols["Mkt Val (GBP)"] = active["market_value_gbp"].values
                cols["Unreal P&L (GBP)"] = active["unrealized_pnl_gbp"].values
                cols["Real P&L (GBP)"] = active["realized_pnl_gbp"].values

                fmt[f"Avg Cost ({currency})"] = f"{ccy_sym}" + "{:,.4f}"
                fmt[f"Price ({currency})"] = f"{ccy_sym}" + "{:,.4f}"
                fmt[f"Mkt Val ({currency})"] = f"{ccy_sym}" + "{:,.2f}"
                fmt[f"Cost ({currency})"] = f"{ccy_sym}" + "{:,.2f}"
                fmt[f"Unreal P&L ({currency})"] = f"{ccy_sym}" + "{:,.2f}"
                fmt["Unreal %"] = "{:+.2f}%"
                fmt["Mkt Val (GBP)"] = "£{:,.2f}"
                fmt["Unreal P&L (GBP)"] = "£{:,.2f}"
                fmt["Real P&L (GBP)"] = "£{:,.2f}"

            cols["Real %"] = active["realized_pnl_pct"].apply(
                lambda v: f"{v:+.2f}%" if v is not None else "N/A"
            ).values
            cols["XIRR %"] = active["xirr"].apply(
                lambda v: f"{v * 100:+.2f}%" if v is not None else "N/A"
            ).values

            display = pd.DataFrame(cols)

            color_cols = [c for c in display.columns if "P&L" in c or c in ("Unreal %", "Real %", "XIRR %")]

            st.dataframe(
                display.style.format(fmt).map(
                    color_signed,
                    subset=color_cols,
                ),
                use_container_width=True,
                hide_index=True,
            )

        # --- Closed Positions ---
        if not closed.empty:
            st.markdown(f"**Closed Positions — {currency}**")

            closed_cols = {
                "Ticker": closed["ticker"].values,
                "Name": closed["display_name"].values,
            }
            closed_fmt = {}
            closed_color_cols = []

            if currency != "GBP":
                closed_cols[f"Realized P&L ({currency})"] = closed["realized_pnl_native"].values
                closed_fmt[f"Realized P&L ({currency})"] = f"{ccy_sym}" + "{:,.2f}"
                closed_color_cols.append(f"Realized P&L ({currency})")

            closed_cols["Realized P&L (GBP)"] = closed["realized_pnl_gbp"].values
            closed_fmt["Realized P&L (GBP)"] = "£{:,.2f}"
            closed_color_cols.append("Realized P&L (GBP)")

            closed_cols["Realized %"] = closed["realized_pnl_pct"].apply(
                lambda v: f"{v:+.2f}%" if v is not None else "N/A"
            ).values
            closed_cols["XIRR %"] = closed["xirr"].apply(
                lambda v: f"{v * 100:+.2f}%" if v is not None else "N/A"
            ).values
            closed_color_cols.extend(["Realized %", "XIRR %"])

            closed_display = pd.DataFrame(closed_cols)
            st.dataframe(
                closed_display.style.format(closed_fmt).map(
                    color_signed,
                    subset=closed_color_cols,
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown(
                f"**Closed {currency} Realized Total** — £{closed['realized_pnl_gbp'].sum():,.2f}"
            )

        # Active subtotal
        if not active.empty:
            sub_mv = active["market_value_gbp"].sum()
            sub_cost = active["total_cost_gbp"].sum()
            sub_ur = active["unrealized_pnl_gbp"].sum()
            sub_re = active["realized_pnl_gbp"].sum()
            if currency != "GBP":
                sub_mv_native = active["market_value"].sum()
                sub_cost_native = active["total_cost"].sum()
                sub_ur_native = active["unrealized_pnl"].sum()
                sub_re_native = active["realized_pnl_native"].sum()
                st.markdown(
                    f"**Active {currency} Subtotal** — "
                    f"Market Value: {ccy_sym}{sub_mv_native:,.2f} (£{sub_mv:,.2f}) | "
                    f"Cost: {ccy_sym}{sub_cost_native:,.2f} (£{sub_cost:,.2f}) | "
                    f"Unrealized: {ccy_sym}{sub_ur_native:,.2f} (£{sub_ur:,.2f}) | "
                    f"Realized: {ccy_sym}{sub_re_native:,.2f} (£{sub_re:,.2f})"
                )
            else:
                st.markdown(
                    f"**Active {currency} Subtotal** — "
                    f"Market Value: £{sub_mv:,.2f} | "
                    f"Cost: £{sub_cost:,.2f} | "
                    f"Unrealized: £{sub_ur:,.2f} | "
                    f"Realized: £{sub_re:,.2f}"
                )

    # Broker total
    b_mv = broker_df["market_value_gbp"].sum()
    b_ur = broker_df["unrealized_pnl_gbp"].sum()
    b_re = broker_df["realized_pnl_gbp"].sum()
    st.success(
        f"**{broker} Total** — "
        f"Market Value: £{b_mv:,.2f} | "
        f"Unrealized: £{b_ur:,.2f} | "
        f"Realized: £{b_re:,.2f}"
    )
    st.divider()
