"""Transactions — view, add, edit, delete buy/sell transactions."""

import streamlit as st
st.set_page_config(page_title="Transactions", page_icon="📝", layout="wide")

import pandas as pd
from datetime import date, datetime
from decimal import Decimal

from sidebar import render_sidebar
render_sidebar()

from db import (
    get_transactions,
    add_transaction,
    delete_transaction,
    get_watchlist,
    update_transaction,
)
from market_data import get_fx_rate_on_date
from ui_access import is_admin_user

st.title("Transactions")

DATE_FMT = "%d-%m-%Y"
admin_mode = is_admin_user("transactions")


def _dec(v) -> Decimal:
    return Decimal(str(v))

if admin_mode:
    st.caption("Admin mode: Add / Modify / Delete actions are enabled.")
else:
    st.caption("View-only mode: transaction edits are hidden.")

# ---------------------------------------------------------------------------
# Add Transaction form (Admin only)
# ---------------------------------------------------------------------------

watchlist = get_watchlist()
ticker_options = {w["ticker"]: f"{w['ticker']} — {w['display_name']}" for w in watchlist}

if admin_mode:
    st.subheader("Add Transaction")
    with st.form("add_txn", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            use_watchlist = st.checkbox("Pick from watchlist", value=True)
            if use_watchlist and ticker_options:
                selected = st.selectbox("Ticker", options=list(ticker_options.keys()),
                                        format_func=lambda t: ticker_options[t])
                ticker = selected
                display_name = next((w["display_name"] for w in watchlist if w["ticker"] == selected), selected)
            else:
                ticker = st.text_input("Yahoo Finance Ticker", placeholder="e.g. AAPL")
                display_name = st.text_input("Display Name", placeholder="e.g. Apple Inc")

            action = st.selectbox("Action", ["BUY", "SELL"])
            txn_date = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")

        with col2:
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
            price = st.number_input("Price per Share", min_value=0.0, step=0.0001, format="%.4f")
            currency = st.selectbox("Currency", ["GBP", "USD"])
            broker = st.selectbox("Broker", ["JB", "DBS"])

            if currency == "USD":
                fx_default = get_fx_rate_on_date("GBPUSD=X", txn_date.strftime("%Y-%m-%d")) or 1.27
                fx_rate = st.number_input(
                    "GBP/USD Exchange Rate",
                    min_value=0.0,
                    value=float(fx_default),
                    step=0.000001,
                    format="%.6f",
                    help="Default uses close FX rate on transaction date (or prior trading day).",
                )
            else:
                fx_rate = 1.0

        notes = st.text_input("Notes (optional)")
        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            if not ticker or not display_name or quantity <= 0 or price < 0:
                st.error("Please fill in all required fields (ticker, name, quantity, price).")
            else:
                add_transaction(
                    ticker=ticker.strip().upper(),
                    display_name=display_name.strip(),
                    action=action,
                    txn_date=txn_date.strftime("%Y-%m-%d"),
                    quantity=quantity,
                    price_per_share=price,
                    currency=currency,
                    broker=broker,
                    exchange_rate_to_gbp=fx_rate,
                    notes=notes,
                )
                st.success(f"Added {action} of {quantity:.0f} {ticker} @ {price:.4f} {currency}")
                st.rerun()

# ---------------------------------------------------------------------------
# Transaction log
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Transaction Log")

txns = get_transactions()
if not txns:
    st.info("No transactions yet.")
    st.stop()

rows = []
for t in txns:
    d = t["date"]
    d_out = d
    if isinstance(d, str):
        try:
            d_out = datetime.strptime(d, "%Y-%m-%d").strftime(DATE_FMT)
        except ValueError:
            d_out = d

    total_txn_currency = _dec(t["quantity"]) * _dec(t["price_per_share"])
    if t["currency"] == "GBP":
        total_gbp = total_txn_currency
    else:
        fx = _dec(t["exchange_rate_to_gbp"] or 0)
        total_gbp = (total_txn_currency / fx) if fx > 0 else total_txn_currency

    rows.append({
        "ID": t["id"],
        "Date": d_out,
        "Ticker": t["ticker"],
        "Name": t["display_name"],
        "Action": t["action"],
        "Qty": t["quantity"],
        "Price": t["price_per_share"],
        "Currency": t["currency"],
        "Total (Txn Ccy)": float(total_txn_currency),
        "Total (GBP)": float(total_gbp),
        "Broker": t["broker"],
        "FX Rate": t["exchange_rate_to_gbp"],
        "Notes": t["notes"] or "",
    })

df = pd.DataFrame(rows)

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    filter_ticker = st.multiselect("Filter by Ticker", options=sorted(df["Ticker"].unique()))
with col2:
    filter_action = st.multiselect("Filter by Action", options=["BUY", "SELL"])
with col3:
    filter_broker = st.multiselect("Filter by Broker", options=sorted(df["Broker"].dropna().unique()))

filtered = df.copy()
if filter_ticker:
    filtered = filtered[filtered["Ticker"].isin(filter_ticker)]
if filter_action:
    filtered = filtered[filtered["Action"].isin(filter_action)]
if filter_broker:
    filtered = filtered[filtered["Broker"].isin(filter_broker)]

st.dataframe(
    filtered.style.format({
        "Qty": "{:,.0f}",
        "Price": "{:,.4f}",
        "Total (Txn Ccy)": "{:,.2f}",
        "Total (GBP)": "£{:,.2f}",
        "FX Rate": "{:.6f}",
    }),
    use_container_width=True,
    hide_index=True,
)

st.caption(f"Showing {len(filtered)} of {len(df)} transactions")

if not filtered.empty:
    st.subheader("Filtered Subtotal")
    subtotal = (
        filtered.groupby("Currency", as_index=False)[["Total (Txn Ccy)", "Total (GBP)"]]
        .sum()
        .sort_values("Currency")
    )
    buy_gbp = filtered.loc[filtered["Action"] == "BUY", "Total (GBP)"].sum()
    sell_gbp = filtered.loc[filtered["Action"] == "SELL", "Total (GBP)"].sum()
    net_gbp = sell_gbp - buy_gbp

    c1, c2, c3 = st.columns(3)
    c1.metric("BUY Total (GBP)", f"£{buy_gbp:,.2f}")
    c2.metric("SELL Total (GBP)", f"£{sell_gbp:,.2f}")
    c3.metric("Net (SELL - BUY)", f"£{net_gbp:,.2f}")

    st.dataframe(
        subtotal.style.format(
            {"Total (Txn Ccy)": "{:,.2f}", "Total (GBP)": "£{:,.2f}"}
        ),
        use_container_width=False,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Modify / Delete transaction (Admin only)
# ---------------------------------------------------------------------------

if admin_mode:
    with st.expander("Modify a Transaction"):
        options = {
            f"#{t['id']} | {t['date']} | {t['action']} {t['quantity']:.0f} {t['ticker']} ({t['broker']})": t
            for t in txns
        }
        selected_label = st.selectbox("Pick a transaction", options=list(options.keys()))
        selected_txn = options[selected_label]

        c1, c2 = st.columns(2)
        with c1:
            edit_ticker = st.text_input("Ticker", value=selected_txn["ticker"]).strip().upper()
            edit_name = st.text_input("Display Name", value=selected_txn["display_name"]).strip()
            edit_action = st.selectbox("Action", ["BUY", "SELL"], index=0 if selected_txn["action"] == "BUY" else 1)
            current_date = datetime.strptime(selected_txn["date"], "%Y-%m-%d").date()
            edit_date = st.date_input("Date", value=current_date, format="DD/MM/YYYY", key="edit_date")

        with c2:
            edit_qty = st.number_input("Quantity", min_value=0.0, value=float(selected_txn["quantity"]), step=1.0)
            edit_price = st.number_input(
                "Price per Share",
                min_value=0.0,
                value=float(selected_txn["price_per_share"]),
                step=0.0001,
                format="%.4f",
            )
            edit_currency = st.selectbox("Currency", ["GBP", "USD"], index=0 if selected_txn["currency"] == "GBP" else 1)
            broker_options = ["JB", "DBS"]
            broker_index = broker_options.index(selected_txn["broker"]) if selected_txn["broker"] in broker_options else 0
            edit_broker = st.selectbox("Broker", broker_options, index=broker_index)

            if edit_currency == "USD":
                suggested = get_fx_rate_on_date("GBPUSD=X", edit_date.strftime("%Y-%m-%d")) or 1.27
                edit_fx = st.number_input(
                    "GBP/USD Exchange Rate",
                    min_value=0.0,
                    value=float(selected_txn["exchange_rate_to_gbp"] or suggested),
                    step=0.000001,
                    format="%.6f",
                )
            else:
                edit_fx = 1.0

        edit_notes = st.text_input("Notes", value=selected_txn["notes"] or "")

        if st.button("Save Changes", type="primary"):
            if not edit_ticker or not edit_name or edit_qty <= 0:
                st.error("Ticker, name, and positive quantity are required.")
            else:
                update_transaction(
                    int(selected_txn["id"]),
                    ticker=edit_ticker,
                    display_name=edit_name,
                    action=edit_action,
                    date=edit_date.strftime("%Y-%m-%d"),
                    quantity=float(edit_qty),
                    price_per_share=float(edit_price),
                    currency=edit_currency,
                    broker=edit_broker,
                    exchange_rate_to_gbp=float(edit_fx),
                    notes=edit_notes,
                )
                st.success(f"Updated transaction #{selected_txn['id']}")
                st.rerun()

    with st.expander("Delete a Transaction"):
        del_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
        if st.button("Delete", type="primary"):
            delete_transaction(int(del_id))
            st.success(f"Deleted transaction #{del_id}")
            st.rerun()
