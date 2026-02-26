"""News — watchlist ticker-wise updates with summaries."""

import streamlit as st
st.set_page_config(page_title="News", page_icon="🗞️", layout="wide")

from db import get_watchlist
from market_data import get_ticker_news

st.title("News")
st.caption("Latest watchlist news shown ticker-wise in alphabetical order.")

watchlist = [dict(w) for w in get_watchlist()]
if not watchlist:
    st.info("Watchlist is empty.")
    st.stop()

watchlist_sorted = sorted(watchlist, key=lambda w: w["ticker"])

# Optional ticker filter — show all if nothing selected
ticker_options = [f"{w['ticker']} — {w['display_name']}" for w in watchlist_sorted]
ticker_map = {f"{w['ticker']} — {w['display_name']}": w["ticker"] for w in watchlist_sorted}
selected_labels = st.multiselect("Filter by Ticker (leave empty for all)", options=ticker_options)
selected_tickers = {ticker_map[lbl] for lbl in selected_labels} if selected_labels else None

display_list = (
    [w for w in watchlist_sorted if w["ticker"] in selected_tickers]
    if selected_tickers
    else watchlist_sorted
)


def _summary_from_titles(news_items: list[dict]) -> str:
    titles = [n.get("title", "").strip() for n in news_items if n.get("title")]
    if not titles:
        return "No recent coverage available."
    top = titles[:3]
    return " | ".join(top)


for w in display_list:
    ticker = w["ticker"]
    name = w["display_name"]
    st.subheader(f"{ticker} — {name}")
    items = get_ticker_news(ticker, limit=6)

    st.markdown(f"**Summary:** {_summary_from_titles(items)}")
    if not items:
        st.caption("No recent news found.")
        st.divider()
        continue

    for item in items:
        title = item.get("title") or "Untitled"
        source = item.get("source") or ""
        published = item.get("published") or ""
        link = item.get("link") or ""
        meta = " | ".join([m for m in [source, published] if m])

        if link:
            st.markdown(f"- [{title}]({link})")
        else:
            st.markdown(f"- {title}")
        if meta:
            st.caption(meta)

    st.divider()
