
import streamlit as st
from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro
from masklib import masked_text_input, PHONE_BR

TABELA = "ag_clientes"
FORM_NS = "clientes_form"

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
        tel_masked = masked_text_input("Telefone", key=f"tel_edit_{item['id']}", mask=PHONE_BR, value=item.get("telefone",""), in_form=True)
        email = st.text_input("Email", value=item.get("email",""))
        salvar = st.form_submit_button("Salvar")  # secundário
    if salvar:
        payload = {"nome": nome, "telefone": tel_masked, "email": email}
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
            tel_masked = masked_text_input("Telefone", key=_k("tel"), mask=PHONE_BR, value="", in_form=True)
        with c3:
            email = st.text_input("Email", key=_k("email"))
        enviar = st.form_submit_button("Incluir", type="primary")
    if enviar:
        inserir_registro(TABELA, {
            "profissional_id": prof_id, "nome": nome, "telefone": tel_masked, "email": email
        })
        st.success("Cliente incluído!")
        st.session_state[f"{FORM_NS}_version"] = _v() + 1
        st.rerun()

    st.divider()
    st.subheader("Lista de clientes")

    itens = listar_registros(TABELA, {"profissional_id": prof_id}, order="nome")
    for it in itens:
        col_info, col_actions = st.columns([6, 4])  # mais espaço para ações
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
