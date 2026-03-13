import streamlit as st
import PyPDF2
import requests
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from deep_translator import GoogleTranslator

# Tenta importar o genai (Padrão 2026)
try:
    from google import genai
except ImportError:
    try:
        import google.genai as genai
    except:
        genai = None

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="JobHunter Pro - Remote Edition", layout="wide", page_icon="🏠")

# --- ESTADO DA SESSÃO (Para não perder os favoritos e as vagas) ---
if 'vagas' not in st.session_state: st.session_state.vagas = []
if 'favoritos' not in st.session_state: st.session_state.favoritos = []

# --- BARRA LATERAL: CONFIGURAÇÕES E FILTROS ---
with st.sidebar:
    st.header("🔑 Configuração de Acesso")
    user_gemini_key = st.text_input("Gemini API Key", type="password")
    user_serpapi_key = st.text_input("SerpApi Key", type="password")
    
    GEMINI_API_KEY = user_gemini_key if user_gemini_key else ""
    SERPAPI_KEY = user_serpapi_key if user_serpapi_key else ""

    st.divider()
    st.header("🏠 Filtros Home Office")
    arquivo_pdf = st.file_uploader("1. Seu currículo (PDF)", type=["pdf"])
    area_pesquisa = st.text_input("2. Área da vaga:", placeholder="Ex: Desenvolvedor Python")
    nivel_vaga = st.text_input("3. Nível:", placeholder="Ex: Júnior, Pleno, Sênior")
    localidade = st.text_input("4. Localidade de busca:", value="Brasil")
    
    st.subheader("🕒 Recência")
    opcoes_data = {
        "Qualquer data": "",
        "Últimas 24 horas": "today",
        "Última semana": "week",
        "Último mês": "month"
    }
    filtro_data = st.selectbox("Mostrar vagas de:", list(opcoes_data.keys()))

    if st.session_state.favoritos:
        st.divider()
        st.subheader("⭐ Vagas Salvas")
        for fav in st.session_state.favoritos:
            st.caption(f"📌 {fav['titulo']} (@{fav['empresa']})")
        if st.button("Limpar Histórico"):
            st.session_state.favoritos = []
            st.rerun()

# --- BLOQUEIO DE SEGURANÇA ---
if not GEMINI_API_KEY or not SERPAPI_KEY:
    st.title("🎯 JobHunter Pro - Remote Edition")
    st.warning("👈 **Ação Necessária:** Por favor, insira suas chaves de API na barra lateral esquerda.")
    st.stop()

# --- FUNÇÕES AUXILIARES ---
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).lower()
    texto = re.sub(r'[^a-záéíóúçãõ0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def traduzir_para_ingles(texto):
    if not texto: return ""
    try:
        # Traduz para inglês para melhor performance do TfidfVectorizer (stop_words='english')
        return GoogleTranslator(source='pt', target='en').translate(texto[:2000])
    except: return texto

# --- LÓGICA DE BUSCA ---
st.title("🎯 JobHunter Pro - Remote Edition")

if st.button("🚀 BUSCAR VAGAS REMOTAS", use_container_width=True):
    if arquivo_pdf and area_pesquisa:
        with st.spinner('Analisando currículo e minerando vagas...'):
            # 1. Processa Currículo
            leitor = PyPDF2.PdfReader(arquivo_pdf)
            texto_curriculo = "".join([p.extract_text() for p in leitor.pages])
            curr_en = traduzir_para_ingles(limpar_texto(texto_curriculo))

            # 2. Busca na SerpApi
            try:
                query = f"{area_pesquisa} {nivel_vaga} remoto {localidade}".strip()
                param_data = opcoes_data[filtro_data]
                url_serp = f"https://serpapi.com/search.json?engine=google_jobs&q={query}&hl=pt&gl=br&ltype=1&chips=date_posted:{param_data}&api_key={SERPAPI_KEY}"
                
                res = requests.get(url_serp, timeout=15).json()
                vagas_brutas = res.get("jobs_results", [])
                
                if vagas_brutas:
                    resultados = []
                    vetorizador = TfidfVectorizer(stop_words='english')
                    
                    for v in vagas_brutas:
                        desc_vaga = v.get('description', '')
                        vaga_en = traduzir_para_ingles(limpar_texto(desc_vaga))
                        
                        # Cálculo de Match
                        try:
                            matriz = vetorizador.fit_transform([curr_en, vaga_en])
                            nota = round(cosine_similarity(matriz[0:1], matriz[1:2])[0][0] * 100, 1)
                        except: nota = 0

                        resultados.append({
                            "titulo": v.get('title'),
                            "empresa": v.get('company_name'),
                            "desc": desc_vaga,
                            "url": v.get('share_link'),
                            "data": v.get("detected_extensions", {}).get("posted_at", "Recente"),
                            "nota": nota
                        })
                    
                    st.session_state.vagas = sorted(resultados, key=lambda x: x['nota'], reverse=True)[:15]
                else:
                    st.warning("Nenhuma vaga remota encontrada para estes termos.")
            except Exception as e:
                st.error(f"Erro na busca: {e}")
    else:
        st.error("Por favor, envie seu currículo e defina a área da vaga.")

# --- EXIBIÇÃO ---
if st.session_state.vagas:
    st.subheader("💼 Vagas Encontradas")
    for i, vaga in enumerate(st.session_state.vagas):
        with st.expander(f"⭐ {vaga['nota']}% Match - {vaga['titulo']} (@ {vaga['empresa']})"):
            st.write(f"🏢 **Empresa:** {vaga['empresa']} | 📅 **Postada:** {vaga['data']}")
            st.write(f"**Descrição:** {vaga['desc'][:700]}...")
            
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("🔗 Abrir Candidatura", vaga['url'], use_container_width=True)
            with c2:
                if st.button("📌 Salvar", key=f"fav_{i}", use_container_width=True):
                    if not any(f['url'] == vaga['url'] for f in st.session_state.favoritos):
                        st.session_state.favoritos.append(vaga)
                        st.toast("Vaga salva!")
                        st.rerun()
