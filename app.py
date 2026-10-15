import os
import re
import uuid
import html
import urllib.request
import subprocess
import streamlit as st

# AQUI ESTÁ O NOVO NOME DA ABA DO NAVEGADOR
st.set_page_config(page_title="Gerador Filmes/Dorama", page_icon="🎬", layout="wide")

# CSS Personalizado para deixar o site com cara de software profissional
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .btn-gerar>button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 15px;
        font-size: 18px;
    }
    .btn-gerar>button:hover {
        background-color: #ff2b2b;
        transform: scale(1.02);
    }
    .titulo-dash {
        text-align: center;
        padding-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Funções de limpeza
def limpar_legenda_kwai(texto):
    if not texto: return ""
    partes = texto.split(',')
    if len(partes) >= 2:
        candidato = partes[0].strip()
        if len(candidato) > 10 and candidato in texto[len(candidato):]:
            texto = candidato
    if ":" in texto:
        p2 = texto.split(":", 1)
        if len(p2) > 1 and len(p2[1].strip()) > 5:
            texto = p2[1]

    texto = re.sub(r'#\S+', '', texto)
    texto = re.sub(r'@\S+', '', texto)
    texto = re.sub(r'https?://\S+', '', texto)
    texto = re.sub(r'(?i)doramas?\s*(brasil|br|oficial|coreano)?', '', texto)
    texto = re.sub(r'(?i)drosil', '', texto)
    texto = texto.replace('"', '').replace("'", "").replace("(", "").replace(")", "")
    return " ".join(texto.split()).strip()

def quebrar_duas_linhas(frase):
    palavras = frase.split()
    if not palavras: return "ASSISTA ATÉ AO FIM", "MOMENTO SURPREENDENTE"
    if len(palavras) <= 3: return frase, ""
    
    melhor_corte = max(1, len(palavras) // 2)
    menor_dif = float('inf')
    for i in range(1, len(palavras)):
        l1 = " ".join(palavras[:i])
        l2 = " ".join(palavras[i:])
        dif = abs(len(l1) - len(l2))
        if dif < menor_dif:
            menor_dif, melhor_corte = dif, i
    return " ".join(palavras[:melhor_corte]), " ".join(palavras[melhor_corte:])

# Inicialização de sessão
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

# Cabeçalho Principal
st.markdown("<h1 class='titulo-dash'>🎬 Gerador Filmes/Dorama</h1>", unsafe_allow_html=True)

# Divisão de topo: Upload e Busca lado a lado
col_topo_1, col_topo_2 = st.columns([1, 1])

with col_topo_1:
    with st.container(border=True):
        st.markdown("### 📁 1. Arquivos de Identidade Visual")
        col_molde, col_fonte = st.columns(2)
        with col_molde:
            fundo_user = st.file_uploader("Upload do Molde (PNG/JPG)", type=["jpg", "jpeg", "png"])
        with col_fonte:
            fonte_user = st.file_uploader("Upload da Fonte (TTF)", type=["ttf"])

with col_topo_2:
    with st.container(border=True):
        st.markdown("### 🔎 2. Importar do Kwai")
        link_kwai = st.text_input("Cole o link direto do Kwai aqui:")
        
        if st.button("📥 Analisar e Extrair Vídeo", use_container_width=True):
            if not link_kwai or not link_kwai.startswith("http"):
                st.warning("⚠️ Insira um link válido do Kwai.")
            else:
                with st.spinner("Conectando ao Kwai e baixando mídia..."):
                    try:
                        req = urllib.request.Request(link_kwai, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=12) as resp:
                            html_raw = resp.read().decode('utf-8', errors='ignore')

                        legenda_kwai = ""
                        metas = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', html_raw, re.IGNORECASE)
                        for m in metas:
                            limpo = limpar_legenda_kwai(html.unescape(m
