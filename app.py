import os
import re
import uuid
import html
import urllib.request
import subprocess
import streamlit as st

st.set_page_config(page_title="DoramaX Pro", page_icon="🎬", layout="centered")

def limpar_legenda_kwai(texto):
    if not texto:
        return ""
    
    partes = texto.split(',')
    if len(partes) >= 2:
        candidato = partes[0].strip()
        if len(candidato) > 10 and candidato in texto[len(candidato):]:
            texto = candidato
            
    if ":" in texto:
        partes_dois = texto.split(":", 1)
        if len(partes_dois) > 1 and len(partes_dois[1].strip()) > 5:
            texto = partes_dois[1]

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

st.title("🎬 DoramaX - Gerador de Cortes")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

st.subheader("1. Ficheiros de Estilo")
col1, col2 = st.columns(2)
with col1:
    fundo_user = st.file_uploader("Seu Molde / Fundo (JPG/PNG)", type=["jpg", "jpeg", "png"])
with col2:
    fonte_user = st.file_uploader("Sua Fonte (TTF)", type=["ttf"])

st.subheader("2. Vídeo do Kwai")
link_kwai = st.text_input("Cole o link do Kwai:", placeholder="https://k.kwai.com/p/...")

if st.button("🔍 Buscar Vídeo e Legenda Automática"):
    if not link_kwai or not link_kwai.startswith("http"):
        st.warning("Insira um link válido do Kwai.")
    else:
        with st.spinner("A localizar vídeo e a extrair legenda..."):
            try:
                req = urllib.request.Request(link_kwai, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    html_raw = resp.read().decode('utf-8', errors='ignore')

                legenda_kwai = ""
                metas = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', html_raw, re.IGNORECASE)
                for m in metas:
                    limpo = limpar_legenda_kwai(html.unescape(m))
                    if len(limpo) > 5:
                        legenda_kwai = limpo
                        break

                urls_mp4 = re.findall(r'https://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html_raw.replace(r'\/', '/'))
                if urls_mp4:
                    caminho_preview = os.path.join(pasta_temp, "preview.mp4")
                    urllib.request.urlretrieve(urls_mp4[0], caminho_preview)
                    st.session_state["video_original"] = caminho_preview
                    st.session_state["legenda_detectada"] = legenda_kwai or "ASSISTA ATÉ AO FIM"
                    st.success("Vídeo e legenda encontrados com sucesso!")
                else:
                    st.error("Não foi possível carregar o vídeo deste link.")
            except Exception as e:
                st.error(f"Erro ao ligar ao Kwai: {e}")

if "video_original" in st.session_state and os.path.exists(st.session_state["video_original"]):
    st.video(st.session_state["video_original"])

    st.subheader("3. Personalização do Corte")
    
    texto_final = st.text_input(
        "Texto de Destaque no Topo:", 
        value=st.session_state.get("legenda_detectada", "")
    )

    duracao = st.selectbox("Duração:", ["30s", "50s", "60s", "Original Completo"])

    if st.button("🚀 Gerar Vídeo no seu Molde"):
        if not fundo_user or not fonte_user:
            st.error("Por favor, envie o seu Molde e a sua Fonte no Passo 1.")
        else:
            with st.spinner("A renderizar vídeo com a fonte maior e reposicionada..."):
                l1, l2 = quebrar_duas_linhas(texto_final)

                caminho_molde = os.path.join(pasta_temp, "molde.jpg")
                caminho_fonte = os.path.join(pasta_temp, "fonte.ttf")
                caminho_saida = os.path.join(pasta_temp, "resultado.mp4")
                txt1_path = os.path.join(pasta_temp, "l1.txt")
                txt2_path = os.path.join(pasta_temp, "l2.txt")

                with open(caminho_molde, "wb") as f:
                    f.write(fundo_user.getbuffer())
                with open(caminho_fonte, "wb") as f:
                    f.write(fonte_user.getbuffer())
                with open(txt1_path, "w", encoding="utf-8") as f:
                    f.write(l1)
                with open(txt2_path, "w", encoding="utf-8") as f:
                    f.write(l2)

                filtro_video = "[1:v]crop=in_w:in_w*9/16:0:(in_h-in_w*9/16)/2,scale=1080:608[vid];"

                # Ajuste de tamanho (65) e posição Y (mais perto do vídeo)
                draw_l1 = (
                    f"drawtext=fontfile='{caminho_fonte}':textfile='{txt1_path}':"
                    f"fontcolor=black:fontsize=65:"
                    f"x=(w-text_w)/2:y=500"
                )
                draw_l2 = (
                    f"drawtext=fontfile='{caminho_fonte}':textfile='{txt2_path}':"
                    f"fontcolor=black:fontsize=65:"
                    f"x=(w-text_w)/2:y=585"
                )

                filtro_completo = (
                    f"[0:v]scale=1080:1920[fundo];"
                    f"{filtro_video}"
                    f"[fundo][vid]overlay=0:(H-h)/2[base];"
                    f"[base]{draw_l1},{draw_l2}[v]"
                )

                comando = [
                    "ffmpeg", "-y",
                    "-i", caminho_molde,
                    "-i", st.session_state["video_original"],
                    "-filter_complex", filtro_completo,
                    "-map", "[v]", "-map", "1:a?",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac"
                ]

                mapa_dur = {"30s": "30", "50s": "50", "60s": "60"}
                if duracao in mapa_dur:
                    comando.extend(["-t", mapa_dur[duracao]])

                comando.append(caminho_saida)
                subprocess.run(comando, check=True)

                st.success("Vídeo finalizado com sucesso no seu molde!")
                st.video(caminho_saida)
                with open(caminho_saida, "rb") as f:
                    st.download_button("⬇️ Descarregar Vídeo Pronto", f, file_name="corte_doramax.mp4")
