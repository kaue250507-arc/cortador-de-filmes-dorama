import os
import re
import uuid
import html
import urllib.request
import subprocess
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gerador Filmes/Dorama", page_icon="🎬", layout="wide")

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

def limpar_legenda_kwai(texto):
    if not texto:
        return ""
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
    if not palavras:
        return "ASSISTA ATÉ AO FIM", "MOMENTO SURPREENDENTE"
    if len(palavras) <= 3:
        return frase, ""
    
    melhor_corte = max(1, len(palavras) // 2)
    menor_dif = float('inf')
    for i in range(1, len(palavras)):
        l1 = " ".join(palavras[:i])
        l2 = " ".join(palavras[i:])
        dif = abs(len(l1) - len(l2))
        if dif < menor_dif:
            menor_dif, melhor_corte = dif, i
    return " ".join(palavras[:melhor_corte]), " ".join(palavras[melhor_corte:])

def gerar_sinopse_com_ia(chave_api, texto_gancho):
    genai.configure(api_key=chave_api)
    modelo = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
    És um especialista em Doramas (K-dramas, C-dramas e J-dramas) e criador de conteúdos virais para Kwai, TikTok e Reels.
    Com base neste gancho/cena de um dorama: "{texto_gancho}", identifica qual é o dorama (ou sugere o mais provável de acordo com essa cena típica) e cria uma legenda pronta para publicação.

    A resposta DEVE seguir rigorosamente esta estrutura:
    🍿 Nome do Dorama: [Nome em Português e Nome Original entre parênteses]
    📖 Sinopse
