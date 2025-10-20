import streamlit as st
import bcrypt
from datetime import time
from database import listar_registros, inserir_registro, atualizar_registro, excluir_registro
from masklib import masked_text_input, PHONE_BR

TABELA = "ag_profissionais"
FORM_NS = "prof_form_v"


def _header():
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.image("start.png", width=80)
    with col_title:
        st.markdown("<h2>Profissionais</h2>", unsafe_allow_html=True)


def _v() -> int:
    if FORM_NS not in st.session_state:
        st.session_state[FORM_NS] = 0
    return st.session_state[FORM_NS]


def _k(name: str) -> str:
    return f"{FORM_NS}_{name}_{_v()}"


def _dias_semana_to_str(dias: list[str]) -> str:
    """
    Converte lista de labels pt-BR -> string com números ISO (1=Seg ... 7=Dom), separados por vírgula.
    """
    mapa = {"Seg": "1", "Ter": "2", "Qua": "3", "Qui": "4", "Sex": "5", "Sáb": "6", "Dom": "7"}
    return ",".join(mapa[d] for d in dias if d in mapa)


def _dias_semana_from_str(val: str) -> list[str]:
    """
    Converte string "1,2,3" -> lista de labels pt-BR.
    """
    if not val:
        return []
    mapa_rev = {"1": "Seg", "2": "Ter", "3": "Qua", "4": "Qui", "5": "Sex", "6": "Sáb", "7": "Dom"}
    out = []
    for p in str(val).split(","):
        p = p.strip()
        if p in mapa_rev:
            out.append(mapa_rev[p])
    return out


@st.dialog("Editar Profissional")
def modal_editar(item: dict):
    with st.form(f"form_edit_prof_{item['id']}", border=True):
        st.markdown("### Dados básicos")
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome", value=item.get("nome", ""))
            telefone = masked_text_input(
                "Telefone", key=f"tel_prof_edit_{item['id']}", mask=PHONE_BR,
                value=item.get("telefone", ""), in_form=True
            )
        with c2:
            email = st.text_input("Email", value=item.get("email", ""))
            ativo = st.checkbox("Ativo", value=bool(item.get("ativo", True)))
        with c3:
            is_admin = st.checkbox("Administrador", value=bool(item.get("is_admin", False)))
            fuso_horario = st.text_input("Fuso horário", value=item.get("fuso_horario", "America/Sao_Paulo"))

        st.markdown("---")
        st.markdown("### Parâmetros de agenda")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            aceita_sabado = st.checkbox("Aceita Sábado", value=bool(item.get("aceita_sabado", False)))
            aceita_domingo = st.checkbox("Aceita Domingo", value=bool(item.get("aceita_domingo", False)))
        with c5:
            hora_inicio_jornada = st.time_input(
                "Início da jornada", value=_safe_time(item.get("hora_inicio_jornada"), time(8, 0))
            )
            hora_fim_jornada = st.time_input(
                "Fim da jornada", value=_safe_time(item.get("hora_fim_jornada"), time(18, 0))
            )
        with c6:
            almoco_inicio = st.time_input("Almoço (início)", value=_safe_time(item.get("almoco_inicio"), None))
            almoco_fim = st.time_input("Almoço (fim)", value=_safe_time(item.get("almoco_fim"), None))
        with c7:
            slot_minutos = st.number_input("Duração do slot (min)", min_value=5, step=5,
                                           value=int(item.get("slot_minutos") or 30))
            buffer_minutos = st.number_input("Buffer entre atend. (min)", min_value=0, step=5,
                                             value=int(item.get("buffer_minutos") or 0))

        c8, c9, c10 = st.columns(3)
        with c8:
            considerar_feriados = st.checkbox("Considerar feriados (BR)", value=bool(item.get("considerar_feriados", False)))
        with c9:
            capacidade_simultanea = st.number_input("Capacidade simultânea", min_value=1, step=1,
                                                    value=int(item.get("capacidade_simultanea") or 1))
        with c10:
            dias_semana_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            dias_semana = st.multiselect(
                "Dias permitidos (opcional)",
                options=dias_semana_labels,
                default=_dias_semana_from_str(item.get("dias_semana") or "1,2,3,4,5"),
                help="Se preenchido, substitui os flags de Sábado/Domingo."
            )

        st.markdown("---")
        st.markdown("### Notificações")
        c11, c12, c13 = st.columns(3)
        with c11:
            whatsapp_notificar = st.checkbox("Notificar por WhatsApp", value=bool(item.get("whatsapp_notificar", False)))
        with c12:
            whatsapp_numero = st.text_input("Número WhatsApp", value=item.get("whatsapp_numero", ""))
        with c13:
            email_notificar = st.checkbox("Notificar por Email", value=bool(item.get("email_notificar", False)))

        cor_calendario = st.text_input("Cor do calendário (HEX)", value=item.get("cor_calendario", "#28B78D"))
        salvar = st.form_submit_button("Salvar")

    if salvar:
        payload = {
            "nome": nome,
            "email": email,
            "telefone": telefone,
            "ativo": bool(ativo),
            "is_admin": bool(is_admin),
            "fuso_horario": fuso_horario,
            "aceita_sabado": bool(aceita_sabado),
            "aceita_domingo": bool(aceita_domingo),
            "hora_inicio_jornada": str(hora_inicio_jornada) if hora_inicio_jornada else None,
            "hora_fim_jornada": str(hora_fim_jornada) if hora_fim_jornada else None,
            "almoco_inicio": str(almoco_inicio) if almoco_inicio else None,
            "almoco_fim": str(almoco_fim) if almoco_fim else None,
            "slot_minutos": int(slot_minutos),
            "buffer_minutos": int(buffer_minutos),
            "considerar_feriados": bool(considerar_feriados),
            "capacidade_simultanea": int(capacidade_simultanea),
            "dias_semana": _dias_semana_to_str(dias_semana) if dias_semana else None,
            "whatsapp_notificar": bool(whatsapp_notificar),
            "whatsapp_numero": whatsapp_numero,
            "email_notificar": bool(email_notificar),
            "cor_calendario": cor_calendario,
        }
        atualizar_registro(TABELA, item["id"], payload)
        st.success("Atualizado!")
        st.rerun()


def _safe_time(val, default: time | None) -> time | None:
    """
    Converte 'HH:MM'/'HH:MM:SS' -> time; retorna default se None/''.
    """
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


def render():
    u = st.session_state.get("user", {})
    if not u.get("is_admin"):
        _header()
        st.error("Acesso restrito ao administrador.")
        return

    _header()

    with st.form("form_prof", border=True):
        st.markdown("### Novo profissional")
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome *", key=_k("nome"))
            email = st.text_input("Email *", key=_k("email"))
        with c2:
            telefone = masked_text_input("Telefone", key=_k("tel"), mask=PHONE_BR, value="", in_form=True)
            is_admin = st.checkbox("Administrador", value=False, key=_k("admin"))
        with c3:
            ativo = st.checkbox("Ativo", value=True, key=_k("ativo"))
            senha = st.text_input("Senha *", type="password", key=_k("senha"))

        st.markdown("---")
        st.markdown("### Parâmetros de agenda (defaults)")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            fuso_horario = st.text_input("Fuso horário", value="America/Sao_Paulo", key=_k("tz"))
            aceita_sabado = st.checkbox("Aceita Sábado", value=False, key=_k("sab"))
            aceita_domingo = st.checkbox("Aceita Domingo", value=False, key=_k("dom"))
        with c5:
            hora_inicio_jornada = st.time_input("Início da jornada", value=time(8, 0), key=_k("hinij"))
            hora_fim_jornada = st.time_input("Fim da jornada", value=time(18, 0), key=_k("hfimj"))
        with c6:
            almoco_inicio = st.time_input("Almoço (início)", value=None, key=_k("almi"))
            almoco_fim = st.time_input("Almoço (fim)", value=None, key=_k("almf"))
        with c7:
            slot_minutos = st.number_input("Duração do slot (min)", min_value=5, step=5, value=30, key=_k("slot"))
            buffer_minutos = st.number_input("Buffer entre atend. (min)", min_value=0, step=5, value=0, key=_k("buf"))

        c8, c9, c10 = st.columns(3)
        with c8:
            considerar_feriados = st.checkbox("Considerar feriados (BR)", value=False, key=_k("fer"))
        with c9:
            capacidade_simultanea = st.number_input("Capacidade simultânea", min_value=1, step=1, value=1, key=_k("cap"))
        with c10:
            dias_semana = st.multiselect(
                "Dias permitidos (opcional)",
                options=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
                default=["Seg", "Ter", "Qua", "Qui", "Sex"], key=_k("dias")
            )

        st.markdown("---")
        st.markdown("### Notificações")
        c11, c12, c13 = st.columns(3)
        with c11:
            whatsapp_notificar = st.checkbox("Notificar por WhatsApp", value=False, key=_k("wn"))
        with c12:
            whatsapp_numero = st.text_input("Número WhatsApp", value="", key=_k("wnum"))
        with c13:
            email_notificar = st.checkbox("Notificar por Email", value=False, key=_k("en"))

        cor_calendario = st.text_input("Cor do calendário (HEX)", value="#28B78D", key=_k("cor"))
        enviar = st.form_submit_button("Incluir", type="primary")

    if enviar:
        senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        inserir_registro(TABELA, {
            "user_id": u.get("user_id") or u.get("id"),
            "is_admin": bool(is_admin),
            "nome": nome,
            "email": email,
            "telefone": telefone,
            "ativo": bool(ativo),
            "senha_hash": senha_hash,
            # parâmetros
            "fuso_horario": fuso_horario,
            "aceita_sabado": bool(aceita_sabado),
            "aceita_domingo": bool(aceita_domingo),
            "hora_inicio_jornada": str(hora_inicio_jornada),
            "hora_fim_jornada": str(hora_fim_jornada),
            "almoco_inicio": str(almoco_inicio) if almoco_inicio else None,
            "almoco_fim": str(almoco_fim) if almoco_fim else None,
            "slot_minutos": int(slot_minutos),
            "buffer_minutos": int(buffer_minutos),
            "considerar_feriados": bool(considerar_feriados),
            "capacidade_simultanea": int(capacidade_simultanea),
            "dias_semana": _dias_semana_to_str(dias_semana) if dias_semana else None,
            "whatsapp_notificar": bool(whatsapp_notificar),
            "whatsapp_numero": whatsapp_numero,
            "email_notificar": bool(email_notificar),
            "cor_calendario": cor_calendario,
        })
        st.success("Profissional incluído!")
        st.session_state[FORM_NS] = _v() + 1
        st.rerun()

    st.divider()
    st.subheader("Lista de profissionais")

    itens = listar_registros(TABELA)
    if not itens:
        st.info("Nenhum profissional cadastrado.")
        return

    for it in itens:
        col_info, col_actions = st.columns([6, 4])
        with col_info:
            resumo_param = (
                f"Jornada {it.get('hora_inicio_jornada','08:00')}–{it.get('hora_fim_jornada','18:00')} • "
                f"Slot {it.get('slot_minutos',30)}' • Buffer {it.get('buffer_minutos',0)}' • "
                f"Cap {it.get('capacidade_simultanea',1)} • "
                f"Dias {it.get('dias_semana','1,2,3,4,5')}"
            )
            st.markdown(
                f"**{it.get('nome','')}**  \n"
                f"{it.get('email','')}  \n"
                f"{it.get('telefone','')}  \n"
                f"{'Admin' if it.get('is_admin') else 'Usuário'} • "
                f"{'Ativo' if it.get('ativo') else 'Inativo'}  \n"
                f"<span style='font-size:12px;color:#666'>{resumo_param}</span>",
                unsafe_allow_html=True
            )
        with col_actions:
            b1, b2 = st.columns([1, 1])
            edit = b1.button("Alterar", key=f"prof_edit_{it['id']}")
            delete = b2.button("Excluir", key=f"prof_del_{it['id']}")

        if edit:
            modal_editar(it)
        if delete:
            confirm_key = f"confirm_prof_{it['id']}"
            if st.session_state.get(confirm_key) is not True:
                st.session_state[confirm_key] = True
                st.warning("Clique novamente para confirmar.")
            else:
                excluir_registro(TABELA, it["id"])
                st.success("Excluído!")
                st.rerun()
