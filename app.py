# app.py
from pathlib import Path
import streamlit as st
from streamlit_option_menu import option_menu
from auth import validar_login

# =========================
# Configuração inicial
# =========================

st.set_page_config(
    page_title="Agenda Profissional",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",  # garante a sidebar expandida (inclusive no mobile)
)

# Oculta elementos nativos do Streamlit (reexibiremos o header no mobile via media query)
st.markdown(
    """
    <style>
      #MainMenu {visibility: hidden;}
      header {visibility: hidden;}
      footer {visibility: hidden;}

      /* No mobile, precisamos do header para o botão de abrir a sidebar */
      @media (max-width: 768px) {
        header {visibility: visible !important;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# CSS global (carrega style.css caso exista)
# =========================
def inject_global_css(path: str = "style.css"):
    p = Path(path)
    if not p.exists():
        return
    try:
        css = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        css = p.read_text(encoding="latin-1", errors="ignore")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

inject_global_css()

# =========================
# Estado & utilidades
# =========================
if "user" not in st.session_state:
    st.session_state.user = None

def _get_debug_flag() -> bool:
    # Compatível com versões antigas e novas do Streamlit
    qp = {}
    try:
        qp = st.query_params  # Streamlit 1.32+
    except Exception:
        try:
            qp = st.experimental_get_query_params()  # versões anteriores
        except Exception:
            qp = {}
    dbg = qp.get("debug", ["0"])
    dbg = dbg[0] if isinstance(dbg, list) else dbg
    return str(dbg).lower() in ("1", "true", "yes", "on")

DEBUG = _get_debug_flag()

# =========================
# Tela de Login (ajustada no topo)
# =========================
def tela_login():
    # leve respiro no topo, sem centralizar verticalmente
    st.markdown("<div style='margin-top:2vh'></div>", unsafe_allow_html=True)

    # layout centrado horizontalmente
    _, center, _ = st.columns([1, 1.05, 1])
    with center:
        # card visual (classe vem do style.css, mas não depende dela para funcionar)
        st.markdown("<div class='auth-card'>", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 3])
        with c1:
            st.image("start.png", use_container_width=True)
        with c2:
            st.markdown(
                "<h1 class='titulo-app' style='margin-top:6px'>Agenda Profissional</h1>"
                "<p class='muted'>Acesse com seu e-mail e senha</p>",
                unsafe_allow_html=True,
            )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-mail", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            logar = st.form_submit_button("Entrar", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)  # fecha .auth-card

    if logar:
        try:
            u = validar_login(email, senha)
        except Exception as e:
            st.error("Erro durante validação de login.")
            if DEBUG:
                st.exception(e)
            return
        if u:
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Credenciais inválidas, inativas ou licença expirada.")

# =========================
# Sidebar (menu lateral)
# =========================
def sidebar_menu(is_admin: bool) -> str:
    with st.sidebar:
        # Cabeçalho visual
        st.markdown("<div class='sidebar-header'>", unsafe_allow_html=True)
        st.image("start.png", use_container_width=True)
        st.markdown("<div class='brand-title'>Agenda Profissional</div>", unsafe_allow_html=True)

        u = st.session_state.user or {}
        nome = u.get("nome", "(sem nome)")
        role = "Administrador" if u.get("is_admin") else "Usuário"
        st.markdown(
            f"<div class='user-chip'>👤 {nome} • <span>{role}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Opções do menu
        options = [
            "Dashboard",
            "Clientes",
            "Tipos de Serviços",
            "Lançamento de Serviços",
            "Agenda",
        ]
        icons = [
            "file-bar-graph-fill",
            "person-lines-fill",
            "book",
            "envelope",
            "calendar-date-fill",
        ]
        if is_admin:
            options.append("Profissionais")
            icons.append("people-fill")

        selected = option_menu(
            menu_title=None,
            options=options,
            icons=icons,
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
            styles={
                "container": {"padding": "0", "background": "transparent"},
                "icon": {"font-size": "20px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "2px 0",
                    "--hover-color": "#dff7ef",
                    "transition": "background 120ms ease"
                },
                "nav-link-selected": {
                    "background-color": "#1e8f6c",
                    "color": "white",
                    "font-weight": "700",
                    "box-shadow": "0 2px 8px rgba(0,0,0,.12)"
                },
            },
        )

        st.markdown(
            "<div class='sidebar-footer'><small>© Start Inteligência de Negócios</small></div>",
            unsafe_allow_html=True,
        )
        if st.button("Sair", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        return selected

# =========================
# Renderização de páginas
# =========================
def _render_page(modname: str):
    try:
        page = __import__(modname)
        if DEBUG:
            st.info(f"Render: {modname}")
        page.render()
    except ModuleNotFoundError as e:
        st.error(f"Módulo '{modname}' não encontrado. Crie {modname}.py no diretório do app.")
        if DEBUG:
            st.exception(e)
    except Exception as e:
        st.error(f"Erro ao renderizar a página '{modname}'.")
        if DEBUG:
            st.exception(e)

# =========================
# Main
# =========================
def main():
    if not st.session_state.user:
        tela_login()
        return

    u = st.session_state.user
    selected = sidebar_menu(u.get("is_admin", False))

    # Wrapper visual do conteúdo
    st.markdown("<div class='content-wrapper'>", unsafe_allow_html=True)

    pages = {
        "Dashboard": "dashboard",
        "Clientes": "clientes",
        "Tipos de Serviços": "tipos_servicos",
        "Lançamento de Serviços": "lancamento_servicos",
        "Agenda": "agenda",
        "Profissionais": "profissionais",
    }
    mod = pages.get(selected)
    if mod:
        _render_page(mod)
    else:
        st.write("Página não reconhecida.")

    st.markdown("</div>", unsafe_allow_html=True)  # fecha .content-wrapper

if __name__ == "__main__":
    main()
