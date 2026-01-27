import streamlit as st
import bcrypt
from services import supabase
import time

def hash_password(password):
    """Transforma '123456' em uma sopa de letrinhas segura"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    """Confere se a senha bate"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def tela_login():
    st.title("🔐 Acesso ao Tradutor Jurídico")
    
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
    
    # --- ABA DE LOGIN ---
    with tab1:
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            if not email or not senha:
                st.warning("Preencha tudo!")
                return None
            
            try:
                # Busca usuário pelo email
                response = supabase.table("profiles").select("*").eq("email", email).execute()
                data = response.data
                
                if data:
                    user = data[0]
                    # Verifica a senha
                    if user.get('password_hash') and check_password(senha, user['password_hash']):
                        st.success("Logado com sucesso!")
                        time.sleep(1)
                        return user['id'] # Retorna o ID Real
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Email não encontrado. Crie uma conta.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
    
    # --- ABA DE CADASTRO ---
    with tab2:
        new_email = st.text_input("Seu melhor Email")
        new_senha = st.text_input("Crie uma Senha", type="password", key="new_pass")
        confirm_senha = st.text_input("Confirme a Senha", type="password")
        
        if st.button("Cadastrar Gratuitamente"):
            if new_senha != confirm_senha:
                st.error("Senhas não batem!")
            elif len(new_senha) < 6:
                st.warning("Senha muito curta (min 6).")
            else:
                try:
                    # Verifica se email já existe
                    check = supabase.table("profiles").select("id").eq("email", new_email).execute()
                    if check.data:
                        st.error("Esse email já tem conta.")
                    else:
                        # Cria novo usuário
                        user_id = new_email  # Simplificação: Usando email como ID (ou gere UUID)
                        hashed = hash_password(new_senha)
                        
                        supabase.table("profiles").insert({
                            "id": user_id,
                            "email": new_email,
                            "password_hash": hashed,
                            "plan_status": "free",
                            "credits_balance": 3
                        }).execute()
                        
                        st.success("Conta criada! Vá para a aba 'Entrar'.")
                        st.balloons()
                except Exception as e:
                    st.error(f"Erro ao criar conta: {e}")
    
    return None

def logout():
    st.session_state.user_id = None
    st.rerun()