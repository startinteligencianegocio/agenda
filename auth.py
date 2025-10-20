import bcrypt
from datetime import date
from typing import Optional, Dict
from database import listar_registros

def validar_login(email: str, senha: str) -> Optional[Dict]:
    usuarios = listar_registros("ag_profissionais", {"email": email})
    if not usuarios:
        return None
    u = usuarios[0]

    senha_hash = u.get("senha_hash") or u.get("SENHA_HASH")
    if not senha_hash:
        return None

    try:
        ok = bcrypt.checkpw(senha.encode("utf-8"), (senha_hash.encode("utf-8") if isinstance(senha_hash, str) else senha_hash))
    except Exception:
        return None

    if not ok:
        return None

    if not u.get("ativo", True):
        return None

    hoje = date.today()

    def to_date(x):
        if not x:
            return None
        if isinstance(x, date):
            return x
        try:
            return date.fromisoformat(str(x))
        except Exception:
            return None

    dl = to_date(u.get("data_licenca"))
    dt = to_date(u.get("data_teste"))

    licenca_ok = (dl and hoje <= dl) or (dt and hoje <= dt)
    if not licenca_ok and not u.get("is_admin", False):
        return None

    return u
