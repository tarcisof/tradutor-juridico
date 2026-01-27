import streamlit as st
from google import genai
from urllib.parse import quote
from dotenv import load_dotenv
import os
import time 
from services import SaaSLogger, supabase
from auth import tela_login, logout

# Carrega variáveis de ambiente
load_dotenv()

# =============================
# 1. Configuração Inicial e CSS
# =============================
st.set_page_config(
    page_title="TraduzJur",
    page_icon="⚖️",
    layout="centered"
)

st.markdown("""
<style>
/* -------------------- GERAL -------------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

.stApp {
    background-color: #FFFFFF;
    font-family: 'Inter', sans-serif;
}

/* -------------------- TÍTULOS E TEXTOS -------------------- */
h1 {
    color: #000000 !important;
    font-weight: 800;
    letter-spacing: -1px;
}

p, label, .stMarkdown {
    color: #333333 !important;
    font-weight: 500;
}

/* -------------------- SIDEBAR -------------------- */
section[data-testid="stSidebar"] {
    background-color: #F8F9FA;
    border-right: 1px solid #E5E7EB;
}

/* -------------------- BOTÕES (CORRIGIDO) -------------------- */
/* Força a cor do texto para BRANCO em todos os estados */
div.stButton > button {
    background-color: #2723ed !important;
    color: #FFFFFF !important; 
    border: none;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-weight: 700;
    transition: all 0.2s;
    box-shadow: 0 4px 6px rgba(39, 35, 237, 0.2);
}

/* Garante que o texto dentro do botão também fique branco */
div.stButton > button p {
    color: #FFFFFF !important;
}

div.stButton > button:hover {
    background-color: #1a16c4 !important; /* Azul mais escuro no hover */
    color: #FFFFFF !important;
    box-shadow: 0 6px 12px rgba(39, 35, 237, 0.4);
    transform: translateY(-1px);
}

div.stButton > button:active {
    background-color: #1a16c4 !important;
    color: #FFFFFF !important;
    transform: translateY(0);
}

/* Botão Secundário (Sair) - Opcional, para diferenciar */
div[data-testid="stVerticalBlock"] > div > div[data-testid="stButton"] > button:has(div:contains("Sair")) {
    background-color: #EF4444 !important; /* Vermelho para sair */
}

/* -------------------- INPUTS & SELETORES -------------------- */
.stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
}

/* Foco com a cor azul */
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #2723ed !important;
    box-shadow: 0 0 0 2px rgba(39, 35, 237, 0.2) !important;
}

/* Radio Buttons (Seleção de Tom e Tipo) */
div[role="radiogroup"] label {
    background-color: #F1F5F9;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #E2E8F0;
    margin-right: 8px;
    cursor: pointer;
    transition: all 0.2s;
}

/* Quando passa o mouse no seletor */
div[role="radiogroup"] label:hover {
    border-color: #2723ed;
    color: #2723ed !important;
}

/* O item selecionado (bolinha) */
div[role="radiogroup"] [data-baseweb="radio"] {
    accent-color: #2723ed !important;
}

/* -------------------- WHATSAPP BUTTON -------------------- */
.whatsapp-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #25D366; 
    color: white !important;
    font-weight: 800;
    padding: 12px;
    border-radius: 8px;
    text-decoration: none;
    margin-top: 20px;
    transition: transform 0.2s;
}
.whatsapp-btn:hover {
    transform: scale(1.02);
}

</style>
""", unsafe_allow_html=True)


# =============================
# 2. Autenticação (Porteiro)
# =============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    usuario_autenticado = tela_login() # Chama tela de login se não tiver user
    if usuario_autenticado:
        st.session_state.user_id = usuario_autenticado
        st.rerun()
    st.stop() 

# =============================
# 3. Lógica do App
# =============================

# Callbacks e Estado
def limpar_tudo():
    st.session_state.mensagem_final = ""
    st.session_state.texto_processo = ""

if "mensagem_final" not in st.session_state:
    st.session_state.mensagem_final = ""

if "texto_processo" not in st.session_state:
    st.session_state.texto_processo = ""

# Interface Principal
st.markdown("<h1>TraduzJur</h1>", unsafe_allow_html=True)
st.markdown("<p class='caption-text'>Converta juridiquês em mensagens claras e envie para o cliente.</p>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    USER_ID_ATUAL = st.session_state.user_id

    # Busca dados no Supabase
    try:
        dados = supabase.table("profiles").select("credits_balance, plan_status").eq("id", USER_ID_ATUAL).execute()
        if dados.data:
            info = dados.data[0]
        else:
            info = {"plan_status": "free", "credits_balance": 0} 
    except:
        info = {"plan_status": "erro", "credits_balance": 0}

    with st.expander("👤 Minha Conta", expanded=True):
        st.write(f"**Email:** {USER_ID_ATUAL}")
        
        status_color = "green" if info['plan_status'] != 'free' else "orange"
        st.markdown(f"**Plano:** :{status_color}[{info['plan_status'].upper()}]")
        
        if info["plan_status"] == "free":
            st.write(f"**Créditos:** {info['credits_balance']}")

    if info["plan_status"] == "free":
        
        stripe_link_base = os.getenv("LINK_STRIPE")    
        link_final = f"{stripe_link_base}?client_reference_id={USER_ID_ATUAL}"

        st.markdown(f"""
        <a href="{link_final}" target="_blank" style="text-decoration:none;">
            <div style="
                background: linear-gradient(180deg, #3B82F6 0%, #2563EB 100%);
                color: white;
                text-align: center;
                padding: 10px;
                border-radius: 8px;
                font-weight: bold;
                box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
                transition: transform 0.2s;
                cursor: pointer;
                margin-bottom: 20px;
            ">
                ⭐ VIRAR PRO
            </div>
        </a>
        """, unsafe_allow_html=True)

    st.divider()
    st.header("Configuração")

    tipo_andamento = st.selectbox(
        "Tipo de documento:",
        ["Despacho", "Decisão", "Intimação / Prazo", "Juntada", "Sentença"]
    )

    st.write("Tom da mensagem:")
    tom_de_voz = st.radio(
        "Tom da mensagem:",
        ["Empático", "Formal", "Direto"],
        horizontal=True,
        label_visibility="collapsed"
    )

    nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Sr. João")

    st.divider()
    
    if st.button("🚪 Sair", key="btn_logout_sidebar"):
        logout()

# --- ÁREA CENTRAL ---
texto_input = st.text_area(
    "Cole o texto do processo aqui:",
    height=200,
    key="texto_processo",
    placeholder="Ex: Certifico e dou fé que, em cumprimento ao r. despacho de fls..."
)

# Botão Principal de Ação
if st.button("✨ GERAR EXPLICAÇÃO", type="primary"):
    
    # Validação
    if not st.session_state.texto_processo.strip():
        st.warning("⚠️ Por favor, cole o texto do processo primeiro.")
        
    else:
        # Checagem de Saldo
        if not SaaSLogger.check_can_generate(USER_ID_ATUAL):
             st.error("🔒 Seus créditos acabaram! Faça o upgrade para continuar.")
             
        else:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                st.error("Erro interno: API Key não configurada.")
            else:
                try:
                    start_time = time.time()
                    client = genai.Client(api_key=api_key)
                    MODEL_NAME = "gemini-2.5-flash" 
                    
                    prompt = f"""
                    Você é um advogado experiente traduzindo um andamento processual
                    para um cliente leigo no WhatsApp.
                    
                    DADOS:
                    - Tipo: {tipo_andamento}
                    - Cliente: {nome_cliente if nome_cliente else 'Cliente'}
                    - Tom: {tom_de_voz}
                    - Texto Original: \"\"\"{st.session_state.texto_processo}\"\"\"

                    REGRAS DE OURO:
                    1. Traduza termos técnicos (ex: 'conclusos', 'certifico').
                    2. Se tiver PRAZO, coloque em negrito com apenas uma estrela (ex: *15 dias*).
                    3. Seja tranquilizador, mas realista (não garanta ganho de causa).
                    4. Use parágrafos curtos.
                    
                    FORMATO DE SAÍDA:
                    - 📌 O que aconteceu: (Resumo em 1 frase simples)
                    - 📅 Prazos/Datas: (Se houver)
                    - 👉 Próximo Passo: (O que o advogado ou cliente fará)
                    """

                    with st.spinner("Analisando processo..."):
                        response = client.models.generate_content(
                            model=MODEL_NAME, 
                            contents=prompt
                        )
                        
                        # Métricas e Logs
                        end_time = time.time()
                        duration = end_time - start_time
                        usage = response.usage_metadata
                        t_in = usage.prompt_token_count if usage else 0
                        t_out = usage.candidates_token_count if usage else 0
                        
                        # Salva Log
                        SaaSLogger.log_generation(
                            user_id=USER_ID_ATUAL,
                            input_text=st.session_state.texto_processo,
                            output_text=response.text,
                            model=MODEL_NAME,
                            tokens_in=t_in,
                            tokens_out=t_out,
                            time_taken=duration
                        )
                        
                        # Desconta Crédito
                        SaaSLogger.debit_credit(USER_ID_ATUAL)

                        st.session_state.mensagem_final = response.text
                        st.rerun() 

                except Exception as e:
                    SaaSLogger.log_event(USER_ID_ATUAL, "error_api", str(e))
                    st.error(f"Erro ao processar: {e}")

# --- RESULTADO ---
if st.session_state.mensagem_final:
    st.markdown("---")
    st.subheader("📱 Mensagem Pronta")
    
    mensagem_editada = st.text_area(
        "Revise antes de enviar:",
        value=st.session_state.mensagem_final,
        height=250
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("Nova Consulta (Limpar)", on_click=limpar_tudo, key="btn_limpar"):
            pass

    with col2:
        msg_encoded = quote(mensagem_editada, safe='')
        link_wa = f"https://wa.me/?text={msg_encoded}"
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" class="whatsapp-btn">
                📲 Enviar no WhatsApp
            </a>
        """, unsafe_allow_html=True)