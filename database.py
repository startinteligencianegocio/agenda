import os
import psycopg2
from supabase import create_client
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("DEBUG: SUPABASE_URL =", SUPABASE_URL)
print("DEBUG: SUPABASE_KEY =", (SUPABASE_KEY[:10] + " ...") if SUPABASE_KEY else None)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL ou SUPABASE_KEY não encontrados no .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def _has_db_env() -> bool:
    return all([
        os.getenv("SUPABASE_DB_HOST"),
        os.getenv("SUPABASE_DB_NAME"),
        os.getenv("SUPABASE_DB_USER"),
        os.getenv("SUPABASE_DB_PASS"),
    ])

def get_connection():
    if not _has_db_env():
        raise RuntimeError(
            "Variáveis de conexão PostgreSQL ausentes. Defina SUPABASE_DB_HOST, SUPABASE_DB_NAME, "
            "SUPABASE_DB_USER, SUPABASE_DB_PASS e SUPABASE_DB_PORT no .env.\n"
            "Ou use apenas o SDK do Supabase (sem executar_sql)."
        )
    conn = psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        dbname=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASS"),
        port=os.getenv("SUPABASE_DB_PORT", "5432"),
        sslmode=os.getenv("SUPABASE_DB_SSLMODE", "require"),
    )
    return conn

def listar_registros(tabela: str, filtros: Optional[Dict[str, Any]] = None, order: Optional[str] = None) -> List[Dict[str, Any]]:
    q = supabase.table(tabela).select("*")
    if filtros:
        for k, v in filtros.items():
            if v is None:
                continue
            q = q.eq(k, v)
    if order:
        q = q.order(order)
    res = q.execute()
    return res.data or []

def inserir_registro(tabela: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    res = supabase.table(tabela).insert(payload).execute()
    if res.data:
        return res.data[0]
    raise RuntimeError(f"Falha ao inserir em {tabela}")

def atualizar_registro(tabela: str, id_value: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    res = supabase.table(tabela).update(payload).eq('id', id_value).execute()
    if res.data:
        return res.data[0]
    raise RuntimeError(f"Falha ao atualizar {tabela} id={id_value}")

def excluir_registro(tabela: str, id_value: str) -> None:
    supabase.table(tabela).delete().eq('id', id_value).execute()

def executar_sql(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]

def contar(tabela: str, filtros: Optional[Dict[str, Any]] = None) -> int:
    q = supabase.table(tabela).select("id", count="exact")
    if filtros:
        for k, v in filtros.items():
            if v is None:
                continue
            q = q.eq(k, v)
    res = q.execute()
    if getattr(res, "count", None) is not None:
        return int(res.count)
    return len(res.data or [])
