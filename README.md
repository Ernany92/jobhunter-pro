# 🎯 JobHunter Pro - Remote Edition

O **JobHunter Pro** é um buscador inteligente focado em oportunidades **Home Office**. Ele utiliza Inteligência Artificial para analisar seu currículo e calcular a compatibilidade com as vagas encontradas através de um Match % em tempo real.

🚀 **[CLIQUE AQUI PARA ACESSAR O APP ONLINE](https://jobhunter-pro.streamlit.app)**

---

## ✨ Funcionalidades
* **Busca Especializada:** Filtra apenas vagas remotas via Google Jobs.
* **Match por IA:** Usa o **Google Gemini** para comparar seu perfil com a descrição da vaga.
* **Tradução:** Traduz descrições de vagas gringas para facilitar a análise.
* **Segurança:** Chaves de API protegidas e nunca expostas no código (usando Streamlit Secrets).

---

## 🛠️ Tecnologias Utilizadas
* **Python** (Linguagem principal)
* **Streamlit** (Interface Web)
* **Google Gemini AI** (Cérebro do Match)
* **SerpApi** (Motor de busca de vagas)
* **Scikit-Learn** (Cálculo de similaridade)

## 🔑 Como usar o App (API Keys)

Para garantir que o serviço esteja sempre disponível e proteger os limites de uso, o **JobHunter Pro** permite que você utilize suas próprias chaves de API. 

**Como configurar no App:**
1. No menu lateral esquerdo (seta no topo), você encontrará o campo **"Configuração de Acesso"**.
2. Insira suas chaves:
   * **Gemini API Key:** Obtenha gratuitamente no [Google AI Studio](https://aistudio.google.com/).
   * **SerpApi Key:** Obtenha no [SerpApi](https://serpapi.com/) (permite buscas no Google Jobs).
3. Após inserir, o app será "destravado" e você poderá realizar suas buscas normalmente.

> *Suas chaves não são armazenadas pelo sistema; elas permanecem ativas apenas durante a sua sessão de uso.*


👤 Autor
Desenvolvido por Ernany Verruck.

Meu LinkedIn: www.linkedin.com/in/ernanyverruck


Este projeto foi desenvolvido com fins educacionais e de auxílio na busca por vagas remotas.
