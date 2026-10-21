import os
import re
import uuid
import html
import json
import urllib.request
import urllib.parse
import subprocess
import glob
import shutil
import streamlit as st

st.set_page_config(page_title="Studio Dorama - Feed & Cortes", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# PERFIS MONITORADOS (KWAI DORAMA)
# ==========================================
PERFIS_KWAI = {
    "doramasbrasil": "https://kwai-video.com/u/@doramasbrasill/8x4HFCCh",
    "Doramasonline": "https://kwai-video.com/u/@Doramasonline./D7uCBBQs",
    "josiiedits": "https://kwai-video.com/u/@josiiedits/KCWSzKBk",
    "clichegarota": "https://kwai-video.com/u/@clichegarota/6fF9JuCW",
    "DoramaOnline": "https://kwai-video.com/u/@DoramaOnline./XuCEcVtu",
    "mundosdodorama552": "https://kwai-video.com/u/@mundodosdorama552/VCRC2ZaI",
}

# Desativa tradução automática e estiliza o feed estilo TikTok
st.markdown("""
<html lang="pt" translate="no">
<head>
    <meta name="google" content="notranslate" />
</head>
</html>
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp { background-color: #0b0f19; }

    .stApp [data-testid="stImage"],
    .stApp [data-testid="stContainer"],
    div[data-testid="stVerticalBlock"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }
    div[data-testid="stImage"] img {
        opacity: 1 !important;
        transition: none !important;
    }

    .titulo-app {
        text-align: center;
        font-size: 2.6rem;
        font-weight: 900;
        background: linear-gradient(90deg, #ff4b4b, #ff7676, #ff4b4b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
        padding-top: 10px;
    }
    
    .subtitulo-app {
        text-align: center;
        color: #8b949e;
        font-size: 1rem;
        margin-bottom: 20px;
    }

    /* Menu de Abas Superior Moderno */
    div[data-testid="stRadio"] > div {
        display: flex;
        justify-content: center;
        gap: 20px;
        background: #161b22;
        padding: 10px 15px;
        border-radius: 14px;
        border: 1px solid #30363d;
        margin-bottom: 25px;
    }
    div[data-testid="stRadio"] label {
        background: transparent !important;
        color: #c9d1d9 !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        padding: 6px 16px !important;
        cursor: pointer !important;
        border-radius: 8px !important;
    }

    div[data-testid="stContainer"] {
        background-color: #161b22;
        border-radius: 16px !important;
        border: 1px solid #30363d !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
        padding: 15px;
    }
    
    div[data-testid="stContainer"]:hover {
        border-color: #ff4b4b !important;
    }

    h3, h4 { color: #e6edf3 !important; font-weight: 700 !important; }
    label { color: #c9d1d9 !important; font-weight: 600 !important; }

    button[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff1f1f 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 0 !important;
        font-size: 1.05rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4) !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.6) !important;
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0d1117 !important;
        color: white !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

def limpar_legenda(texto):
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
    texto = re.sub(r'(?i)filmes?\s*(brasil|br|oficial)?', '', texto)
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

def tem_imagem_de_video(caminho_arquivo):
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", caminho_arquivo],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return "video" in res.stdout.lower()
    except Exception:
        return True

def tem_audio(caminho_arquivo):
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", caminho_arquivo],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return "audio" in res.stdout.lower()
    except Exception:
        return True

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_videos_feed_tiktok(termo_pesquisa):
    """Busca os IDs dos shorts de doramas mais assistidos para exibir no player TikTok."""
    import yt_dlp
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            query = f"ytsearch15:{termo_pesquisa} dorama shorts"
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', []) if info else []
            for item in entries:
                if not item:
                    continue
                v_id = item.get('id')
                v_title = item.get('title') or "Cena Incrível de Dorama"
                if v_id:
                    videos.append({
                        "id": v_id,
                        "title": v_title,
                        "url": f"https://www.youtube.com/watch?v={v_id}"
                    })
    except Exception:
        pass
    
    # Lista de segurança garantida caso a busca do YouTube demore
    if not videos:
        videos = [
            {"id": "a93e3B2RjYg", "title": "Ele ficou com ciúmes ao ver ela com outro", "url": "https://www.youtube.com/watch?v=a93e3B2RjYg"},
            {"id": "cI8_K7y_9Fw", "title": "Quando ele descobre a verdade sobre ela", "url": "https://www.youtube.com/watch?v=cI8_K7y_9Fw"},
            {"id": "4mXJ9_n3q0E", "title": "Momento fofo do casal no dorama", "url": "https://www.youtube.com/watch?v=4mXJ9_n3q0E"},
        ]
    return videos

def descarregar_video_motor(url_alvo, pasta_destino):
    """Motor de download com proteção anti-bloqueio para servidores em nuvem."""
    caminho_saida = os.path.join(pasta_destino, "preview.mp4")
    for f_antigo in glob.glob(os.path.join(pasta_destino, "preview*")):
        try: os.remove(f_antigo)
        except Exception: pass

    legenda = ""
    sucesso = False

    # 1. Kwai
    if "kwai.com" in url_alvo or "kwai-video.com" in url_alvo:
        try:
            req = urllib.request.Request(url_alvo, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                html_raw = resp.read().decode('utf-8', errors='ignore')

            metas = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', html_raw, re.IGNORECASE)
            for m in metas:
                limpo = limpar_legenda(html.unescape(m))
                if len(limpo) > 5:
                    legenda = limpo
                    break

            urls_mp4 = re.findall(r'https://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html_raw.replace(r'\/', '/'))
            if urls_mp4:
                urllib.request.urlretrieve(urls_mp4[0], caminho_saida)
                sucesso = True
        except Exception:
            sucesso = False

    # 2. TikTok
    elif "tiktok.com" in url_alvo:
        try:
            api_url = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url_alvo)}"
            req_tik = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_tik, timeout=15) as resp_tik:
                dados_tik = json.loads(resp_tik.read().decode('utf-8'))
            if dados_tik.get("code") == 0:
                data_item = dados_tik.get("data", {})
                url_mp4_tik = data_item.get("play") or data_item.get("wmplay")
                if url_mp4_tik:
                    req_v = urllib.request.Request(url_mp4_tik, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req_v, timeout=25) as v_stream, open(caminho_saida, "wb") as f_out:
                        f_out.write(v_stream.read())
                    legenda = limpar_legenda(data_item.get("title", ""))
                    sucesso = True
        except Exception:
            sucesso = False

    # 3. YouTube / Motor Geral (com cliente mobile para evitar bloqueio 403)
    if not sucesso:
        import yt_dlp
        ydl_opts = {
            'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(pasta_destino, 'preview_dl.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],
                    'player_skip': ['webpage', 'configs']
                }
            }
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_alvo, download=True)
                if not legenda:
                    legenda = limpar_legenda(f"{info.get('title', '')} {info.get('description', '')}")

            arquivos = glob.glob(os.path.join(pasta_destino, "preview_dl.*"))
            if arquivos:
                arq_orig = arquivos[0]
                if not arq_orig.endswith(".mp4"):
                    subprocess.run(["ffmpeg", "-y", "-i", arq_orig, "-c", "copy", caminho_saida], check=True)
                    try: os.remove(arq_orig)
                    except Exception: pass
                else:
                    shutil.move(arq_orig, caminho_saida)
                sucesso = True
        except Exception:
            sucesso = False

    return sucesso, caminho_saida, legenda

# Estados de Sessão
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "preview_fixo" not in st.session_state:
    st.session_state["preview_fixo"] = False

if "feed_index" not in st.session_state:
    st.session_state["feed_index"] = 0

if "nav_radio" not in st.session_state:
    st.session_state["nav_radio"] = "🔥 Feed de Vídeos (Estilo TikTok)"

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

st.markdown('<div class="titulo-app">🎬 Studio Dorama: Feed & Cortes</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-app">Assista a vídeos virais no estilo TikTok e crie cortes profissionais</div>', unsafe_allow_html=True)

# Menu Superior de Navegação
aba_selecionada = st.radio(
    "Navegação:",
    ["🔥 Feed de Vídeos (Estilo TikTok)", "🎬 Editor de Cortes"],
    key="nav_radio",
    horizontal=True,
    label_visibility="collapsed"
)

# ==============================================================================
# ABA 1: FEED ESTILO TIKTOK
# ==============================================================================
if aba_selecionada == "🔥 Feed de Vídeos (Estilo TikTok)":
    
    with st.expander("📺 Ver Perfis Concorrentes do Kwai (Acesso Rápido)"):
        st.caption("Acesse diretamente os perfis que você acompanha no Kwai:")
        cols_kwai = st.columns(3)
        for i, (nome_k, link_k) in enumerate(PERFIS_KWAI.items()):
            with cols_kwai[i % 3]:
                st.link_button(f"🔗 @{nome_k}", link_k, use_container_width=True)

    # Barra de busca por temas
    col_pesq1, col_pesq2 = st.columns([3, 1])
    with col_pesq1:
        termo_feed = st.text_input("Tema do Feed:", value=st.session_state.get("termo_busca_salvo", "dorama ciúmes romance"), placeholder="Ex: ciúmes, vingança, beijo, comédia")
    with col_pesq2:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar Feed", use_container_width=True):
            st.session_state["termo_busca_salvo"] = termo_feed
            st.session_state["feed_index"] = 0
            st.session_state["videos_feed"] = buscar_videos_feed_tiktok(termo_feed)
            st.rerun()

    if "videos_feed" not in st.session_state:
        st.session_state["videos_feed"] = buscar_videos_feed_tiktok(termo_feed)

    lista_videos = st.session_state["videos_feed"]
    total_videos = len(lista_videos)
    idx_atual = max(0, min(st.session_state["feed_index"], total_videos - 1))
    video_atual = lista_videos[idx_atual]

    # Indicador de posição do feed
    st.markdown(
        f"<p style='text-align: center; color: #ff7676; font-size: 1.1rem; font-weight: 700; margin-bottom: 5px;'>"
        f"📱 Vídeo {idx_atual + 1} de {total_videos}: <span style='color: white;'>{video_atual['title']}</span>"
        f"</p>", 
        unsafe_allow_html=True
    )

    # PLAYER VERTICAL FORMATO SMARTPHONE (TIKTOK / REELS)
    col_esp1, col_player, col_esp2 = st.columns([1, 1.2, 1])
    with col_player:
        iframe_html = f"""
        <div style="display: flex; justify-content: center; align-items: center; margin: 10px 0;">
            <div style="width: 350px; height: 600px; border-radius: 24px; overflow: hidden; box-shadow: 0 10px 35px rgba(255, 75, 75, 0.3); border: 2.5px solid #ff4b4b; background: #000;">
                <iframe 
                    width="100%" 
                    height="100%" 
                    src="https://www.youtube.com/embed/{video_atual['id']}?autoplay=1&mute=0&controls=1&loop=1&playlist={video_atual['id']}&playsinline=1" 
                    title="Player TikTok Dorama" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                    allowfullscreen 
                    style="border: none;">
                </iframe>
            </div>
        </div>
        """
        st.components.v1.html(iframe_html, height=620)

    # BOTÕES DE NAVEGAÇÃO E AÇÃO
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1.8, 1])
    
    with col_nav1:
        if st.button("⏮️ Anterior", use_container_width=True):
            if st.session_state["feed_index"] > 0:
                st.session_state["feed_index"] -= 1
                st.rerun()

    with col_nav2:
        btn_cortar_feed = st.button("✂️ CORTAR ESTE VÍDEO AGORA", type="primary", use_container_width=True)
        if btn_cortar_feed:
            with st.spinner("A transferir vídeo e a configurar o editor..."):
                sucesso, c_out, leg = descarregar_video_motor(video_atual["url"], pasta_temp)
                if sucesso and os.path.exists(c_out) and tem_imagem_de_video(c_out):
                    st.session_state["video_original"] = c_out
                    st.session_state["texto_input_armazenado"] = leg or video_atual["title"]
                    st.session_state["preview_fixo"] = True
                    st.session_state["url_manual_importada"] = video_atual["url"]
                    st.session_state["nav_radio"] = "🎬 Editor de Cortes"
                    st.rerun()
                else:
                    st.warning("⚠️ Este vídeo possui proteção de reprodução na nuvem. Pressione 'Próximo ⏭️' para escolher outro ou cole um link do Kwai diretamente no Editor!")

    with col_nav3:
        if st.button("Próximo ⏭️", use_container_width=True):
            if st.session_state["feed_index"] < total_videos - 1:
                st.session_state["feed_index"] += 1
                st.rerun()

# ==============================================================================
# ABA 2: EDITOR DE CORTES
# ==============================================================================
elif aba_selecionada == "🎬 Editor de Cortes":
    col_topo_1, col_topo_2 = st.columns([1, 1])

    with col_topo_1:
        with st.container(border=True):
            st.markdown("### 📁 1. Arquivos de Identidade Visual")
            col_molde, col_fonte = st.columns(2)
            with col_molde:
                fundo_user = st.file_uploader("Molde / Layout (PNG/JPG)", type=["jpg", "jpeg", "png"])
            with col_fonte:
                fonte_user = st.file_uploader("Fonte (TTF)", type=["ttf", "otf"])

    with col_topo_2:
        with st.container(border=True):
            st.markdown("### 🔎 2. Importar Link Manual")
            url_sugerida = st.session_state.get("url_manual_importada", "")
            link_video = st.text_input("Cole o link (Kwai, TikTok, Insta ou Shorts):", value=url_sugerida)
            if st.button("📥 Analisar e Extrair Vídeo", use_container_width=True):
                if not link_video or not link_video.startswith("http"):
                    st.warning("⚠️ Insira um link válido.")
                else:
                    with st.spinner("A descarregar o vídeo..."):
                        sucesso, c_out, leg = descarregar_video_motor(link_video, pasta_temp)
                        if sucesso and tem_imagem_de_video(c_out):
                            st.session_state["video_original"] = c_out
                            st.session_state["texto_input_armazenado"] = leg or "ASSISTA ATÉ AO FIM"
                            st.session_state["preview_fixo"] = True
                            st.rerun()
                        else:
                            st.error("Não foi possível transferir este vídeo. Verifique se o link está acessível.")

    st.markdown("<br>", unsafe_allow_html=True)

    if "video_original" in st.session_state and os.path.exists(st.session_state["video_original"]):
        col_preview, col_editor = st.columns([1, 1.2])
        
        with col_preview:
            with st.container(border=True):
                st.markdown("#### 📺 Visualizador de Mídia")
                st.video(st.session_state["video_original"])

        with col_editor:
            with st.container(border=True):
                st.markdown("#### 🎛️ Painel de Personalização")
                
                valor_inicial = st.session_state.get("texto_input_armazenado", "ASSISTA ATÉ AO FIM")
                texto_final = st.text_input("Texto de Destaque no Topo:", value=valor_inicial, key="campo_texto_destaque")
                st.session_state["texto_input_armazenado"] = texto_final
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tamanho_fonte = st.slider("Tamanho da Fonte:", 30, 90, st.session_state.get("valor_tamanho_fonte", 65), 2, key="slider_tamanho_fonte")
                    st.session_state["valor_tamanho_fonte"] = tamanho_fonte
                with col_t2:
                    posicao_y = st.slider("Altura do Texto (Vertical):", 300, 700, st.session_state.get("valor_posicao_y", 500), 10, key="slider_posicao_y")
                    st.session_state["valor_posicao_y"] = posicao_y

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    opcoes_cor = {"Preto": "black", "Branco": "white", "Amarelo": "yellow"}
                    cor_nome = st.selectbox("Cor do Texto:", list(opcoes_cor.keys()), index=0)
                    cor_hex = opcoes_cor[cor_nome]
                with col_c2:
                    opcoes_borda = {"Sem Borda": 0, "Borda Fina": 3, "Borda Marcante": 5}
                    borda_nome = st.selectbox("Contorno / Borda:", list(opcoes_borda.keys()), index=0)
                    largura_borda = opcoes_borda[borda_nome]
                    cor_borda = "white" if cor_hex == "black" else "black"

                col_b1, col_b2 = st.columns([1.5, 1])
                with col_b1:
                    if st.button("👁️ Abrir / Fixar Imagem", use_container_width=True):
                        st.session_state["preview_fixo"] = True
                        st.rerun()
                with col_b2:
                    if st.button("❌ Ocultar Imagem", use_container_width=True):
                        st.session_state["preview_fixo"] = False
                        st.rerun()

                if st.session_state.get("preview_fixo", False):
                    if not fundo_user or not fonte_user:
                        st.info("ℹ️ Envie o Molde e a Fonte no Passo 1 para exibir a imagem de pré-visualização.")
                    else:
                        l1, l2 = quebrar_duas_linhas(texto_final)
                        caminho_molde_prev = os.path.join(pasta_temp, "molde_prev.jpg")
                        caminho_fonte_prev = os.path.join(pasta_temp, "fonte_prev.ttf")
                        caminho_saida_prev = os.path.join(pasta_temp, "preview_texto.jpg")
                        txt1_prev = os.path.join(pasta_temp, "l1_prev.txt")
                        txt2_prev = os.path.join(pasta_temp, "l2_prev.txt")

                        with open(caminho_molde_prev, "wb") as f: f.write(fundo_user.getbuffer())
                        with open(caminho_fonte_prev, "wb") as f: f.write(fonte_user.getbuffer())
                        with open(txt1_prev, "w", encoding="utf-8") as f: f.write(l1)
                        with open(txt2_prev, "w", encoding="utf-8") as f: f.write(l2)

                        espacamento = tamanho_fonte + 20
                        draw_l1 = f"drawtext=fontfile='{caminho_fonte_prev}':textfile='{txt1_prev}':fontsize={tamanho_fonte}:fontcolor={cor_hex}:borderw={largura_borda}:bordercolor={cor_borda}:x=(w-text_w)/2:y={posicao_y}"
                        draw_l2 = f"drawtext=fontfile='{caminho_fonte_prev}':textfile='{txt2_prev}':fontsize={tamanho_fonte}:fontcolor={cor_hex}:borderw={largura_borda}:bordercolor={cor_borda}:x=(w-text_w)/2:y={posicao_y}+{espacamento}"

                        filtro_prev = f"[0:v]scale=1080:1920[fundo];[fundo]{draw_l1},{draw_l2}[v]"
                        comando_prev = ["ffmpeg", "-y", "-i", caminho_molde_prev, "-filter_complex", filtro_prev, "-map", "[v]", "-frames:v", "1", "-update", "1", caminho_saida_prev]
                        subprocess.run(comando_prev, check=True)
                        st.image(caminho_saida_prev, caption=f"Altura: {posicao_y}px | Tamanho: {tamanho_fonte}px", use_container_width=True)

                st.markdown("<hr style='border-color: #30363d; margin: 20px 0;'>", unsafe_allow_html=True)
                
                modo_anti_copyright = st.checkbox("🛡️ Ativar Modo Anti-Copyright / Anti-Strike", value=True)
                duracao = st.selectbox("Duração Final do Vídeo:", ["30s", "50s", "60s", "Vídeo Completo"])
                st.markdown("<br>", unsafe_allow_html=True)
                
                btn_gerar = st.button("🚀 INICIAR RENDERIZAÇÃO FINAL", type="primary", use_container_width=True)

                if btn_gerar:
                    if not fundo_user or not fonte_user:
                        st.error("⚠️ Envie o Molde e a Fonte no Passo 1 antes de renderizar.")
                    else:
                        with st.status("🎬 A renderizar o corte...", expanded=True) as status:
                            st.write("📥 A preparar os ficheiros base...")
                            l1, l2 = quebrar_duas_linhas(texto_final)
                            caminho_molde = os.path.join(pasta_temp, "molde.jpg")
                            caminho_fonte = os.path.join(pasta_temp, "fonte.ttf")
                            caminho_saida = os.path.join(pasta_temp, "resultado.mp4")
                            txt1_path = os.path.join(pasta_temp, "l1.txt")
                            txt2_path = os.path.join(pasta_temp, "l2.txt")

                            with open(caminho_molde, "wb") as f: f.write(fundo_user.getbuffer())
                            with open(caminho_fonte, "wb") as f: f.write(fonte_user.getbuffer())
                            with open(txt1_path, "w", encoding="utf-8") as f: f.write(l1)
                            with open(txt2_path, "w", encoding="utf-8") as f: f.write(l2)

                            espacamento = tamanho_fonte + 20
                            draw_l1 = f"drawtext=fontfile='{caminho_fonte}':textfile='{txt1_path}':fontsize={tamanho_fonte}:fontcolor={cor_hex}:borderw={largura_borda}:bordercolor={cor_borda}:x=(w-text_w)/2:y={posicao_y}"
                            draw_l2 = f"drawtext=fontfile='{caminho_fonte}':textfile='{txt2_path}':fontsize={tamanho_fonte}:fontcolor={cor_hex}:borderw={largura_borda}:bordercolor={cor_borda}:x=(w-text_w)/2:y={posicao_y}+{espacamento}"

                            filtro_video = "[1:v]crop=in_w:in_w*9/16:0:(in_h-in_w*9/16)/2,scale=1080:608,setpts=PTS/1.03[vid];" if modo_anti_copyright else "[1:v]crop=in_w:in_w*9/16:0:(in_h-in_w*9/16)/2,scale=1080:608[vid];"

                            tem_som = tem_audio(st.session_state["video_original"])
                            if modo_anti_copyright and tem_som:
                                filtro_audio = "[1:a]atempo=1.03[a];"
                                mapa_audio = ["[a]"]
                            elif tem_som:
                                filtro_audio = ""
                                mapa_audio = ["1:a?"]
                            else:
                                filtro_audio = ""
                                mapa_audio = []

                            filtro_completo = f"[0:v]scale=1080:1920[fundo];{filtro_video}{filtro_audio}[fundo][vid]overlay=0:(H-h)/2[base];[base]{draw_l1},{draw_l2}[v]"

                            comando = ["ffmpeg", "-y", "-i", caminho_molde, "-i", st.session_state["video_original"], "-filter_complex", filtro_completo, "-map", "[v]"]
                            if mapa_audio:
                                comando.extend(["-map", mapa_audio[0], "-c:a", "aac"])
                            comando.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])

                            mapa_dur = {"30s": "30", "50s": "50", "60s": "60"}
                            if duracao in mapa_dur:
                                comando.extend(["-t", mapa_dur[duracao]])
                            comando.append(caminho_saida)

                            subprocess.run(comando, check=True)
                            status.update(label="✅ Renderização concluída com sucesso!", state="complete", expanded=False)

                        with open(caminho_saida, "rb") as f_video:
                            st.success("O seu vídeo está pronto!")
                            st.download_button(
                                label="⬇️ BAIXAR VÍDEO PRONTO", 
                                data=f_video.read(), 
                                file_name="corte_final.mp4", 
                                mime="video/mp4", 
                                use_container_width=True,
                                key="btn_download_video_final"
                            )
