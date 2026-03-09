import streamlit as st
import PyPDF2
import requests
import re
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from deep_translator import GoogleTranslator

# --- INTERFACE STREAMLIT (Configuração Inicial) ---
st.set_page_config(page_title="JobHunter Pro - Remote Edition", layout="wide", page_icon="🏠")

# --- BARRA LATERAL: CONFIGURAÇÃO DE CHAVES ---
with st.sidebar:
    st.header("🔑 Configuração de Acesso")
    st.markdown("Para garantir o funcionamento, insira suas chaves de API abaixo:")
    
    # Inputs para chaves de usuário (tipo password para ocultar o texto)
    user_gemini_key = st.text_input("Gemini API Key", type="password", help="Obtenha em: aistudio.google.com")
    user_serpapi_key = st.text_input("SerpApi Key", type="password", help="Obtenha em: serpapi.com")
    
    # Lógica de Prioridade: 1º Input do Usuário | 2º Secrets do Streamlit
    GEMINI_API_KEY = user_gemini_key if user_gemini_key else st.secrets.get("GEMINI_API_KEY")
    SERPAPI_KEY = user_serpapi_key if user_serpapi_key else st.secrets.get("SERPAPI_KEY")

    st.divider()

# --- BLOQUEIO DE SEGURANÇA ---
# Se não houver chaves, o app para aqui e solicita ao usuário
if not GEMINI_API_KEY or not SERPAPI_KEY:
    st.title("🎯 JobHunter Pro - Remote Edition")
    st.warning("👈 **Ação Necessária:** Por favor, insira suas chaves de API na barra lateral esquerda para começar.")
    st.info("""
    Este buscador utiliza APIs externas para encontrar vagas e analisar currículos. 
    1. **Gemini Key:** Necessária para a Inteligência Artificial.
    2. **SerpApi Key:** Necessária para buscar vagas no Google Jobs.
    """)
    st.stop()
else:
    # Configura o Gemini se a chave existir
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Erro ao configurar Google Gemini: {e}")
        st.stop()

# --- FUNÇÕES AUXILIARES ---
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).lower()
    texto = re.sub(r'[^a-záéíóúçãõ0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def traduzir_para_ingles(texto):
    if not texto: return ""
    try:
        return GoogleTranslator(source='pt', target='en').translate(texto[:2500])
    except: return texto

# --- ESTADO DA SESSÃO ---
if 'vagas' not in st.session_state: st.session_state.vagas = []
if 'favoritos' not in st.session_state: st.session_state.favoritos = []

# --- INTERFACE: CONTINUAÇÃO DA SIDEBAR (Filtros) ---
with st.sidebar:
    st.header("🏠 Filtros Home Office")
    arquivo_pdf = st.file_uploader("1. Seu currículo (PDF)", type=["pdf"])
    area_pesquisa = st.text_input("2. Área da vaga:", placeholder="Ex: Desenvolvedor Python")
    nivel_vaga = st.text_input("3. Nível:", placeholder="Ex: Júnior")
    localidade = st.text_input("4. Localidade de busca:", value="Brasil")
    
    st.divider()
    st.subheader("🕒 Recência")
    opcoes_data = {
        "Qualquer data": "",
        "Últimas 24 horas": "today",
        "Últimos 3 dias": "3days",
        "Última semana": "week",
        "Último mês": "month"
    }
    filtro_data = st.selectbox("Mostrar vagas de:", list(opcoes_data.keys()))

    if st.session_state.favoritos:
        st.divider()
        st.subheader("⭐ Vagas Salvas")
        for fav in st.session_state.favoritos:
            st.caption(f"📌 {fav['titulo']} (@{fav['empresa']})")
        if st.button("Limpar Histórico", use_container_width=True):
            st.session_state.favoritos = []
            st.rerun()

st.title("🎯 JobHunter Pro - Remote Edition")
st.info("Este buscador está configurado para encontrar exclusivamente vagas **Home Office**.")

# --- LÓGICA DE BUSCA ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🚀 BUSCAR VAGAS REMOTAS", use_container_width=True):
        if arquivo_pdf and area_pesquisa:
            with st.spinner('Filtrando oportunidades remotas...'):
                leitor = PyPDF2.PdfReader(arquivo_pdf)
                texto_curriculo = "".join([p.extract_text() for p in leitor.pages])
                curr_en = traduzir_para_ingles(limpar_texto(texto_curriculo))

                try:
                    query = f"{area_pesquisa} {nivel_vaga} remoto {localidade}".strip()
                    param_data = opcoes_data[filtro_data]
                    
                    # Uso da variável SERPAPI_KEY (que pode ser a do usuário ou a do Secret)
                    url_serp = f"https://serpapi.com/search.json?engine=google_jobs&q={query}&hl=pt&gl=br&ltype=1&chips=date_posted:{param_data}&api_key={SERPAPI_KEY}"
                    
                    res = requests.get(url_serp, timeout=15).json()
                    vagas_brutas = []
                    
                    for v in res.get("jobs_results", []):
                        vagas_brutas.append({
                            "titulo": v.get('title'), 
                            "empresa": v.get('company_name'),
                            "desc": v.get('description', ''), 
                            "url": v.get('share_link'),
                            "data": v.get("detected_extensions", {}).get("posted_at", "Recente")
                        })
                    
                    if vagas_brutas:
                        vetorizador = TfidfVectorizer(stop_words='english')
                        for v in vagas_brutas:
                            vaga_en = traduzir_para_ingles(limpar_texto(v["desc"]))
                            matriz = vetorizador.fit_transform([curr_en, vaga_en])
                            v["nota"] = round(cosine_similarity(matriz[0:1], matriz[1:2])[0][0] * 100, 1)
                        
                        st.session_state.vagas = sorted(vagas_brutas, key=lambda x: x.get('nota', 0), reverse=True)[:15]
                    else:
                        st.warning("Nenhuma vaga remota encontrada para estes termos.")
                except Exception as e: 
                    st.error(f"Erro na busca: {e}")
        else:
            st.warning("Carregue o PDF e preencha a área da vaga.")

# --- EXIBIÇÃO ---
if st.session_state.vagas:
    st.subheader("💼 Vagas Home Office Encontradas")
    for i, vaga in enumerate(st.session_state.vagas):
        with st.expander(f"⭐ {vaga.get('nota', 0)}% Match - {vaga['titulo']} (@ {vaga['empresa']})"):
            st.write(f"🏢 **Empresa:** {vaga['empresa']} | 📅 **Postada:** {vaga['data']}")
            st.write(f"**Descrição:** {vaga['desc'][:600]}...")
            
            c1, c2 = st.columns([1, 1])
            with c1:
                st.link_button("🔗 Abrir Candidatura", vaga['url'], use_container_width=True)
            with c2:
                if st.button("⭐ Salvar para depois", key=f"fav_{i}", use_container_width=True):
                    if not any(f['url'] == vaga['url'] for f in st.session_state.favoritos):
                        st.session_state.favoritos.append(vaga)
                        st.toast(f"Vaga salva!")
                        st.rerun()

elif arquivo_pdf:
    st.info("Aguardando busca.")
