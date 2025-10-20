
import streamlit as st
from utils_layout import styled_submit

def render_login(auth_fn, logo="start.png", title="Agenda Profissional"):
    left, center, right = st.columns([1,2,1])
    with center:
        col_logo, col_title = st.columns([1,5])
        with col_logo:
            st.image(logo, width=80)
        with col_title:
            st.markdown(f"<h2 style='margin:0'>{title}</h2>", unsafe_allow_html=True)

    st.write("")
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login_form", border=False):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            ok = styled_submit("Entrar", "padrao")
        if ok:
            auth_fn(email, senha)
