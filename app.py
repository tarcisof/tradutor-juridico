import streamlit as st
from google import genai
from urllib.parse import quote
from dotenv import load_dotenv
import os
import time 
from services import SaaSLogger, supabase
from auth import tela_login, logout
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlencode

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

/* -------------------- BOTÕES -------------------- */
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

div.stButton > button p {
    color: #FFFFFF !important;
}

div.stButton > button:hover {
    background-color: #1a16c4 !important;
    color: #FFFFFF !important;
    box-shadow: 0 6px 12px rgba(39, 35, 237, 0.4);
    transform: translateY(-1px);
}

div.stButton > button:active {
    background-color: #1a16c4 !important;
    color: #FFFFFF !important;
    transform: translateY(0);
}

/* -------------------- INPUTS & SELETORES -------------------- */
.stTextArea textarea,
.stTextInput input,
.stSelectbox div[data-baseweb="select"] {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
}

.stTextArea textarea:focus,
.stTextInput input:focus {
    border-color: #2723ed !important;
    box-shadow: 0 0 0 2px rgba(39, 35, 237, 0.2) !important;
}

div[role="radiogroup"] label {
    background-color: #F1F5F9;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #E2E8F0;
    margin-right: 8px;
    cursor: pointer;
    transition: all 0.2s;
}

div[role="radiogroup"] label:hover {
    border-color: #2723ed;
    color: #2723ed !important;
}

div[role="radiogroup"] [data-baseweb="radio"] {
    accent-color: #2723ed !important;
}

/* -------------------- EXPANDER (CORREÇÃO DEFINITIVA) -------------------- */
details {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    margin-bottom: 10px;
}

details summary {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

details summary:hover {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

/* Quando expandido */
details[open] {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

/* Conteúdo interno do expander */
details[open] > div {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

/* Setinha sempre preta */
details summary svg {
    fill: #000000 !important;
    stroke: #000000 !important;
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

    with st.sidebar:
        USER_ID_ATUAL = st.session_state.user_id

        # ---------------------------------------------------------
        # 1. BUSCA DADOS INICIAIS
        # ---------------------------------------------------------
        try:
            dados = supabase.table("profiles").select("*").eq("id", USER_ID_ATUAL).execute()
            info = dados.data[0] if dados.data else {"plan_status": "free", "credits_balance": 0, "last_credit_reset": None}
        except:
            info = {"plan_status": "free", "credits_balance": 0, "last_credit_reset": None}

        # ---------------------------------------------------------
        # 2. VERIFICAÇÃO DE RESET (CRÍTICO PARA O TEMPO APARECER CERTO)
        # ---------------------------------------------------------
        if info["plan_status"] == "free":
            SaaSLogger.refresh_free_credits_if_needed(USER_ID_ATUAL)
            dados_refresh = supabase.table("profiles").select("*").eq("id", USER_ID_ATUAL).execute()
            if dados_refresh.data:
                info = dados_refresh.data[0]

        # ---------------------------------------------------------
        # 3. VISUALIZAÇÃO (SEU CÓDIGO AQUI)
        # ---------------------------------------------------------
        with st.expander("👤 Minha Conta", expanded=True):
            st.write(f"**Email:** {USER_ID_ATUAL}")
            
            # Define cor do status
            status_color = "green" if info['plan_status'] != 'free' else "orange"
            st.markdown(f"**Plano:** :{status_color}[{info['plan_status'].upper()}]")
            
            # Se for Free, mostra saldo e tempo
            if info["plan_status"] == "free":
                st.write(f"**Créditos:** {info['credits_balance']}")
                
                last_reset = info.get("last_credit_reset")
                reset_em = SaaSLogger.time_until_next_reset(last_reset)

                # Dica visual: Se tiver 0 créditos, chama mais atenção (warning)
                # Se tiver créditos, fica discreto (caption)
                if info['credits_balance'] == 0:
                    st.warning(f"⏳ Renova **{reset_em}**")
                else:
                    st.caption(f"🔄 Renova **{reset_em}**")



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
                ⭐ VIRE PREMIUM
            </div>
        </a>
        """, unsafe_allow_html=True)

    st.markdown("<h2 style='color: black; margin-bottom: 10px;'>Configuração</h2>", unsafe_allow_html=True)

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

    st.markdown("""
        <style>
        /* Placeholder do input */
        input::placeholder {
            color: black !important;
            opacity: 1; /* importante pro Chrome */
        }

        /* Firefox */
        input::-moz-placeholder {
            color: black !important;
            opacity: 1;
        }

        /* Edge / IE */
        input:-ms-input-placeholder {
            color: black !important;
        }
        </style>
    """, unsafe_allow_html=True)

    nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Sr. João")
    
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
                    5. Se não tiver nome do Cliente, chame de Cliente.
                    
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
                        
                        end_time = time.time()
                        duration = end_time - start_time
                        usage = response.usage_metadata
                        t_in = usage.prompt_token_count if usage else 0
                        t_out = usage.candidates_token_count if usage else 0
                        
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

tab_traducao, tab_historico = st.tabs(
    ["📝 Tradução", "📜 Histórico"]
)
# --- RESULTADO ---
with tab_traducao:
    if st.session_state.mensagem_final:
        st.markdown("<h2 style='color: black; margin-bottom: 10px;'>Mensagem Pronta</h2>", unsafe_allow_html=True)

        mensagem_editada = st.text_area(
            "Revise antes de enviar:",
            value=st.session_state.mensagem_final,
            height=250
        )

        col1, col2 = st.columns([4, 1])

        with col1:
            st.code(mensagem_editada, language=None)
            st.caption("☝️ Clique no ícone acima para copiar")

        with col2:
            st.empty()  # pode usar pra algo depois ou remover totalmente

        st.markdown("<br>", unsafe_allow_html=True)

        # ---- BOTÃO WHATSAPP (FULL WIDTH) ----
        params = {"text": mensagem_editada}
        link_wa = f"https://wa.me/?{urlencode(params, encoding='utf-8')}"
        
        st.markdown(
            f"""
            <a href="{link_wa}" target="_blank" style="
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: #25D366;
                color: white;
                font-weight: 800;
                padding: 14px;
                border-radius: 10px;
                text-decoration: none;
                text-align: center;
                width: 100%;
                margin-bottom: 12px;
                font-size: 16px;
            ">
                📲 Enviar no WhatsApp
            </a>
            """,
            unsafe_allow_html=True
        )

        # ---- BOTÃO LIMPAR ----
        st.button(
            "🗑️ Limpar Tudo e Iniciar Novo",
            on_click=limpar_tudo,
            use_container_width=True
        )
with tab_historico:
    st.markdown("<h2 style='color: black; margin-bottom: 10px;'>Histórico de Traduções</h2>", unsafe_allow_html=True)

    if info["plan_status"] == "free":
        st.info("ℹ️ Plano Grátis: Você vê o histórico das últimas 24 horas.")
    else:
        st.success("💎 Plano Premium: Visualizando histórico completo do mês.")

    if st.button("🔄 Atualizar Histórico"):
        st.rerun()

    historico = SaaSLogger.get_history(
        USER_ID_ATUAL,
        info["plan_status"]
    )
    st.markdown("""
    <style>
    /* Setinha (arrow) do expander */
    details summary svg {
        fill: black !important;
        stroke: black !important;
    }

    /* Texto do título do expander */
    details summary {
        color: black !important;
    }
    </style>
    """, unsafe_allow_html=True)


    if not historico:
        st.write("Nenhum histórico encontrado para o período.")
    else:
        tz_sp = ZoneInfo("America/Sao_Paulo")

        for item in historico:
            # Converte a data do Supabase (UTC) para São Paulo
            data_utc = datetime.fromisoformat(item["created_at"])
            data_sp = data_utc.astimezone(tz_sp)
            data_formatada = data_sp.strftime("%d/%m/%Y %H:%M")

            with st.expander(f"📅 {data_formatada}"):
                st.markdown(
                    "<h2 style='color: black; margin-bottom: 10px;'>Original</h2>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <p style="
                        color: black;
                        font-size: 14px;
                        line-height: 1.6;
                        white-space: pre-wrap;
                        margin: 0;
                    ">
                        {item["input_text"][:150] + "..." if len(item["input_text"]) > 150 else item["input_text"]}
                    </p>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    "<h2 style='color: black; margin-bottom: 10px;'>Tradução</h2>",
                    unsafe_allow_html=True
                )

                st.code(item["output_text"], language=None)