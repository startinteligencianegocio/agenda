# dashboard.py
import streamlit as st
from datetime import date, timedelta
from database import supabase  # usa o SDK já configurado no seu database.py

TITLE = "Agenda Profissional"

def _header():
    col_logo, col_title = st.columns([1,6])
    with col_logo:
        st.image("start.png", width=160)
    with col_title:
        st.markdown(f"<h2 style='margin:0'>{TITLE}</h2>", unsafe_allow_html=True)

def _inject_css():
    # tenta carregar style.css global (se existir) + garante CSS mínimo dos KPIs
    css = ""
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            css = f.read()
    except Exception:
        pass

    extra = """
    /* KPI cards */
    .kpi-row { margin-top: .5rem; margin-bottom: 1rem; }
    .kpi-card{
        background: linear-gradient(135deg, #28B78D 0%, #243743 60%, #A1A9AE 100%);
        border-radius: 16px;
        padding: 18px 20px;
        color: #fff;
        box-shadow: 0 4px 16px rgba(0,0,0,.18);
        border: 1px solid rgba(255,255,255,.08);
        min-height: 96px;
        display:flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-value{
        font-size: 32px;
        line-height: 1;
        font-weight: 800;
        margin-bottom: 6px;
        text-shadow: 0 1px 2px rgba(0,0,0,.35);
    }
    .kpi-label{
        font-size: 14px;
        opacity: .95;
        font-weight: 500;
        letter-spacing: .2px;
        text-shadow: 0 1px 1px rgba(0,0,0,.25);
    }
    """
    st.markdown(f"<style>{css}\n{extra}</style>", unsafe_allow_html=True)

def _count_exact(q):
    """
    Retorna count de uma consulta Supabase com select(..., count='exact').
    Compatível com versões que expõem .count ou que só retornam data.
    """
    try:
        resp = q.execute()
        if hasattr(resp, "count") and resp.count is not None:
            return int(resp.count)
        if hasattr(resp, "data") and resp.data is not None:
            return len(resp.data)
        return 0
    except Exception as e:
        st.warning(f"Falha ao contar: {e}")
        return 0

def _contagens_basicas(prof_id: str):
    """
    a) Atendimentos do dia
    b) Atendimentos do mês anterior (inteiro)
    c) Atendimentos no mês atual até ontem
    d) Total do mês (a + c)
    """
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    primeiro_mes = hoje.replace(day=1)

    # mês anterior (intervalo completo)
    ultimo_mes_anterior = primeiro_mes - timedelta(days=1)
    primeiro_mes_anterior = ultimo_mes_anterior.replace(day=1)

    # a) dia
    q_dia = _count_exact(
        supabase.table("ag_agenda")
        .select("id", count="exact")
        .eq("profissional_id", prof_id)
        .eq("data_atendimento", str(hoje))
    )

    # b) mês anterior
    q_mes_ant = _count_exact(
        supabase.table("ag_agenda")
        .select("id", count="exact")
        .eq("profissional_id", prof_id)
        .gte("data_atendimento", str(primeiro_mes_anterior))
        .lte("data_atendimento", str(ultimo_mes_anterior))
    )

    # c) mês atual até ontem
    if hoje.day == 1:
        q_mes_ate_ontem = 0
    else:
        q_mes_ate_ontem = _count_exact(
            supabase.table("ag_agenda")
            .select("id", count="exact")
            .eq("profissional_id", prof_id)
            .gte("data_atendimento", str(primeiro_mes))
            .lte("data_atendimento", str(ontem))
        )

    total_mes = q_dia + q_mes_ate_ontem
    return q_dia, q_mes_ant, q_mes_ate_ontem, total_mes

def _contagens_status(prof_id: str):
    """
    Contagens por status (linha 2):
    - Confirmados (geral)
    - Pendentes (geral)
    - Cancelados (geral)
    - Concluídos (hoje)  <-- NOVO
    """
    hoje = date.today()

    confirmados = _count_exact(
        supabase.table("ag_agenda")
        .select("id", count="exact")
        .eq("profissional_id", prof_id)
        .eq("status", "Confirmado")
    )
    pendentes = _count_exact(
        supabase.table("ag_agenda")
        .select("id", count="exact")
        .eq("profissional_id", prof_id)
        .eq("status", "Pendente")
    )
    cancelados = _count_exact(
        supabase.table("ag_agenda")
        .select("id", count="exact")
        .eq("profissional_id", prof_id)
        .eq("status", "Cancelado")
    )
    concluidos_hoje = _count_exact(
        supabase.table("ag_agenda")
        .select("id", count="exact")
        .eq("profissional_id", prof_id)
        .eq("status", "Concluído")
        .eq("data_atendimento", str(hoje))
    )
    return confirmados, pendentes, cancelados, concluidos_hoje

def _kpi_card(label: str, value: int):
    html = f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render():
    _inject_css()
    _header()

    user = st.session_state.get("user", {})
    prof_id = user.get("id")
    if not prof_id:
        st.error("Profissional não identificado na sessão.")
        return

    # Linha 1 — KPIs básicos
    a, b, c, d = _contagens_basicas(prof_id)
    st.markdown('<div class="kpi-row"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1: _kpi_card("Atendimentos do dia", a)
    with c2: _kpi_card("Atendimentos mês anterior", b)
    with c3: _kpi_card("Atendimentos no mês (até ontem)", c)
    with c4: _kpi_card("Total no mês (a + c)", d)

    # Linha 2 — KPIs por status (Confirmados, Pendentes, Cancelados, Concluídos hoje)
    conf, pend, canc, concl_hoje = _contagens_status(prof_id)
    st.markdown('<div class="kpi-row"></div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4, gap="small")
    with s1: _kpi_card("Agendamentos Confirmados", conf)
    with s2: _kpi_card("Agendamentos Pendentes", pend)
    with s3: _kpi_card("Agendamentos Cancelados", canc)
    with s4: _kpi_card("Concluídos (hoje)", concl_hoje)

    #st.divider()
    #st.caption("KPIs com gradiente #28B78D → #243743 → #A1A9AE. Ajuste em style.css se quiser novas cores.")
