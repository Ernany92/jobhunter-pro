import streamlit as st
import PyPDF2
import requests
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Tenta importar o SDK moderno do Gemini (Padrão 2026)
try:
    from google import genai
except ImportError:
    try:
        import google.genai as genai
    except:
        genai = None

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="JobHunter Pro - Remote Edition", layout="wide", page_icon="🏠")

# --- ESTADO DA SESSÃO ---
if 'vagas' not in st.session_state: st.session_state.vagas = []
if 'favoritos' not in st.session_state: st.session_state.favoritos = []

# --- BARRA LATERAL ---
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

# --- INICIALIZAÇÃO DO CLIENTE GEMINI (SDK 2026) ---
client = None
if genai and GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.sidebar.error(f"Erro ao iniciar cliente Gemini: {e}")

# --- FUNÇÃO DE LIMPEZA ---
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).lower()
    texto = re.sub(r'[^a-záéíóúçãõ0-9\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()

# --- FUNÇÃO PARA ANÁLISE SEMÂNTICA DO GEMINI ---
def analisar_vaga_com_gemini(curriculo, descricao_vaga):
    if not client:
        return "⚠️ SDK do Gemini ou API Key não configurados corretamente."
    
    prompt = f"""
    Você é um recrutador técnico especialista em tecnologia.
    Analise o Currículo fornecido contra a Descrição da Vaga abaixo.

    --- CURRÍCULO ---
    {curriculo}

    --- DESCRIÇÃO DA VAGA ---
    {descricao_vaga}

    --- INSTRUÇÕES ---
    Forneça uma análise extremamente direta, profissional e objetiva dividida exatamente em:
    1. **Compatibilidade Semântica Geral**: (Diga se o perfil faz sentido para a vaga de forma macro)
    2. **Pontos Fortes (Matches)**: (Máximo 3 pontos onde o candidato atende muito bem)
    3. **Gaps / O que falta**: (Ferramentas, linguagens ou conceitos técnicos mencionados na vaga que não estão claros no currículo)
    4. **Sugestão de Ajuste Rápido**: (Uma dica de como destacar alguma experiência no currículo para ter mais chances)

    Seja focado em tech, direto ao ponto e evite introduções longas.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Utilizando o modelo flash atualizado e rápido
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ Erro ao gerar análise com a IA: {e}"

# --- LÓGICA DE BUSCA ---
st.title("🎯 JobHunter Pro - Remote Edition")

# Mantemos o texto extraído na sessão para usar na IA sob demanda
if 'texto_curriculo_raw' not in st.session_state:
    st.session_state.texto_curriculo_raw = ""

if st.button("🚀 BUSCAR VAGAS REMOTAS", use_container_width=True):
    if arquivo_pdf and area_pesquisa:
        with st.spinner('Analisando currículo e minerando vagas...'):
            # 1. Processa o PDF do Currículo
            leitor = PyPDF2.PdfReader(arquivo_pdf)
            st.session_state.texto_curriculo_raw = "".join([p.extract_text() for p in leitor.pages])
            curr_limpo = limpar_texto(st.session_state.texto_curriculo_raw)

            # 2. Busca na SerpApi com Parâmetros Seguros
            try:
                query = f"{area_pesquisa} {nivel_vaga} remoto {localidade}".strip()
                param_data = opcoes_data[filtro_data]
                
                url_serp = "https://serpapi.com/search.json"
                params = {
                    "engine": "google_jobs",
                    "q": query,
                    "hl": "pt",
                    "gl": "br",
                    "ltype": "1",
                    "api_key": SERPAPI_KEY
                }
                
                if param_data:
                    params["chips"] = f"date_posted:{param_data}"
                
                res = requests.get(url_serp, params=params, timeout=15).json()
                vagas_brutas = res.get("jobs_results", [])
                
                if vagas_brutas:
                    resultados = []
                    vetorizador = TfidfVectorizer(stop_words=['de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'para', 'com'])
                    
                    for v in vagas_brutas:
                        desc_vaga = v.get('description', '')
                        vaga_limpa = limpar_texto(desc_vaga)
                        
                        try:
                            matriz = vetorizador.fit_transform([curr_limpo, vaga_limpa])
                            nota = round(cosine_similarity(matriz[0:1], matriz[1:2])[0][0] * 100, 1)
                        except:
                            nota = 0.0

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
            
            # Seção para acionar a Inteligência Artificial sob demanda
            st.divider()
            st.subheader("🧠 Inteligência de Carreira")
            
            # Ativa o botão de análise do Gemini apenas se o currículo já tiver sido carregado
            if st.session_state.texto_curriculo_raw:
                if st.button(f"🔍 Gerar Feedback da IA para esta Vaga", key=f"ai_{i}"):
                    with st.spinner("O Gemini está analisando a compatibilidade..."):
                        feedback = analisar_vaga_com_gemini(st.session_state.texto_curriculo_raw, vaga['desc'])
                        st.info(feedback)
            else:
                st.caption("⚠️ Faça o upload de um currículo na barra lateral para liberar a análise de IA.")
            st.divider()
            
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("🔗 Abrir Candidatura", vaga['url'], use_container_width=True)
            with c2:
                if st.button("📌 Salvar Vaga", key=f"fav_{i}", use_container_width=True):
                    if not any(f['url'] == vaga['url'] for f in st.session_state.favoritos):
                        st.session_state.favoritos.append(vaga)
                        st.toast("Vaga salva!")
                        st.rerun()
