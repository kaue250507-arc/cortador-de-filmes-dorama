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
    if ":" in texto:
        partes = texto.split(":", 1)
        if len(partes) > 1 and len(partes[1].strip()) > 5:
            texto = partes[1]

    # Remove hashtags, menções e links do Kwai
    texto = re.sub(r'#\S+', '', texto)
    texto = re.sub(r'@\S+', '', texto)
    texto = re.sub(r'https?://\S+', '', texto)
    texto = re.sub(r'(?i)doramas?\s*(brasil|br|oficial|coreano)?', '', texto)
    texto = texto.replace('"', '').replace("'", "")
    
    frases = [f.strip() for f in texto.split('.') if len(f.strip()) > 3]
    if frases:
        texto = frases[0]
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

# 1. Upload dos ficheiros de estilo
st.subheader("1. Ficheiros de Estilo")
col1, col2 = st.columns(2)
with col1:
    fundo_user = st.file_uploader("Seu Molde Rosa (JPG/PNG)", type=["jpg", "jpeg", "png"])
with col2:
    fonte_user = st.file_uploader("Sua Fonte TTF (ex: Nexa-Heavy)", type=["ttf"])

# 2. Busca do vídeo e da legenda
st.subheader("2. Vídeo do Kwai")
link_kwai = st.text_input("Cole o link do Kwai:", placeholder="https://k.kwai.com/p/...")

if st.button("🔍 Buscar Prévia e Legenda"):
    if not link_kwai or not link_kwai.startswith("http"):
        st.warning("Insira um link válido do Kwai.")
    else:
        with st.spinner("A localizar vídeo e a extrair o texto original..."):
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
                    st.session_state["legenda_detectada"] = legenda_kwai or "Ela foi confundida com a amante"
                    st.success("Vídeo e texto detetados com sucesso!")
                else:
                    st.error("Não foi possível carregar o vídeo deste link.")
            except Exception as e:
                st.error(f"Erro ao ligar ao Kwai: {e}")

# 3. Prévia e Configuração do Corte
if "video_original" in st.session_state and os.path.exists(st.session_state["video_original"]):
    st.video(st.session_state["video_original"])

    st.subheader("3. Personalização do Corte")
    
    texto_final = st.text_input(
        "Texto de Destaque no Topo (ele será dividido em 2 linhas automaticamente):", 
        value=st.session_state.get("legenda_detectada", "")
    )
    
    ajuste_corte = st.radio(
        "Enquadramento no Molde:",
        ["✂️ Recortar cena central limpa (Remove faixas pretas e textos antigos)", 
         "📐 Manter vídeo original sem recorte"],
        index=0
    )

    duracao = st.selectbox("Duração:", ["30s", "50s", "60s", "Original Completo"])

    if st.button("🚀 Gerar Vídeo com Molde e Fonte"):
        if not fundo_user or not fonte_user:
            st.error("Carregue o Molde e a Fonte no Passo 1.")
        else:
            with st.spinner("A aplicar o molde rosa, recortar faixas e diagramar o texto preto..."):
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

                # Recorta o centro da cena para remover as faixas e logos do corte anterior
                if "Recortar cena central limpa" in ajuste_corte:
                    filtro_video = "[1:v]crop=in_w:in_w*9/16:0:(in_h-in_w*9/16)/2,scale=1080:608[vid];"
                else:
                    filtro_video = "[1:v]scale=1080:-2[vid];"

                # Texto em PRETO puro, centralizado e posicionado na faixa rosa abaixo da logo
                draw_l1 = (
                    f"drawtext=fontfile='{caminho_fonte}':textfile='{txt1_path}':"
                    f"fontcolor=black:fontsize=50:"
                    f"x=(w-text_w)/2:y=470"
                )
                draw_l2 = (
                    f"drawtext=fontfile='{caminho_fonte}':textfile='{txt2_path}':"
                    f"fontcolor=black:fontsize=50:"
                    f"x=(w-text_w)/2:y=545"
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

                st.success("Vídeo finalizado com o seu estilo!")
                st.video(caminho_saida)
                with open(caminho_saida, "rb") as f:
                    st.download_button("⬇️ Baixar Vídeo Pronto", f, file_name="corte_doramax.mp4")
