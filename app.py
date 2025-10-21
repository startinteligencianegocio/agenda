import re
import streamlit as st
from streamlit_option_menu import option_menu
from auth import validar_login
from pathlib import Path
import streamlit as st
from pathlib import Path

hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
"""
def inject_global_css(path="style.css"):
    p = Path(path)
    if not p.exists(): return
    try:
        css = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        css = p.read_text(encoding="latin-1", errors="ignore")
    import streamlit as st
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

inject_global_css()


inject_global_css()
st.set_page_config(page_title="Agenda Profissional", page_icon="📅", layout="wide")

css_path = Path(__file__).with_name("style.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None

DEBUG = st.query_params.get("debug", ["0"]) if hasattr(st, "query_params") else "0"
try:
    DEBUG = (DEBUG[0] if isinstance(DEBUG, list) else DEBUG) in ("1", "true", "True")
except Exception:
    DEBUG = False

def tela_login():
    # 3 colunas: tudo (header + form) ficará na coluna central
    _, center, _ = st.columns([1, 1, 1])

    with center:
        # Header com 2 colunas (logo + título) alinhado ao formulário
        h_logo, h_title = st.columns([1, 6])
        with h_logo:
            st.image("start.png", width=160)
        with h_title:
            st.markdown(
                "<h1 class='titulo-app' style='margin:10px 0 0 0;font-size:28px;line-height:1.1;white-space:nowrap;'>Agenda Profissional</h1>",
                unsafe_allow_html=True,
            )
            st.markdown("<p class='muted' style='margin: 2px 0 18px 0;'>Acesse com seu e-mail e senha</p>", unsafe_allow_html=True)

        # Formulário (aqui mesmo na mesma coluna central)
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-mail", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password")
            logar = st.form_submit_button("Entrar")

    if logar:
        try:
            u = validar_login(email, senha)
        except Exception as e:
            st.error("Erro durante validação de login.")
            st.exception(e)
            return
        if u:
            st.session_state.user = u
            if DEBUG: st.write({"user": u})
            st.success("Login efetuado com sucesso!")
            st.rerun()
        else:
            st.error("Credenciais inválidas, inativas ou licença expirada.")

def streamlit_menu(is_admin: bool):
    try:
        selected = option_menu(
            menu_title=None,
            options=[
                "Dashboard",
                "Clientes",
                "Tipos de Serviços",
                "Lançamento de Serviços",
                "Agenda",
                *( ["Profissionais"] if is_admin else [] )
            ],
            icons=[
                "file-bar-graph-fill",
                "person-lines-fill",
                "book",
                "envelope",
                "calendar-date-fill",
                *( ["people-fill"] if is_admin else [] )
            ],
            menu_icon="cast",
            default_index=0,
            orientation="VERTICAL",
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#28B78D", "color": "white"},
            },
        )
        return selected
    except Exception as e:
        st.error("Falha ao construir o menu.")
        st.exception(e)
        return "Dashboard"

def _render_page(modname: str):
    try:
        page = __import__(modname)
        if DEBUG: st.info(f"Render: {modname}")
        page.render()
    except ModuleNotFoundError as e:
        st.error(f"Módulo '{modname}' não encontrado. Crie {modname}.py no diretório do app.")
        st.exception(e)
    except Exception as e:
        st.error(f"Erro ao renderizar a página '{modname}'.")
        st.exception(e)

def main():
    if not st.session_state.user:
        tela_login()
        return

    u = st.session_state.user
    with st.sidebar:
        st.success(f"Logado como: {u.get('nome','(sem nome)')} ✨")
        if u.get('is_admin'): st.info("Modo administrador")
        if st.button("Sair"):
            st.session_state.user = None
            st.rerun()

    selected = streamlit_menu(u.get('is_admin', False))

    if DEBUG: st.sidebar.write({"selected": selected, "is_admin": u.get('is_admin', False)})

    if selected == "Dashboard":
        _render_page("dashboard")
    elif selected == "Clientes":
        _render_page("clientes")
    elif selected == "Tipos de Serviços":
        _render_page("tipos_servicos")
    elif selected == "Lançamento de Serviços":
        _render_page("lancamento_servicos")
    elif selected == "Agenda":
        _render_page("agenda")
    elif selected == "Profissionais":
        _render_page("profissionais")
    else:
        st.write("Página não reconhecida.")

if __name__ == "__main__":
    main()
