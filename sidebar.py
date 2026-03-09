"""Shared sidebar components for all pages."""

import streamlit as st


def render_sidebar():
    """Render common sidebar elements (Refresh button)."""
    with st.sidebar:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
