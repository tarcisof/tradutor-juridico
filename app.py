import streamlit as st
from google import genai
from urllib.parse import quote
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# =============================
# Configuração inicial
# =============================
st.set_page_config(
    page_title="Tradutor Jurídico",
    page_icon="⚖️",
    layout="centered"
)

# =============================
# Funções de Estado (Callbacks)
# =============================
# Esta função roda ANTES da tela ser redesenhada
def limpar_tudo():
    st.session_state.mensagem_final = ""
    st.session_state.texto_processo = ""
    # Não precisa st.rerun(), o callback já força a atualização

# =============================
# Estado da sessão
# =============================
if "mensagem_final" not in st.session_state:
    st.session_state.mensagem_final = ""

if "texto_processo" not in st.session_state:
    st.session_state.texto_processo = ""

# =============================
# Estilos CSS
# =============================
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        border-radius: 8px;
    }
    /* Estilo para o link do WhatsApp parecer um botão */
    .whatsapp-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #25D366;
        color: white !important;
        padding: 0.6rem;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        width: 100%;
        margin-top: 10px;
        text-align: center;
    }
    .whatsapp-btn:hover {
        background-color: #128C7E;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# Interface
# =============================
st.title("⚖️ Tradutor Jurídico")
st.caption("Converta juridiquês em mensagens claras para WhatsApp.")

with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Se não tiver no .env, pede na interface
    if not os.getenv("GOOGLE_API_KEY"):
        api_key_input = st.text_input("Cole sua Google API Key", type="password")
        if api_key_input:
            os.environ["GOOGLE_API_KEY"] = api_key_input
    
    tipo_andamento = st.selectbox(
        "Tipo de andamento:",
        ["Despacho", "Decisão", "Intimação / Prazo", "Juntada"]
    )
    
    tom_de_voz = st.radio(
        "Tom da mensagem:",
        ["Formal", "Empático (Recomendado)", "Direto"],
        index=1
    )
    
    nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: João")

# --- Área de Input ---
# O 'key' conecta este widget diretamente ao session_state
texto_input = st.text_area(
    "Cole o andamento processual:",
    height=150,
    key="texto_processo",
    placeholder="Ex: Certifico e dou fé que..."
)

# --- Botão Gerar ---
if st.button("✨ Gerar Explicação"):
    if not st.session_state.texto_processo.strip():
        st.warning("⚠️ Cole o texto do processo antes.")
    else:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("⚠️ API Key não configurada.")
        else:
            try:
                client = genai.Client(api_key=api_key)
                prompt = f"""
                Você é um advogado experiente explicando um andamento processual
                para um cliente leigo, por WhatsApp.

                Tipo do andamento: {tipo_andamento}
                Cliente: {nome_cliente if nome_cliente else 'Cliente'}
                Tom de voz: {tom_de_voz}

                Contexto sobre os tipos de andamento (use como referência obrigatória):
                - Despacho: normalmente não decide o mérito, apenas movimenta o processo.
                - Decisão: o juiz decidiu algo relevante no processo.
                - Sentença: encerra o processo em 1ª instância.
                - Juntada: apenas informa que um documento foi anexado, sem decisão.

                Texto original do processo:
                \"\"\"{st.session_state.texto_processo}\"\"\"

                Tarefa:
                Explique o conteúdo acima de forma simples, humana e objetiva,
                adaptando a explicação ao tipo de andamento informado.

                Regras obrigatórias:
                1. Use português simples, frases curtas e linguagem empática.
                2. Nunca use juridiquês sem explicação.
                3. Use emojis com moderação (máx. 2 ou 3).
                4. Destaque PRAZOS e DATAS em negrito (ex: *15 dias*, *até 10/03*).
                5. NUNCA garanta vitória ou resultado. Deixe claro que é apenas uma etapa do processo.
                6. Se houver prazo, explique claramente QUEM deve fazer O QUÊ.
                7. Se não houver prazo, informe isso explicitamente.

                Formato da resposta (siga exatamente):
                - 📌 O que aconteceu:
                - ⏰ Prazo (se houver):
                - 👉 O que precisamos fazer agora:
                - 🧘 Observação importante:
                """


                with st.spinner("Traduzindo..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash", 
                        contents=prompt
                    )
                    st.session_state.mensagem_final = response.text
                    st.rerun() # Força atualização para mostrar o resultado

            except Exception as e:
                st.error(f"Erro: {e}")

# =============================
# Área de Resultado
# =============================
if st.session_state.mensagem_final:
    st.divider()
    st.subheader("📱 Mensagem Pronta")
    
    # Editor de texto para ajustes finos
    mensagem_editada = st.text_area(
        "Edite se necessário:",
        value=st.session_state.mensagem_final,
        height=200
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("Para copiar, use o botão no canto do bloco abaixo 👇")
        st.code(mensagem_editada, language=None)

    with col2:
        msg_encoded = quote(mensagem_editada, safe='')
        link_wa = f"https://wa.me/?text={msg_encoded}"
        st.markdown(f"""
            <div style="margin-top: 40px;">
                <a href="{link_wa}" target="_blank" class="whatsapp-btn">
                    📲 Enviar no WhatsApp
                </a>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.button("✔️ Concluir Atendimento (Limpar)", on_click=limpar_tudo)