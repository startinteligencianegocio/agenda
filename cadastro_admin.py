# cadastro_admin.py
import streamlit as st
import bcrypt
from utils.database import get_connection

def cadastrar_admin():
    st.title("Cadastro do Administrador Inicial")

    nome = st.text_input("Nome completo")
    email = st.text_input("E-mail")
    telefone = st.text_input("Telefone")
    senha = st.text_input("Senha", type="password")
    confirmar = st.text_input("Confirmar Senha", type="password")

    if st.button("Cadastrar Administrador"):
        if not nome or not email or not senha:
            st.error("⚠️ Preencha todos os campos obrigatórios.")
            return

        if senha != confirmar:
            st.error("⚠️ As senhas não conferem.")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Verificar se já existe admin cadastrado
            cur.execute("SELECT COUNT(*) FROM ag_profissionais WHERE is_admin = TRUE;")
            if cur.fetchone()[0] > 0:
                st.warning("⚠️ Já existe um administrador cadastrado.")
                cur.close()
                conn.close()
                return

            # Gerar hash da senha
            senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            # Inserir administrador
            cur.execute("""
                INSERT INTO ag_profissionais (nome, email, telefone, senha_hash, is_admin, ativo)
                VALUES (%s, %s, %s, %s, TRUE, TRUE)
            """, (nome, email, telefone, senha_hash))

            conn.commit()
            cur.close()
            conn.close()

            st.success("✅ Administrador cadastrado com sucesso!")

        except Exception as e:
            st.error(f"❌ Erro ao cadastrar administrador: {e}")
