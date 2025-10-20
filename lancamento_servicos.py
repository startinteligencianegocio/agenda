# lancamento_servicos.py
import streamlit as st
from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro

TITLE = "Lançamento de Serviços"
TABELA = "ag_servicos"
FORM_NS = "lan_serv_form_v"

def _v() -> int:
    if FORM_NS not in st.session_state:
        st.session_state[FORM_NS] = 0
    return st.session_state[FORM_NS]

def _k(name: str) -> str:
    return f"{FORM_NS}_{name}_{_v()}"

def _header():
    col_logo, col_title = st.columns([1,6])
    with col_logo:
        st.image("start.png", width=80)
    with col_title:
        st.markdown(f"<h2 style='margin:0'>{TITLE}</h2>", unsafe_allow_html=True)

@st.dialog("Editar item de serviço")
def _modal_editar(item, prof_id: str):
    # Carrega agendas (precisamos de cliente_id) e tipos (precisamos do id do serviço)
    ags = listar_registros("ag_agenda", {"profissional_id": prof_id})
    ag_labels, ag_map = [], {}
    for a in ags:
        lab = f"{a.get('cliente_nome','(sem nome)')} • {a.get('data_atendimento','')} {a.get('hora_inicio','')}-{a.get('hora_fim','')}"
        ag_labels.append(lab)
        ag_map[lab] = a
    ag_label_atual = next((lab for lab, a in ag_map.items() if a["id"] == item.get("agenda_id")), (ag_labels[0] if ag_labels else None))

    tps = listar_registros("ag_tipos_servicos", {"profissional_id": prof_id, "ativo": True}, order="nome")
    ts_labels, ts_map = [], {}
    for t in tps:
        lab = f"{t.get('nome','')} — R$ {float(t.get('valor_padrao',0.0)):.2f} • {int(t.get('duracao_minutos',30))}min"
        ts_labels.append(lab)
        ts_map[lab] = t
    ts_label_atual = next((lab for lab, t in ts_map.items() if t["id"] == item.get("tipo_servico_id")), (ts_labels[0] if ts_labels else None))

    with st.form(f"form_edit_item_{item['id']}"):
        c1, c2 = st.columns([2,2])
        with c1:
            ag_sel = st.selectbox("Agendamento", options=ag_labels, index=(ag_labels.index(ag_label_atual) if ag_label_atual in ag_labels else 0))
            qtd = st.number_input("Quantidade", min_value=1, step=1, value=int(item.get("quantidade",1)))
        with c2:
            ts_sel = st.selectbox("Serviço", options=ts_labels, index=(ts_labels.index(ts_label_atual) if ts_label_atual in ts_labels else 0))
            val_unit = st.number_input("Valor unitário (R$)", min_value=0.0, step=0.5, value=float(item.get("valor_unitario",0.0)))

        salvar = st.form_submit_button("Salvar", type="primary")

    if salvar:
        ag = ag_map.get(ag_sel)
        ts = ts_map.get(ts_sel)
        if not ag or not ts:
            st.error("Selecione um agendamento e um serviço válidos.")
            return

        cli_id = ag.get("cliente_id")
        if cli_id is None:
            st.error("O agendamento selecionado não possui cliente vinculado (cliente_id). Corrija o agendamento antes de salvar.")
            return

        qtd_i = int(qtd)
        val_u = float(val_unit)
        total = val_u * qtd_i

        payload = {
            "agenda_id": ag["id"],
            "tipo_servico_id": ts["id"],          # <- seu schema usa 'tipo_servico_id'
            "profissional_id": prof_id,
            "cliente_id": int(cli_id),
            "quantidade": qtd_i,
            "valor_unitario": val_u,
            "valor_total": total,
            "valor": total,                       # <- NOVO: atende NOT NULL de 'valor'
        }
        atualizar_registro(TABELA, item["id"], payload)
        st.success("Item atualizado!")
        st.rerun()

def render():
    _header()

    u = st.session_state.get("user", {})
    prof_id = u.get("id")
    if not prof_id:
        st.error("Profissional não identificado na sessão.")
        return

    # Agendamentos (precisamos do cliente_id)
    ags = listar_registros("ag_agenda", {"profissional_id": prof_id}, order="data_atendimento")
    ag_labels, ag_map = [], {}
    for a in ags:
        lab = f"{a.get('cliente_nome','(sem nome)')} • {a.get('data_atendimento','')} {a.get('hora_inicio','')}-{a.get('hora_fim','')}"
        ag_labels.append(lab)
        ag_map[lab] = a

    # Tipos de serviço (apenas ativos)
    tps = listar_registros("ag_tipos_servicos", {"profissional_id": prof_id, "ativo": True}, order="nome")
    ts_labels, ts_map = [], {}
    for t in tps:
        lab = f"{t.get('nome','')} — R$ {float(t.get('valor_padrao',0.0)):.2f} • {int(t.get('duracao_minutos',30))}min"
        ts_labels.append(lab)
        ts_map[lab] = t

    st.subheader("Novo lançamento")
    with st.form("form_lanc_serv", border=True):
        c1, c2, c3 = st.columns([2,2,1])

        with c1:
            ag_sel = st.selectbox("Agendamento", options=ag_labels, index=0 if ag_labels else None, key=_k("ag"))
            qtd = st.number_input("Quantidade", min_value=1, step=1, value=1, key=_k("qtd"))
        with c2:
            ts_sel = st.selectbox("Serviço", options=ts_labels, index=0 if ts_labels else None, key=_k("ts"))
            valor_padrao = float(ts_map[ts_sel]["valor_padrao"]) if ts_sel in ts_map else 0.0
            val_unit = st.number_input("Valor unitário (R$)", min_value=0.0, step=0.5, value=valor_padrao, key=_k("val"))
        with c3:
            total_preview = (float(val_unit) * int(qtd)) if (ts_sel and ag_sel) else 0.0
            st.metric("Total (prev.)", f"R$ {total_preview:.2f}")

        enviar = st.form_submit_button("Incluir", type="primary")

    if enviar:
        if not ag_sel or not ts_sel:
            st.error("Selecione um agendamento e um serviço.")
            return

        ag = ag_map.get(ag_sel)
        ts = ts_map.get(ts_sel)
        if not ag or not ts:
            st.error("Seleção inválida de agendamento/serviço.")
            return

        cli_id = ag.get("cliente_id")
        if cli_id is None:
            st.error("O agendamento selecionado não possui cliente vinculado (cliente_id). Corrija o agendamento antes de lançar serviços.")
            return

        qtd_i = int(qtd)
        val_u = float(val_unit)
        total = val_u * qtd_i

        payload = {
            "agenda_id": ag["id"],
            "tipo_servico_id": ts["id"],      # <- nome conforme seu schema
            "profissional_id": prof_id,
            "cliente_id": int(cli_id),
            "quantidade": qtd_i,
            "valor_unitario": val_u,
            "valor_total": total,
            "valor": total,                   # <- preencher para NOT NULL
        }

        inserir_registro(TABELA, payload)
        st.success("Serviço lançado!")
        st.session_state[FORM_NS] = _v() + 1  # limpa inputs
        st.rerun()

    st.divider()
    st.subheader("Serviços lançados")

    itens = listar_registros(TABELA, {"profissional_id": prof_id})
    if not itens:
        st.info("Nenhum serviço lançado.")
        return

    # caches locais para exibir nomes
    _ag_by_id = {a["id"]: a for a in ags}
    _ts_by_id = {t["id"]: t for t in tps}

    for it in itens:
        ag = _ag_by_id.get(it.get("agenda_id"))
        ts = _ts_by_id.get(it.get("tipo_servico_id"))
        cliente_nome = (ag.get("cliente_nome") if ag else "")
        serv_nome = (ts.get("nome") if ts else "")

        col_info, col_actions = st.columns([7,3])
        with col_info:
            st.markdown(
                f"**Cliente:** {cliente_nome or '-'}  \n"
                f"**Serviço:** {serv_nome or '-'}  \n"
                f"**Qtd:** {int(it.get('quantidade',1))}  •  "
                f"**Vlr unit.:** R$ {float(it.get('valor_unitario',0.0)):.2f}  •  "
                f"**Total:** R$ {float(it.get('valor_total',0.0)):.2f}"
            )

        with col_actions:
            st.markdown('<div class="actions-right">', unsafe_allow_html=True)
            edit = st.button("Alterar", key=f"ls_edit_{it['id']}")
            st.markdown('<div class="btn-excluir">', unsafe_allow_html=True)
            delete = st.button("Excluir", key=f"ls_del_{it['id']}")
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if edit:
            _modal_editar(it, prof_id)

        if delete:
            if st.session_state.get(f"confirm_ls_{it['id']}") != True:
                st.session_state[f"confirm_ls_{it['id']}"] = True
                st.warning("Clique novamente para confirmar.")
            else:
                excluir_registro(TABELA, it["id"])
                st.success("Excluído!")
                st.rerun()
