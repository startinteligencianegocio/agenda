# dashboard.py
import streamlit as st
import pandas as pd
from datetime import date
from calendar import month_name
from database import listar_registros

TAB_AGENDA = "ag_agenda"
TAB_PROFISSIONAIS = "ag_profissionais"
TAB_TIPOS = "ag_tipos_servicos"

# -----------------------------
# Utils
# -----------------------------
def _try_numeric(s):
    try:
        return pd.to_numeric(s, errors="coerce")
    except Exception:
        return pd.Series([None] * len(s))

def _fmt_brl(v):
    if v is None:
        v = 0.0
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _load_df(tabela: str) -> pd.DataFrame:
    try:
        rows = listar_registros(tabela, {})
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        st.warning(f"Não foi possível carregar registros de {tabela}.")
        if st.session_state.get("DEBUG"): st.exception(e)
        return pd.DataFrame()

# -----------------------------
# Normalização
# -----------------------------
def _load_agenda_norm() -> pd.DataFrame:
    df = _load_df(TAB_AGENDA)
    if df.empty:
        return df

    data_col = next((c for c in df.columns if c.lower() in ("data","data_agenda","dt_agenda","dia")), None)
    hora_col = next((c for c in df.columns if "hora" in c.lower() and ("ini" in c.lower() or "início" in c.lower() or "inicio" in c.lower())), None)
    status_col = next((c for c in df.columns if c.lower() == "status"), None)
    valor_col = next((c for c in df.columns if any(x in c.lower() for x in ("valor","preco","preço","total"))), None)
    prof_id_col = next((c for c in df.columns if "prof" in c.lower() and "id" in c.lower()), None)
    tipo_id_col = next((c for c in df.columns if "tipo" in c.lower() and "id" in c.lower()), None)

    df["__data__"] = pd.to_datetime(df[data_col], errors="coerce").dt.date if data_col else pd.NaT
    df["__hora__"] = pd.to_datetime(df[hora_col], errors="coerce").dt.time if hora_col else None
    df["__status__"] = df[status_col].astype(str).str.upper() if status_col else "PENDENTE"
    df["__valor__"] = _try_numeric(df[valor_col]).fillna(0.0) if valor_col else 0.0

    # Join profissionais
    dfp = _load_df(TAB_PROFISSIONAIS)
    if not dfp.empty and prof_id_col:
        prof_id = next((c for c in dfp.columns if c.lower() in ("id","prof_id","cod_profissional","codigo")), None)
        prof_nome = next((c for c in dfp.columns if c.lower() in ("nome","nome_prof","razao_social","profissional")), None)
        if prof_id and prof_nome:
            df = df.merge(dfp[[prof_id, prof_nome]], left_on=prof_id_col, right_on=prof_id, how="left")
            df.rename(columns={prof_nome: "__prof__"}, inplace=True)
        else:
            df["__prof__"] = None
    else:
        df["__prof__"] = None

    # Join tipos
    dft = _load_df(TAB_TIPOS)
    if not dft.empty and tipo_id_col:
        tipo_id = next((c for c in dft.columns if c.lower() in ("id","tipo_id","cod_tipo","codigo")), None)
        tipo_nome = next((c for c in dft.columns if c.lower() in ("nome","descricao","servico","título","titulo")), None)
        if tipo_id and tipo_nome:
            df = df.merge(dft[[tipo_id, tipo_nome]], left_on=tipo_id_col, right_on=tipo_id, how="left")
            df.rename(columns={tipo_nome: "__servico__"}, inplace=True)
        else:
            df["__servico__"] = None
    else:
        df["__servico__"] = None

    df["__ano__"] = [d.year if isinstance(d, date) else None for d in df["__data__"]]
    df["__mes__"] = [d.month if isinstance(d, date) else None for d in df["__data__"]]
    return df

# -----------------------------
# Filtros
# -----------------------------
def _filtros_periodo(df: pd.DataFrame):
    hoje = date.today()
    anos = sorted([int(a) for a in df["__ano__"].dropna().unique().tolist()], reverse=True) if not df.empty else [hoje.year]
    if not anos: anos = [hoje.year]
    ano_sel = st.selectbox("Ano", anos, index=0)

    meses = list(range(1, 12 + 1))
    labels = [f"{m:02d} - {month_name[m].capitalize()}" for m in meses]
    idx_mes = (hoje.month - 1) if ano_sel == hoje.year else 0
    mes_sel = st.selectbox("Mês", meses, format_func=lambda m: labels[m-1], index=idx_mes)
    return ano_sel, mes_sel

def _aplicar_periodo(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    if df.empty:
        return df
    return df[(df["__ano__"] == ano) & (df["__mes__"] == mes)].copy()

# -----------------------------
# KPIs (forçados 4 colunas lado-a-lado)
# -----------------------------
def _kpi_html(label: str, value: str) -> str:
    return f"""
    <div class='kpi-card'>
      <div class='kpi-value'>{value}</div>
      <div class='kpi-label'>{label}</div>
    </div>
    """

def _area_kpis(df_mes: pd.DataFrame, ano: int, mes: int):
    ref = f"{ano}/{str(mes).zfill(2)}"
    total = len(df_mes)
    confirmados = int((df_mes["__status__"] == "CONFIRMADO").sum()) if not df_mes.empty else 0
    cancelados = int((df_mes["__status__"] == "CANCELADO").sum()) if not df_mes.empty else 0
    soma_confirmados = float(df_mes.loc[df_mes["__status__"] == "CONFIRMADO", "__valor__"].sum()) if not df_mes.empty else 0.0
    ticket_medio = (soma_confirmados / confirmados) if confirmados > 0 else 0.0

    st.markdown("### 🏷️ Resumo do mês")
    c1, c2, c3, c4 = st.columns(4)   # <-- garante uma linha com 4 colunas
    with c1:
        st.markdown(_kpi_html("Atendimentos", f"{total} · {ref}"), unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi_html("Confirmados", f"{confirmados} · {ref}"), unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi_html("Cancelados", f"{cancelados} · {ref}"), unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi_html("Ticket Médio", f"{_fmt_brl(ticket_medio)} · {ref}"), unsafe_allow_html=True)

# -----------------------------
# Gráficos/Tabelas
# -----------------------------
def _evolucao_diaria(df_mes: pd.DataFrame):
    st.markdown("### 📈 Evolução diária (quantidade)")
    if df_mes.empty:
        st.caption("Sem dados no período selecionado.")
        return
    serie = df_mes.groupby("__data__")["__status__"].count().rename("Qtde").reset_index().sort_values("__data__").set_index("__data__")
    st.line_chart(serie)

def _distribuicao_status(df_mes: pd.DataFrame):
    st.markdown("### 📌 Distribuição por status")
    if df_mes.empty:
        st.caption("Sem dados no período selecionado.")
        return
    dist = df_mes["__status__"].value_counts().rename_axis("Status").reset_index(name="Qtde")
    st.dataframe(dist, hide_index=True, use_container_width=True)

def _top_profissionais(df_mes: pd.DataFrame, topn=5):
    st.markdown("### 🧑‍🔧 Top Profissionais (confirmados)")
    if df_mes.empty or "__prof__" not in df_mes.columns:
        st.caption("Sem dados para profissionais.")
        return
    base = df_mes[df_mes["__status__"] == "CONFIRMADO"]
    if base.empty:
        st.caption("Sem confirmados no período.")
        return
    top = base["__prof__"].fillna("(Sem nome)").value_counts().head(topn).rename_axis("Profissional").reset_index(name="Qtde")
    st.bar_chart(top.set_index("Profissional"))

def _top_servicos(df_mes: pd.DataFrame, topn=5):
    st.markdown("### 💈 Top Serviços (confirmados)")
    if df_mes.empty or "__servico__" not in df_mes.columns:
        st.caption("Sem dados para serviços.")
        return
    base = df_mes[df_mes["__status__"] == "CONFIRMADO"]
    if base.empty:
        st.caption("Sem confirmados no período.")
        return
    top = base["__servico__"].fillna("(Sem nome)").value_counts().head(topn).rename_axis("Serviço").reset_index(name="Qtde")
    st.bar_chart(top.set_index("Serviço"))

def _tabela_detalhe(df_mes: pd.DataFrame):
    st.markdown("### 📋 Detalhamento do mês")
    if df_mes.empty:
        st.caption("Sem dados no período selecionado.")
        return
    show = pd.DataFrame({
        "Data": pd.to_datetime(df_mes["__data__"]).dt.strftime("%d/%m/%Y"),
        "Hora": df_mes["__hora__"].astype(str),
        "Profissional": df_mes.get("__prof__", pd.Series([""] * len(df_mes))),
        "Serviço": df_mes.get("__servico__", pd.Series([""] * len(df_mes))),
        "Status": df_mes["__status__"],
        "Valor": df_mes["__valor__"].map(_fmt_brl),
    })
    st.dataframe(show, hide_index=True, use_container_width=True)
    st.download_button(
        "Baixar CSV do mês",
        data=show.to_csv(index=False).encode("utf-8"),
        file_name="dashboard_agenda_mes.csv",
        mime="text/csv",
        use_container_width=True,
    )

# -----------------------------
# Page
# -----------------------------
def render():
    st.markdown("## 📊 Dashboard")
    df = _load_agenda_norm()
    if df.empty:
        st.info("Sem dados de agenda.")
        return

    # Filtros — uma única chamada
    col1, col2 = st.columns(2)
    with col1:
        ano, mes = _filtros_periodo(df)
    with col2:
        st.empty()  # espaço de layout

    df_mes = _aplicar_periodo(df, ano, mes)

    _area_kpis(df_mes, ano, mes)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1: _evolucao_diaria(df_mes)
    with c2: _distribuicao_status(df_mes)

    c3, c4 = st.columns(2)
    with c3: _top_profissionais(df_mes)
    with c4: _top_servicos(df_mes)

    st.markdown("---")
    _tabela_detalhe(df_mes)
