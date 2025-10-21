import streamlit as st
import re
from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro

TABELA = "ag_clientes"
FORM_NS = "clientes_form"

# ----------------------
# Utilidades telefone
# ----------------------
def _digits_only(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")

def _format_phone_br(s: str | None) -> str:
    d = _digits_only(s)
    if len(d) >= 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:11]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:10]}"
    if len(d) >= 2:
        return f"({d[:2]}) {d[2:]}"
    return d

def _header():
    col_logo, col_title = st.columns([1,6])
    with col_logo:
        st.image("start.png", width=80)
    with col_title:
        st.markdown("<h2>Clientes</h2>", unsafe_allow_html=True)

def _v() -> int:
    if f"{FORM_NS}_version" not in st.session_state:
        st.session_state[f"{FORM_NS}_version"] = 0
    return st.session_state[f"{FORM_NS}_version"]

def _k(name: str) -> str:
    return f"{FORM_NS}_{name}_{_v()}"

@st.dialog("Editar Cliente")
def modal_editar(item):
    with st.form(f"form_edit_cliente_{item['id']}"):
        nome = st.text_input("Nome", value=item.get("nome",""))
        tel_raw = st.text_input(
            "Telefone",
            value=item.get("telefone",""),
            key=f"tel_edit_{item['id']}",
            help="Digite apenas números ou no formato (DD) 9XXXX-XXXX"
        )
        tel_preview = _format_phone_br(tel_raw)
        if tel_preview and tel_preview != tel_raw:
            st.caption(f"Formatado: {tel_preview}")
        email = st.text_input("Email", value=item.get("email",""))
        salvar = st.form_submit_button("Salvar")  # secundário
    if salvar:
        payload = {"nome": nome, "telefone": _format_phone_br(tel_raw), "email": email}
        atualizar_registro(TABELA, item["id"], payload)
        st.success("Atualizado!")
        st.rerun()

def render():
    u = st.session_state.get("user", {})
    prof_id = u.get("id")
    _header()

    with st.form("form_cliente", border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome *", key=_k("nome"))
        with c2:
            tel_raw = st.text_input(
                "Telefone",
                key=_k("tel"),
                help="Digite apenas números ou no formato (DD) 9XXXX-XXXX"
            )
            tel_preview = _format_phone_br(tel_raw)
            if tel_preview and tel_preview != tel_raw:
                st.caption(f"Formatado: {tel_preview}")
        with c3:
            email = st.text_input("Email", key=_k("email"))
        enviar = st.form_submit_button("Incluir", type="primary")
    if enviar:
        inserir_registro(TABELA, {
            "profissional_id": prof_id,
            "nome": nome,
            "telefone": _format_phone_br(tel_raw),
            "email": email
        })
        st.success("Cliente incluído!")
        st.session_state[f"{FORM_NS}_version"] = _v() + 1
        st.rerun()

    st.divider()
    st.subheader("Lista de clientes")

    itens = listar_registros(TABELA, {"profissional_id": prof_id}, order="nome")
    for it in itens:
        col_info, col_actions = st.columns([6, 4])
        with col_info:
            st.markdown(
                f"**{it.get('nome','')}**  \n"
                f"{it.get('telefone','')}  \n"
                f"{it.get('email','')}"
            )
        with col_actions:
            b1, b2 = st.columns([1, 1])
            edit = b1.button("Alterar", key=f"cli_edit_{it['id']}")
            delete = b2.button("Excluir", key=f"cli_del_{it['id']}")

        if edit:
            modal_editar(it)
        if delete:
            if st.session_state.get(f"confirm_cli_{it['id']}") != True:
                st.session_state[f"confirm_cli_{it['id']}"] = True
                st.warning("Clique novamente para confirmar.")
            else:
                excluir_registro(TABELA, it["id"])
                st.success("Excluído!")
                st.rerun()
