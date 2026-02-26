"""Simple admin access control for edit actions — hidden from client view."""

import os

import streamlit as st


def is_admin_user(page_key: str) -> bool:
    """Return whether the current session is in admin mode.

    Admin unlock is hidden behind ?admin=1 query parameter.
    Client users never see the unlock UI.
    """
    state_key = "admin_unlocked"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    # Only show admin controls if ?admin=1 is in URL
    params = st.query_params
    show_admin_ui = params.get("admin") == "1"

    if not show_admin_ui and not st.session_state[state_key]:
        return False

    expected_pin = ""
    try:
        expected_pin = st.secrets.get("ADMIN_PIN", "")
    except Exception:
        expected_pin = ""
    if not expected_pin:
        expected_pin = os.environ.get("ADMIN_PIN", "")

    if st.session_state[state_key]:
        # Small caption + lock button at bottom of sidebar
        with st.sidebar:
            st.caption("Admin mode active")
            if st.button("Lock", key=f"lock_{page_key}"):
                st.session_state[state_key] = False
                st.rerun()
        return True

    if show_admin_ui:
        with st.sidebar:
            if not expected_pin:
                st.caption("Admin PIN is not configured.")
            pin = st.text_input("PIN", type="password", key=f"pin_{page_key}")
            if st.button("Unlock", key=f"unlock_{page_key}"):
                if expected_pin and pin == expected_pin:
                    st.session_state[state_key] = True
                    st.rerun()
                else:
                    st.error("Invalid PIN")

    return bool(st.session_state[state_key])
