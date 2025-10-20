
from database import listar_registros
from datetime import datetime, timedelta
from phone_utils import sanitize_br_phone

def notificar_agendamentos(profissional_id: str, profissional_nome: str):
    hoje = datetime.today().date()
    amanha = hoje + timedelta(days=1)
    ags = listar_registros("ag_agenda", {"profissional_id": profissional_id})
    links = []
    for ag in ags:
        if str(ag["data_atendimento"]) == str(amanha):
            numero = sanitize_br_phone(ag.get("cliente_telefone", ""))
            msg = f"Aqui é {profissional_nome}, você tem um horário agendado no dia {ag['data_atendimento']} às {ag['hora_inicio']} hrs. Digite 1 para Confirmar e 2 Cancelar"
            link = f"https://wa.me/{numero}?text={msg.replace(' ', '%20')}"
            links.append({"cliente": ag.get("cliente_nome"), "link": link})
    return links
