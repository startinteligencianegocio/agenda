
import re
import streamlit as st

def only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def format_br_phone(digits: str) -> str:
    # Format Brazilian phone digits into (XX) XXXXX-XXXX or (XX) XXXX-XXXX.
    d = only_digits(digits)
    if len(d) <= 10:
        # (XX) XXXX-XXXX
        if len(d) <= 2:
            return f"({{d}}"
        elif len(d) <= 6:
            return f"({{d[:2]}}) {{d[2:]}}"
        else:
            return f"({{d[:2]}}) {{d[2:6]}}-{{d[6:10]}}"
    else:
        # 11+ digits -> (XX) XXXXX-XXXX (ignore extras)
        d = d[:11]
        return f"({{d[:2]}}) {{d[2:7]}}-{{d[7:11]}}"

def sanitize_br_phone(formatted: str) -> str:
    # Return only digits, suitable for wa.me etc.
    return only_digits(formatted)

def mask_phone_on_change(key: str):
    # Streamlit on_change callback to enforce mask in-place via session_state.
    val = st.session_state.get(key, "") or ""
    st.session_state[key] = format_br_phone(val)
