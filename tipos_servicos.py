
import streamlit as st
from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro

TABELA = "ag_tipos_servicos"
FORM_NS = "tipos_serv_form_v"

def _header():
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.image("start.png", width=80)
    with col_title:
        st.markdown("<h2>Tipos de Serviços</h2>", unsafe_allow_html=True)

def _v() -> int:
    """Versão do formulário para limpar inputs após incluir."""
    if FORM_NS not in st.session_state:
        st.session_state[FORM_NS] = 0
    return st.session_state[FORM_NS]

def _k(name: str) -> str:
    """Gera key única baseada na versão do form."""
    return f"{FORM_NS}_{name}_{_v()}"

@st.dialog("Editar Serviço")
def modal_editar(item: dict):
    with st.form(f"form_edit_ts_{item['id']}"):
        nome = st.text_input("Nome", value=item.get("nome", ""))
        descricao = st.text_area("Descrição", value=item.get("descricao", ""))
        valor_padrao = st.number_input(
            "Valor Padrão (R$)", min_value=0.0, step=0.5,
            value=float(item.get("valor_padrao", 0.0))
        )
        ativo = st.checkbox("Ativo", value=bool(item.get("ativo", True)))
        duracao = st.number_input(
            "Duração (min)", min_value=5, step=5,
            value=int(item.get("duracao_minutos", 30))
        )
        salvar = st.form_submit_button("Salvar")  # secondary
    if salvar:
        atualizar_registro(
            TABELA, item["id"],
            {
                "nome": nome,
                "descricao": descricao,
                "valor_padrao": float(valor_padrao),
                "ativo": bool(ativo),
                "duracao_minutos": int(duracao),
            },
        )
        st.success("Atualizado!")
        st.rerun()

def render():
    _header()
    u = st.session_state.get("user", {})
    prof_id = u.get("id")

    # ===== Formulário de inclusão =====
    with st.form("form_ts", border=True):
        c1, c2 = st.columns([2, 2])
        with c1:
            nome = st.text_input("Nome *", key=_k("nome"))
            valor_padrao = st.number_input(
                "Valor Padrão (R$)", min_value=0.0, value=0.0, step=0.5, key=_k("valor")
            )
            ativo = st.checkbox("Ativo", value=True, key=_k("ativo"))
        with c2:
            descricao = st.text_area("Descrição", key=_k("desc"))
            duracao = st.number_input(
                "Duração (min)", min_value=5, value=30, step=5, key=_k("dur")
            )
        enviar = st.form_submit_button("Incluir", type="primary")
    if enviar:
        inserir_registro(
            TABELA,
            {
                "profissional_id": prof_id,
                "nome": nome,
                "descricao": descricao,
                "valor_padrao": float(valor_padrao),
                "ativo": bool(ativo),
                "duracao_minutos": int(duracao),
            },
        )
        st.success("Serviço incluído!")
        st.session_state[FORM_NS] = _v() + 1  # limpa inputs
        st.rerun()

    st.divider()
    st.subheader("Serviços cadastrados")

    itens = listar_registros(TABELA, {"profissional_id": prof_id}, order="nome")
    if not itens:
        st.info("Nenhum serviço cadastrado.")
        return

    for it in itens:
        # lista com ações mais largas e botões lado a lado
        col_info, col_actions = st.columns([6, 4])

        with col_info:
            nome_srv = it.get("nome", "")
            ativo_txt = "Ativo" if it.get("ativo") else "Inativo"
            desc_txt = it.get("descricao", "") or ""
            dur_txt = int(it.get("duracao_minutos", 30))
            val_txt = float(it.get("valor_padrao", 0.0))
            st.markdown(
                f"**{nome_srv}** — {ativo_txt}  \n"
                f"{desc_txt}  \n"
                f"Duração: {dur_txt} min • Valor padrão: R$ {val_txt:.2f}"
            )

        with col_actions:
            b1, b2 = st.columns([1, 1])
            edit = b1.button("Alterar", key=f"ts_edit_{it['id']}")
            delete = b2.button("Excluir", key=f"ts_del_{it['id']}")

        if edit:
            modal_editar(it)
        if delete:
            confirm_key = f"confirm_ts_{it['id']}"
            if st.session_state.get(confirm_key) is not True:
                st.session_state[confirm_key] = True
                st.warning("Clique novamente para confirmar a exclusão.")
            else:
                excluir_registro(TABELA, it["id"])
                st.success("Excluído!")
                st.rerun()
