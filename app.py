import os
import re
import uuid
import html
import shutil
import urllib.request
import subprocess
import streamlit as st

st.set_page_config(page_title="DoramaX Pro", page_icon="🎬", layout="centered")

st.title("🎬 DoramaX - Gerador de Cortes")
st.write("Insira o link, confira a prévia e crie o seu corte personalizado.")

# 1. Sessão isolada para não misturar ficheiros entre diferentes pessoas
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

pasta_temp = f"temp_{st.session_state.session_id}"
os.makedirs(pasta_temp, exist_ok=True)

# 2. Upload de Moldes Personalizados
st.subheader("1. Seus Arquivos de Estilo")
col1, col2 = st.columns(2)
with col1:
    fundo_user = st.file_uploader("Envie seu Molde/Fundo (JPG/PNG)", type=["jpg", "jpeg", "png"])
with col2:
    fonte_user = st.file_uploader("Envie sua Fonte (TTF)", type=["ttf"])

# 3. Link do Kwai e Prévia
st.subheader("2. Vídeo do Kwai")
link_kwai = st.text_input("Cole o link do Kwai aqui:", placeholder="https://k.kwai.com/p/...")

if st.button("🔍 Buscar Prévia do Vídeo"):
    if not link_kwai or not link_kwai.startswith("http"):
        st.warning("Insira um link válido do Kwai.")
    else:
        with st.spinner("A localizar o vídeo no Kwai..."):
            try:
                req = urllib.request.Request(link_kwai, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    html_raw = resp.read().decode('utf-8', errors='ignore')
                
                urls_mp4 = re.findall(r'https://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html_raw.replace(r'\/', '/'))
                if urls_mp4:
                    caminho_preview = os.path.join(pasta_temp, "preview.mp4")
                    urllib.request.urlretrieve(urls_mp4[0], caminho_preview)
                    st.session_state["video_original"] = caminho_preview
                    st.success("Vídeo encontrado! Veja a prévia abaixo.")
                else:
                    st.error("Não foi possível extrair o vídeo diretamente deste link.")
            except Exception as e:
                st.error(f"Erro ao ligar ao Kwai: {e}")

# Exibe o player de prévia se o vídeo foi descarregado
if "video_original" in st.session_state and os.path.exists(st.session_state["video_original"]):
    st.video(st.session_state["video_original"])

    # 4. Textos e Duração
    st.subheader("3. Personalização do Corte")
    txt_l1 = st.text_input("Texto da Linha 1:", value="ASSISTA ATÉ AO FIM")
    txt_l2 = st.text_input("Texto da Linha 2:", value="MOMENTO SURPREENDENTE")
    duracao = st.selectbox("Escolha a duração:", ["30s", "50s", "60s", "Original Completo"])

    if st.button("🚀 Gerar Vídeo Final"):
        if not fundo_user or not fonte_user:
            st.error("Atenção: Carregue o seu Molde e a sua Fonte no Passo 1 antes de gerar.")
        else:
            with st.spinner("A renderizar vídeo com alta definição..."):
                caminho_molde = os.path.join(pasta_temp, "molde.jpg")
                caminho_fonte = os.path.join(pasta_temp, "fonte.ttf")
                caminho_saida = os.path.join(pasta_temp, "corte_final.mp4")

                with open(caminho_molde, "wb") as f:
                    f.write(fundo_user.getbuffer())
                with open(caminho_fonte, "wb") as f:
                    f.write(fonte_user.getbuffer())

                comando = [
                    "ffmpeg", "-y",
                    "-i", caminho_molde,
                    "-i", st.session_state["video_original"],
                    "-filter_complex",
                    f"[0:v]scale=1080:1920[fundo];"
                    f"[1:v]scale=1080:-2[vid];"
                    f"[fundo][vid]overlay=0:(H-h)/2[base];"
                    f"[base]drawtext=fontfile='{caminho_fonte}':text='{txt_l1}':fontcolor=black:fontsize=65:x=(w-text_w)/2:y=500,"
                    f"drawtext=fontfile='{caminho_fonte}':text='{txt_l2}':fontcolor=black:fontsize=65:x=(w-text_w)/2:y=580[v]",
                    "-map", "[v]", "-map", "1:a?",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac"
                ]

                mapa_duracao = {"30s": "30", "50s": "50", "60s": "60"}
                if duracao in mapa_duracao:
                    comando.extend(["-t", mapa_duracao[duracao]])

                comando.append(caminho_saida)
                subprocess.run(comando, check=True)

                st.success("Vídeo concluído com sucesso!")
                st.video(caminho_saida)
                with open(caminho_saida, "rb") as f:
                    st.download_button("⬇️ Baixar Vídeo Pronto", f, file_name="dorama_corte.mp4")
