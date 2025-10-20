# agenda.py
import streamlit as st
from datetime import date, time, datetime, timedelta
from urllib.parse import quote
import pandas as pd

from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro
from masklib import masked_text_input, PHONE_BR
from utils_layout import whatsapp_icon

STATUS = ["Pendente", "Confirmado", "Concluído", "Cancelado"]
FORM_NS = "agenda_form_v"


def _header():
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.image("start.png", width=80)
    with col_title:
        st.markdown("<h2>Agenda</h2>", unsafe_allow_html=True)


def _carregar_clientes(prof_id: str):
    return listar_registros("ag_clientes", {"profissional_id": prof_id}, order="nome")


def _carregar_profissional(prof_id: str) -> dict | None:
    arr = listar_registros("ag_profissionais", {"id": prof_id})
    return arr[0] if arr else None


def _v() -> int:
    if FORM_NS not in st.session_state:
        st.session_state[FORM_NS] = 0
    return st.session_state[FORM_NS]


def _k(name: str) -> str:
    return f"{FORM_NS}_{name}_{_v()}"


@st.dialog("Editar Atendimento")
def modal_editar(item):
    with st.form(f"form_edit_ag_{item['id']}"):
        cliente_nome = st.text_input("Cliente", value=item.get("cliente_nome", ""))
        tel_masked = masked_text_input(
            "Telefone",
            key=f"tel_ag_edit_{item['id']}",
            mask=PHONE_BR,
            value=item.get("cliente_telefone", ""),
            in_form=True,
        )
        data_atendimento = st.date_input("Data", value=date.fromisoformat(item.get("data_atendimento")))
        hora_inicio = st.time_input("Hora início", value=time.fromisoformat(item.get("hora_inicio")))
        hora_fim = st.time_input("Hora fim", value=time.fromisoformat(item.get("hora_fim")))
        status = st.selectbox("Status", STATUS, index=STATUS.index(item.get("status", "Pendente")))
        observacoes = st.text_area("Observações", value=item.get("observacoes", ""))
        salvar = st.form_submit_button("Salvar")
    if salvar:
        atualizar_registro("ag_agenda", item["id"], {
            "cliente_nome": cliente_nome,
            "cliente_telefone": tel_masked,
            "data_atendimento": str(data_atendimento),
            "hora_inicio": str(hora_inicio),
            "hora_fim": str(hora_fim),
            "status": status,
            "observacoes": observacoes,
        })
        st.success("Atualizado!")
        st.rerun()


def _whatsapp_link(nome_prof: str, tel: str, data_str: str, hora_ini: str):
    num = (tel or "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    msg = (
        f"Aqui é {nome_prof}, você tem um horário agendado em {data_str} às {hora_ini} hrs.\n"
        f"Por Favor, responda : 1 - Confirmar / 2 - Cancelar"
    )
    return f"https://wa.me/{num}?text={quote(msg)}"


# ----------------------
# Utilidades Tab 3
# ----------------------
def _to_dt(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def _overlaps(a_ini: datetime, a_fim: datetime, b_ini: datetime, b_fim: datetime) -> bool:
    # intervalo [início, fim)
    return (a_ini < b_fim) and (a_fim > b_ini)


def _weekday_iso(d: date) -> int:
    # ISO: Monday=1 ... Sunday=7
    return (d.weekday() + 1)


def _weekday_pt(d: date) -> str:
    nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    return nomes[d.weekday()]


def _feriados_fixos_br(ano: int) -> set[date]:
    # Fixos nacionais (sem móveis)
    base = [
        (1, 1),   # Confraternização Universal
        (4, 21),  # Tiradentes
        (5, 1),   # Dia do Trabalho
        (9, 7),   # Independência
        (10, 12), # N. Sra. Aparecida
        (11, 2),  # Finados
        (11, 15), # Proclamação da República
        (12, 25), # Natal
    ]
    return {date(ano, m, d) for (m, d) in base}


def _dia_permitido(d: date, prof: dict) -> bool:
    ds = (prof.get("dias_semana") or "").strip()
    if ds:
        permitidos = {int(x) for x in ds.split(",") if x.strip().isdigit()}
        return _weekday_iso(d) in permitidos
    wd = _weekday_iso(d)
    if wd in {1, 2, 3, 4, 5}:
        return True
    if wd == 6:
        return bool(prof.get("aceita_sabado"))
    if wd == 7:
        return bool(prof.get("aceita_domingo"))
    return True


def _as_time(prof: dict | None, field: str, default: time | None) -> time | None:
    if not prof:
        return default
    val = prof.get(field)
    if not val:
        return default
    try:
        s = str(val)
        if len(s) == 5:
            s += ":00"
        hh, mm, ss = map(int, s.split(":"))
        return time(hh, mm, ss)
    except Exception:
        return default


def _build_grade_disponibilidade(
    dados_agenda: list,
    prof: dict,
    prof_id: str,
    data_ini: date,
    data_fim: date,
    jornada_ini: time,
    jornada_fim: time,
    slot_min: int,
    buffer_min: int,
    almoco_ini: time | None,
    almoco_fim: time | None,
    considerar_feriados: bool,
    capacidade: int,
) -> pd.DataFrame:
    """
    Gera slots e marca Disponível/Ocupado conforme:
      - dias permitidos pelo profissional
      - jornada e intervalo de almoço (slots no almoço são ignorados)
      - buffer entre atendimentos (aplicado ao fim do slot)
      - capacidade simultânea
    """
    rows = []

    # Índice por data com atendimentos do período
    idx = {}
    for a in dados_agenda:
        if str(a.get("profissional_id")) != str(prof_id):
            continue
        try:
            d = date.fromisoformat(a.get("data_atendimento"))
            if not (data_ini <= d <= data_fim):
                continue
            hi = time.fromisoformat(a.get("hora_inicio"))
            hf = time.fromisoformat(a.get("hora_fim"))
        except Exception:
            continue
        idx.setdefault(d, []).append({
            "ini": _to_dt(d, hi),
            "fim": _to_dt(d, hf),
            "cliente": a.get("cliente_nome", ""),
            "status": a.get("status", ""),
            "obs": a.get("observacoes", "")
        })

    # Feriados fixos
    feriados = set()
    if considerar_feriados:
        for an in {data_ini.year, data_fim.year}:
            feriados |= _feriados_fixos_br(an)

    dia = data_ini
    while dia <= data_fim:
        if not _dia_permitido(dia, prof):
            dia += timedelta(days=1)
            continue
        if considerar_feriados and dia in feriados:
            dia += timedelta(days=1)
            continue

        slot_ini = _to_dt(dia, jornada_ini)
        jornada_f = _to_dt(dia, jornada_fim)

        while slot_ini < jornada_f:
            slot_fim = slot_ini + timedelta(minutes=int(slot_min))
            if slot_fim > jornada_f:
                break

            # Ignora slot dentro do almoço
            if almoco_ini and almoco_fim:
                a_ini = _to_dt(dia, almoco_ini)
                a_fim = _to_dt(dia, almoco_fim)
                if _overlaps(slot_ini, slot_fim, a_ini, a_fim):
                    # pula direto para o fim do almoço
                    slot_ini = max(slot_fim, a_fim)
                    continue

            # Conta sobreposições
            sobrepos = 0
            det_cliente = det_status = det_obs = ""
            for ag in idx.get(dia, []):
                if _overlaps(slot_ini, slot_fim, ag["ini"], ag["fim"]):
                    sobrepos += 1
                    if not det_cliente:
                        det_cliente, det_status, det_obs = ag["cliente"], ag["status"], ag["obs"]

            situacao = "Disponível" if sobrepos < int(capacidade or 1) else "Ocupado"

            rows.append({
                "Data": dia.strftime("%Y-%m-%d"),
                "Dia Semana": _weekday_pt(dia),
                "Horário": f"{slot_ini.strftime('%H:%M')} - {slot_fim.strftime('%H:%M')}",
                "Situação": situacao,
                "Cliente": det_cliente if situacao == "Ocupado" else "",
                "Status Atendimento": det_status if situacao == "Ocupado" else "",
                "Obs.": det_obs if situacao == "Ocupado" else "",
            })

            slot_ini = slot_fim + timedelta(minutes=int(buffer_min or 0))

        dia += timedelta(days=1)

    df = pd.DataFrame(rows)
    if not df.empty:
        df["__d"] = pd.to_datetime(df["Data"])
        df["__h"] = df["Horário"].str.slice(0, 5)
        df = df.sort_values(["__d", "__h"]).drop(columns=["__d", "__h"])
    return df


# ----------------------
# RENDER
# ----------------------
def render():
    _header()
    u = st.session_state.get("user", {})
    prof_id = u.get("id")
    prof_nome = u.get("nome")

    if not prof_id:
        st.error("Profissional não identificado na sessão.")
        return

    # flash pós-inclusão
    if st.session_state.get("flash_agenda_ok"):
        st.toast("✅ Agenda inserida com sucesso!", icon="🎉")
        st.success("Agenda inserida com sucesso!")
        del st.session_state["flash_agenda_ok"]

    profissional = _carregar_profissional(prof_id)
    dados = listar_registros("ag_agenda", {"profissional_id": prof_id})

    tab1, tab2, tab3 = st.tabs(["📝 Agendar", "📊 Dashboard", "🗓️ Disponibilidade"])

    # ---------------- TAB 1: Agendar ----------------
    with tab1:
        clientes = _carregar_clientes(prof_id)
        nomes = [c.get("nome", "") for c in clientes]
        mapa_nome_cli = {c.get("nome", ""): c for c in clientes}

        st.subheader("Novo atendimento")
        col_sel, _ = st.columns([2, 6])
        with col_sel:
            nome_sel = st.selectbox(
                "Cliente",
                options=["(Novo cliente)"] + nomes,
                index=0,
                key=f"{FORM_NS}_cli_sel_outside"
            )

        with st.form("form_ag", border=True):
            c2, c3, c4 = st.columns(3)
            with c2:
                data_atendimento = st.date_input("Data", value=date.today(), key=_k("data"))
            with c3:
                hora_inicio = st.time_input("Hora Início", key=_k("hora_ini"))
                observacoes = st.text_area("Observações", key=_k("obs"))
            with c4:
                dur = st.number_input(
                    "Duração (min)", min_value=5, step=5,
                    value=int((profissional or {}).get("slot_minutos") or 30),
                    key=_k("dur")
                )
                status = st.selectbox("Status", STATUS, index=0, key=_k("status"))

            enviar = st.form_submit_button("Incluir", type="primary")

        if enviar:
            if nome_sel == "(Novo cliente)":
                st.error("Selecione um cliente existente ou cadastre-o primeiro no módulo **Clientes**.")
                st.stop()

            cli = mapa_nome_cli.get(nome_sel)
            if not cli:
                st.error("Cliente inválido. Atualize a página e tente novamente.")
                st.stop()

            hi = datetime.combine(data_atendimento, hora_inicio)
            hf = hi + timedelta(minutes=int(dur))

            inserir_registro("ag_agenda", {
                "profissional_id": prof_id,
                "cliente_id": int(cli["id"]),
                "cliente_nome": cli.get("nome", ""),
                "cliente_telefone": cli.get("telefone", ""),
                "data_atendimento": str(data_atendimento),
                "hora_inicio": str(hora_inicio),
                "hora_fim": str(hf.time()),
                "status": status,
                "observacoes": observacoes,
            })
            st.session_state["flash_agenda_ok"] = True
            st.session_state[FORM_NS] = _v() + 1
            st.rerun()

    # ---------------- TAB 2: Dashboard ----------------
    with tab2:
        st.subheader("Resumo da Agenda")
        total = len(dados)
        por_status = {s: 0 for s in STATUS}
        for a in dados:
            por_status[a.get("status", "Pendente")] = por_status.get(a.get("status", "Pendente"), 0) + 1

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total", total)
        k2.metric("Pendente", por_status.get("Pendente", 0))
        k3.metric("Confirmado", por_status.get("Confirmado", 0))
        k4.metric("Concluído", por_status.get("Concluído", 0))
        k5.metric("Cancelado", por_status.get("Cancelado", 0))

        st.divider()
        st.subheader("Atendimentos por Status (Kanban)")

        dados_por_status = {s: [] for s in STATUS}
        for a in dados:
            s = a.get("status", "Pendente")
            if s not in dados_por_status:
                s = "Pendente"
            dados_por_status[s].append(a)

        cols = st.columns(4)
        for stt, col in zip(STATUS, cols):
            with col:
                st.markdown(f"<div class='kanban-title {stt.lower()}'>{stt}</div>", unsafe_allow_html=True)
                for a in dados_por_status[stt]:
                    with st.container(border=True):
                        st.write(f"**{a['cliente_nome']}**")
                        st.write(f"📅 {a['data_atendimento']} ⏰ {a['hora_inicio']} - {a['hora_fim']}")
                        if a.get("observacoes"):
                            st.write(a["observacoes"])

                        m1, m2 = st.columns([2, 1])
                        destinos = [s for s in STATUS if s != stt]
                        novo_status = m1.selectbox("Mover para", options=destinos, key=f"mv_to_{a['id']}")
                        mover = m2.button("Mover", key=f"mv_btn_{a['id']}")
                        if mover:
                            atualizar_registro("ag_agenda", a["id"], {"status": novo_status})
                            st.success(f"Movido para {novo_status}")
                            st.rerun()

                        cbtn1, cbtn2, cicon = st.columns([1, 1, 0.5])
                        edit = cbtn1.button("Alterar", key=f"ag_edit_{a['id']}")
                        delete = cbtn2.button("Excluir", key=f"ag_del_{a['id']}")
                        link = _whatsapp_link(prof_nome, a.get("cliente_telefone", ""), a["data_atendimento"], a["hora_inicio"])
                        with cicon:
                            whatsapp_icon(link, size=22)

                        if edit:
                            modal_editar(a)
                        if delete:
                            if st.session_state.get(f"confirm_ag_{a['id']}") != True:
                                st.session_state[f"confirm_ag_{a['id']}"] = True
                                st.warning("Clique novamente para confirmar.")
                            else:
                                dependentes = listar_registros("ag_servicos", {"agenda_id": a["id"]})
                                for dd in dependentes:
                                    excluir_registro("ag_servicos", dd["id"])
                                excluir_registro("ag_agenda", a["id"])
                                st.success("Excluído!")
                                st.rerun()

    # ---------------- TAB 3: Disponibilidade ----------------
    with tab3:
        st.subheader("Disponibilidade por Período")

        hoje = date.today()

        # Defaults do profissional
        j_ini_default = _as_time(profissional, "hora_inicio_jornada", time(8, 0))
        j_fim_default = _as_time(profissional, "hora_fim_jornada", time(18, 0))
        alm_ini_default = _as_time(profissional, "almoco_inicio", None)
        alm_fim_default = _as_time(profissional, "almoco_fim", None)
        slot_default = int((profissional or {}).get("slot_minutos") or 30)
        buffer_default = int((profissional or {}).get("buffer_minutos") or 0)
        cap_default = int((profissional or {}).get("capacidade_simultanea") or 1)
        considerar_feriados = bool((profissional or {}).get("considerar_feriados") or False)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            dt_ini = st.date_input("Data inicial", value=hoje, min_value=hoje, key="disp_dt_ini")
        with c2:
            dt_fim = st.date_input("Data final", value=hoje + timedelta(days=7), min_value=dt_ini, key="disp_dt_fim")
        with c3:
            jornada_inicio = st.time_input("Início da jornada", value=j_ini_default)
        with c4:
            jornada_fim = st.time_input("Fim da jornada", value=j_fim_default)

        c5, c6, c7 = st.columns(3)
        with c5:
            slot_min = st.number_input("Duração do Slot (min)", min_value=5, step=5, value=slot_default)
        with c6:
            buffer_min = st.number_input("Buffer entre Slots (min)", min_value=0, step=5, value=buffer_default)
        with c7:
            cap_sim = st.number_input("Capacidade Simultânea", min_value=1, step=1, value=cap_default)

        # Almoço opcional (toggle para evitar None em time_input)
        use_lunch = (alm_ini_default is not None and alm_fim_default is not None)
        use_lunch = st.toggle("Considerar intervalo de almoço?", value=use_lunch, help="Ative para bloquear slots no horário do almoço.")
        if use_lunch:
            c8, c9 = st.columns(2)
            with c8:
                almoco_inicio = st.time_input("Almoço (início)", value=alm_ini_default or time(12, 0))
            with c9:
                almoco_fim = st.time_input("Almoço (fim)", value=alm_fim_default or time(13, 0))
        else:
            almoco_inicio, almoco_fim = None, None

        # Validações (inclui trava dt_ini >= hoje)
        if dt_ini < hoje:
            st.warning("Ajustei a data inicial para hoje, pois não é permitido período anterior à data atual.")
            dt_ini = hoje
            if dt_fim < dt_ini:
                dt_fim = dt_ini

        if dt_fim < dt_ini:
            st.error("A data final deve ser maior ou igual à data inicial.")
            st.stop()

        if jornada_fim <= jornada_inicio:
            st.error("O fim da jornada deve ser maior que o início.")
            st.stop()

        if (almoco_inicio and almoco_fim) and almoco_fim <= almoco_inicio:
            st.error("O fim do almoço deve ser maior que o início.")
            st.stop()

        # Monta grade de disponibilidade
        df = _build_grade_disponibilidade(
            dados_agenda=dados,
            prof=profissional or {},
            prof_id=str(prof_id),
            data_ini=dt_ini,
            data_fim=dt_fim,
            jornada_ini=jornada_inicio,
            jornada_fim=jornada_fim,
            slot_min=int(slot_min),
            buffer_min=int(buffer_min),
            almoco_ini=almoco_inicio,
            almoco_fim=almoco_fim,
            considerar_feriados=considerar_feriados,
            capacidade=int(cap_sim),
        )

        if not df.empty:
            # --- KPIs gerais ---
            total_slots = len(df)
            livres = int((df["Situação"] == "Disponível").sum())
            ocupados = total_slots - livres
            r1, r2, r3 = st.columns(3)
            r1.metric("Slots no período", total_slots)
            r2.metric("Disponíveis", livres)
            r3.metric("Ocupados", ocupados)

            # --- Tabela detalhada com cores ---
            def _color_row(row):
                return (["background-color: #ffe5e5"] * len(row)) if row["Situação"] == "Ocupado" else (["background-color: #eaffea"] * len(row))

            st.dataframe(
                df.style.apply(_color_row, axis=1),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            # --- Resumo por dia ---
            st.markdown("#### Resumo por dia")
            resumo = (
                df.groupby("Data", as_index=False)
                  .agg(
                      total_slots=("Situação", "count"),
                      disponiveis=("Situação", lambda s: int((s == "Disponível").sum())),
                      ocupados=("Situação", lambda s: int((s == "Ocupado").sum())),
                  )
            )
            resumo["taxa_ocupacao_%"] = (resumo["ocupados"] / resumo["total_slots"] * 100).round(1)

            st.dataframe(
                resumo,
                use_container_width=True,
                hide_index=True,
            )

            # --- Gráfico de ocupação por dia (barras) ---
            st.markdown("#### Gráfico: Ocupação por dia (%)")
            chart_df = resumo[["Data", "taxa_ocupacao_%"]].set_index("Data")
            st.bar_chart(chart_df, use_container_width=True)

            # --- Exportar CSVs ---
            cexp1, cexp2 = st.columns(2)
            _ini_str = dt_ini.strftime("%Y%m%d")
            _fim_str = dt_fim.strftime("%Y%m%d")

            csv_full = df.to_csv(index=False).encode("utf-8-sig")
            cexp1.download_button(
                "⬇️ Baixar disponibilidade (CSV)",
                data=csv_full,
                file_name=f"disponibilidade_{_ini_str}_{_fim_str}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            csv_resumo = resumo.to_csv(index=False).encode("utf-8-sig")
            cexp2.download_button(
                "⬇️ Baixar resumo por dia (CSV)",
                data=csv_resumo,
                file_name=f"disponibilidade_resumo_{_ini_str}_{_fim_str}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Nenhum horário encontrado para o período configurado.")
