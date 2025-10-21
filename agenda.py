# agenda.py
import streamlit as st
import pandas as pd
from datetime import date, time, datetime, timedelta
from urllib.parse import quote_plus

# Funções de banco (ajuste conforme seu módulo/database)
from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro

TAB_AGENDA = "ag_agenda"
TAB_CLIENTES = "ag_clientes"
TAB_PROFISSIONAIS = "ag_profissionais"
TAB_TIPOS = "ag_tipos_servicos"

STATUS_OPCOES = ["PENDENTE", "CONFIRMADO", "CANCELADO"]

def _get_df(tabela: str, filtros: dict | None = None) -> pd.DataFrame:
    """Wrapper com fallback seguro em caso de ausência de registros/colunas."""
    try:
        rows = listar_registros(tabela, filtros or {})
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        return df
    except Exception as e:
        st.warning(f"Não foi possível listar registros de {tabela}.")
        if st.session_state.get("DEBUG"):
            st.exception(e)
        return pd.DataFrame()

def _select_cliente(pro_key: str = "cli"):
    df = _get_df(TAB_CLIENTES)
    if df.empty:
        return None, None, None, st.selectbox("Cliente", ["(cadastre clientes)"], index=0, key=f"{pro_key}_empty", disabled=True)
    # tenta colunas comuns
    nome_col = next((c for c in df.columns if c.lower() in ("nome", "nome_razao", "nome_razao_social", "razao_social", "cliente")), None)
    id_col = next((c for c in df.columns if c.lower() in ("id", "cliente_id", "cod_cliente", "codigo")), None)
    fone_col = next((c for c in df.columns if "fone" in c.lower() or "cel" in c.lower() or "telefone" in c.lower()), None)
    email_col = next((c for c in df.columns if "mail" in c.lower() or "email" in c.lower()), None)

    df["_label"] = df.apply(lambda r: f"{str(r.get(id_col,''))} — {str(r.get(nome_col,''))}".strip(" —"), axis=1) if not df.empty else ""
    escolha = st.selectbox("Cliente", df["_label"].tolist(), index=0 if not df.empty else None, key=f"{pro_key}_cli")
    if not escolha or df.empty:
        return None, None, None, escolha
    row = df[df["_label"] == escolha].iloc[0]
    return row.get(id_col), row.get(nome_col), row.get(fone_col), escolha

def _select_profissional(pro_key: str = "pro"):
    df = _get_df(TAB_PROFISSIONAIS)
    if df.empty:
        return None, None, st.selectbox("Profissional", ["(cadastre profissionais)"], index=0, key=f"{pro_key}_empty", disabled=True)
    nome_col = next((c for c in df.columns if c.lower() in ("nome", "nome_prof", "profissional", "razao_social")), None)
    id_col = next((c for c in df.columns if c.lower() in ("id", "prof_id", "cod_profissional", "codigo")), None)

    df["_label"] = df.apply(lambda r: f"{str(r.get(id_col,''))} — {str(r.get(nome_col,''))}".strip(" —"), axis=1)
    escolha = st.selectbox("Profissional", df["_label"].tolist(), index=0, key=f"{pro_key}_prof")
    row = df[df["_label"] == escolha].iloc[0]
    return row.get(id_col), row.get(nome_col), escolha

def _select_tipo_servico(key: str = "tipo"):
    df = _get_df(TAB_TIPOS)
    if df.empty:
        return None, st.selectbox("Tipo de Serviço", ["(cadastre tipos de serviços)"], index=0, key=f"{key}_empty", disabled=True)
    nome_col = next((c for c in df.columns if c.lower() in ("nome", "descricao", "servico", "titulo")), None)
    id_col = next((c for c in df.columns if c.lower() in ("id", "tipo_id", "cod_tipo", "codigo")), None)
    preco_col = next((c for c in df.columns if "preco" in c.lower() or "valor" in c.lower()), None)

    df["_label"] = df.apply(
        lambda r: f"{str(r.get(id_col,''))} — {str(r.get(nome_col,''))}" + (f" (R$ {r.get(preco_col):.2f})" if preco_col in df.columns and pd.notna(r.get(preco_col)) else ""),
        axis=1
    )
    escolha = st.selectbox("Tipo de Serviço", df["_label"].tolist(), index=0, key=f"{key}_tipo")
    row = df[df["_label"] == escolha].iloc[0]
    return row.get(id_col), escolha

def _whatsapp_link(nome_prof: str, data_ag: date, hora_ini: time, fone: str | None) -> str | None:
    if not fone:
        return None
    data_str = data_ag.strftime("%d/%m/%Y")
    hora_str = hora_ini.strftime("%H:%M")
    # Mensagem em 2 linhas como você pediu:
    msg = (
        f"Aqui é {nome_prof}, você tem um horário agendado em {data_str} às {hora_str} hrs.\n"
        "Por Favor, responda : 1 - Confirmar / 2 - Cancelar"
    )
    texto = quote_plus(msg)
    # Normaliza número (tira símbolos); assuma DDI Brasil se faltando
    numero = "".join([c for c in str(fone) if c.isdigit()])
    if numero and numero.startswith("0"):
        numero = numero.lstrip("0")
    if len(numero) <= 11 and not numero.startswith("55"):
        numero = "55" + numero
    return f"https://wa.me/{numero}?text={texto}"

def _form_incluir_agenda():
    st.subheader("➕ Incluir agendamento")
    with st.form("form_ag_incluir", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            data_ag = st.date_input("Data", value=date.today())
        with col2:
            hora_ini = st.time_input("Hora início", value=time(9, 0))
        with col3:
            duracao_min = st.number_input("Duração (min)", min_value=15, max_value=480, value=60, step=15)
        with col4:
            status = st.selectbox("Status", STATUS_OPCOES, index=0)

        col5, col6 = st.columns([1, 1])
        with col5:
            prof_id, prof_nome, _ = _select_profissional("inc")
        with col6:
            cli_id, cli_nome, cli_fone, _ = _select_cliente("inc")

        tipo_id, _ = _select_tipo_servico("inc")

        obs = st.text_area("Observações", placeholder="Observações do atendimento (opcional)", height=80)

        enviar = st.form_submit_button("Incluir", use_container_width=True)

    if enviar:
        try:
            payload = {
                "data": data_ag.isoformat(),
                "hora_inicio": hora_ini.strftime("%H:%M:%S"),
                "duracao_min": int(duracao_min),
                "status": status,
                "profissional_id": prof_id,
                "cliente_id": cli_id,
                "tipo_id": tipo_id,
                "obs": obs,
                "criado_em": datetime.now().isoformat(sep=" ", timespec="seconds"),
            }
            inserir_registro(TAB_AGENDA, payload)
            st.toast("✅ Agenda inserida", icon="✅")

            # Mostra link do WhatsApp já no fluxo de inclusão:
            wa = _whatsapp_link(prof_nome or "", data_ag, hora_ini, cli_fone)
            if wa:
                st.markdown(
                    f"<a href='{wa}' target='_blank' class='btn btn-whatsapp btn-whatsapp-large'>Abrir WhatsApp</a>",
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.error("Falha ao incluir agendamento.")
            if st.session_state.get("DEBUG"):
                st.exception(e)

def _filtro_periodo():
    with st.expander("📅 Filtro de período", expanded=True):
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            inicio = st.date_input("Início", value=date.today() - timedelta(days=0), key="f_ini")
        with col2:
            fim = st.date_input("Fim", value=date.today(), key="f_fim")
        with col3:
            profiltro = st.text_input("Filtrar por Profissional (contém)", placeholder="Nome, parte do nome…")
    return inicio, fim, profiltro

def _carregar_agendas(inicio: date, fim: date, profiltro: str = "") -> pd.DataFrame:
    df = _get_df(TAB_AGENDA)
    if df.empty:
        return df

    # Normaliza possíveis colunas
    # datas
    data_col = next((c for c in df.columns if c.lower() in ("data", "data_agenda", "dt_agenda", "dia")), None)
    hora_col = next((c for c in df.columns if "hora" in c.lower() and "inicio" in c.lower()), None)
    status_col = next((c for c in df.columns if c.lower() == "status"), None)
    prof_id_col = next((c for c in df.columns if "prof" in c.lower() and "id" in c.lower()), None)
    cli_id_col = next((c for c in df.columns if "cli" in c.lower() and "id" in c.lower()), None)
    obs_col = next((c for c in df.columns if c.lower() in ("obs", "observacao", "observacoes")), None)

    # converte datas/horas
    if data_col:
        df[data_col] = pd.to_datetime(df[data_col], errors="coerce").dt.date
    if hora_col and hora_col in df.columns:
        df[hora_col] = pd.to_datetime(df[hora_col], errors="coerce").dt.time
    # filtra período
    if data_col:
        df = df[(df[data_col] >= inicio) & (df[data_col] <= fim)]

    # join com profissionais e clientes para exibir nomes/telefones
    dfp = _get_df(TAB_PROFISSIONAIS)
    dfc = _get_df(TAB_CLIENTES)
    nome_prof_col = next((c for c in (dfp.columns if not dfp.empty else []) if c.lower() in ("nome","nome_prof","razao_social","profissional")), None)
    id_prof_col = next((c for c in (dfp.columns if not dfp.empty else []) if c.lower() in ("id","prof_id","cod_profissional","codigo")), None)
    nome_cli_col = next((c for c in (dfc.columns if not dfc.empty else []) if c.lower() in ("nome","nome_razao","razao_social","cliente")), None)
    id_cli_col = next((c for c in (dfc.columns if not dfc.empty else []) if c.lower() in ("id","cliente_id","cod_cliente","codigo")), None)
    fone_cli_col = next((c for c in (dfc.columns if not dfc.empty else []) if "fone" in c.lower() or "cel" in c.lower() or "telefone" in c.lower()), None)

    if not df.empty and data_col:
        # adiciona colunas auxiliares
        if prof_id_col and not dfp.empty and id_prof_col:
            df = df.merge(dfp[[id_prof_col, nome_prof_col]], left_on=prof_id_col, right_on=id_prof_col, how="left", suffixes=("","_p"))
            df.rename(columns={nome_prof_col: "nome_prof"}, inplace=True)
        if cli_id_col and not dfc.empty and id_cli_col:
            base_cols = [id_cli_col]
            if nome_cli_col: base_cols.append(nome_cli_col)
            if fone_cli_col: base_cols.append(fone_cli_col)
            df = df.merge(dfc[base_cols], left_on=cli_id_col, right_on=id_cli_col, how="left", suffixes=("","_c"))
            if nome_cli_col: df.rename(columns={nome_cli_col: "nome_cli"}, inplace=True)
            if fone_cli_col: df.rename(columns={fone_cli_col: "fone_cli"}, inplace=True)

        # filtro por nome do profissional
        if profiltro and "nome_prof" in df.columns:
            df = df[df["nome_prof"].astype(str).str.contains(profiltro, case=False, na=False)]

        # normalização segura
        if status_col and status_col in df.columns:
            df["status_norm"] = df[status_col].astype(str).str.upper()
        else:
            df["status_norm"] = "PENDENTE"

        if hora_col and hora_col in df.columns:
            df["hora_sort"] = df[hora_col].apply(lambda x: (x.hour, x.minute) if pd.notna(x) else (99,99))
        else:
            df["hora_sort"] = (99,99)

        df.sort_values(by=[data_col, "hora_sort"], inplace=True, ignore_index=True)

    return df

def _card_agendamento(row: pd.Series, data_col: str, hora_col: str | None, status_col: str | None):
    nome_prof = str(row.get("nome_prof") or "")
    nome_cli = str(row.get("nome_cli") or "")
    fone_cli = row.get("fone_cli")
    obs = row.get("obs") or row.get("observacao") or ""

    d: date = row.get(data_col)
    h: time | None = row.get(hora_col) if hora_col else None
    htxt = h.strftime("%H:%M") if isinstance(h, time) else "--:--"

    with st.container(border=True):
        st.markdown(f"**{nome_cli or '(Sem nome)'}** — {nome_prof or '(Sem prof.)'}")
        st.caption(f"📅 {d.strftime('%d/%m/%Y')} • 🕒 {htxt}")
        if obs:
            st.write(obs)

        # Botões de ação
        st.markdown("<div class='kanban-actions'>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1,1,1,1])

        # MOVER (troca de status via select)
        with c1:
            with st.popover("Mover", use_container_width=True):
                novo_status = st.selectbox("Novo status", STATUS_OPCOES, index=0, key=f"mv_{row.name}_{d}_{htxt}")
                if st.button("Aplicar", use_container_width=True, key=f"mv_ok_{row.name}_{d}_{htxt}"):
                    try:
                        rid = row.get("id") or row.get("ID") or row.get("pk") or row.get("codigo")
                        if rid is None:
                            st.error("ID não encontrado para atualizar.")
                        else:
                            atualizar_registro(TAB_AGENDA, int(rid), {"status": novo_status})
                            st.toast("✅ Status atualizado")
                            st.rerun()
                    except Exception as e:
                        st.error("Falha ao mover agendamento.")
                        if st.session_state.get("DEBUG"): st.exception(e)

        # ALTERAR (abre um mini form inline)
        with c2:
            with st.popover("Alterar", use_container_width=True):
                nova_hora = st.time_input("Hora", value=h or time(9,0), key=f"alt_hr_{row.name}_{d}_{htxt}")
                nova_obs = st.text_area("Observações", value=str(obs), key=f"alt_obs_{row.name}_{d}_{htxt}")
                if st.button("Salvar", use_container_width=True, key=f"alt_ok_{row.name}_{d}_{htxt}"):
                    try:
                        rid = row.get("id") or row.get("ID") or row.get("pk") or row.get("codigo")
                        if rid is None:
                            st.error("ID não encontrado para atualizar.")
                        else:
                            atualizar_registro(TAB_AGENDA, int(rid), {
                                "hora_inicio": nova_hora.strftime("%H:%M:%S"),
                                "obs": nova_obs
                            })
                            st.toast("✅ Alterações salvas")
                            st.rerun()
                    except Exception as e:
                        st.error("Falha ao alterar agendamento.")
                        if st.session_state.get("DEBUG"): st.exception(e)

        # EXCLUIR
        with c3:
            if st.button("Excluir", use_container_width=True, key=f"del_{row.name}_{d}_{htxt}"):
                try:
                    rid = row.get("id") or row.get("ID") or row.get("pk") or row.get("codigo")
                    if rid is None:
                        st.error("ID não encontrado para excluir.")
                    else:
                        excluir_registro(TAB_AGENDA, int(rid))
                        st.toast("🗑️ Agendamento excluído")
                        st.rerun()
                except Exception as e:
                    st.error("Falha ao excluir agendamento.")
                    if st.session_state.get("DEBUG"): st.exception(e)

        # WHATSAPP
        with c4:
            wa = _whatsapp_link(nome_prof, d, h or time(0,0), fone_cli)
            if wa:
                st.markdown(f"<a href='{wa}' target='_blank' class='btn btn-whatsapp btn-whatsapp-large'>WhatsApp</a>", unsafe_allow_html=True)
            else:
                st.caption("Sem telefone para WhatsApp")
        st.markdown("</div>", unsafe_allow_html=True)

def _kanban(df: pd.DataFrame):
    if df.empty:
        st.info("Sem agendamentos para o período selecionado.")
        return

    data_col = next((c for c in df.columns if c.lower() in ("data","data_agenda","dt_agenda","dia")), None)
    hora_col = next((c for c in df.columns if "hora" in c.lower() and "inicio" in c.lower()), None)
    status_col = next((c for c in df.columns if c.lower() == "status"), None)

    cols = st.columns(3)
    blocos = [("PENDENTE", cols[0]), ("CONFIRMADO", cols[1]), ("CANCELADO", cols[2])]

    for status, col in blocos:
        with col:
            st.markdown(f"### {status.title()}")
            sub = df[df["status_norm"] == status].reset_index(drop=True)
            if sub.empty:
                st.caption("— vazio —")
            else:
                for _, row in sub.iterrows():
                    _card_agendamento(row, data_col, hora_col, status_col)

def render():
    st.markdown("## 📆 Agenda")
    _form_incluir_agenda()

    st.markdown("---")
    inicio, fim, profiltro = _filtro_periodo()
    df = _carregar_agendas(inicio, fim, profiltro)

    _kanban(df)

    with st.expander("🛠️ Disponibilidade (em breve)"):
        st.caption("Área reservada para futuras configurações de grade de horários do profissional.")
