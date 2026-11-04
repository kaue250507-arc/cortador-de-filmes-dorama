import os
import re
import json
import uuid
import html
import random
import urllib.request
import urllib.parse
import subprocess
import glob
import streamlit as st

st.set_page_config(
    page_title="Studio Filmes/Dorama", 
    page_icon="🎬", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# DESIGN SYSTEM: VISUAL PROFISSIONAL (SEM CARA DE IA)
# ==============================================================================
st.markdown("""
<html lang="pt" translate="no">
<head>
    <meta name="google" content="notranslate" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
</head>
</html>
<style>
    #MainMenu, header, footer, .stDeployButton { display: none !important; visibility: hidden !important; }
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    .stApp {
        background: radial-gradient(circle at 50% -10%, #1a1025 0%, #0c0f17 55%, #06080d 100%) !important;
        color: #f1f5f9 !important;
    }

    div[data-testid="stContainer"] {
        background: rgba(18, 23, 33, 0.75) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.4) !important;
        padding: 22px !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease;
    }
    div[data-testid="stContainer"]:hover {
        border-color: rgba(255, 51, 102, 0.3) !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5) !important;
    }

    h3, h4 {
        color: #ffffff !important;
        font-weight: 800 !important;
        letter-spacing: -0.4px !important;
    }
    label {
        color: #94a3b8 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, #ff3366 0%, #ff1f44 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
        letter-spacing: 0.5px !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 24px !important;
        box-shadow: 0 4px 20px rgba(255, 31, 68, 0.35) !important;
        transition: all 0.25s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 6px 28px rgba(255, 31, 68, 0.6) !important;
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0b0e14 !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        font-size: 0.95rem !important;
    }
    .stTextInput input:focus {
        border-color: #ff3366 !important;
        box-shadow: 0 0 0 2px rgba(255, 51, 102, 0.25) !important;
    }

    div[data-baseweb="slider"] div {
        background-color: #ff3366 !important;
    }

    video, img {
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
    }

    hr {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO E PROCESSAMENTO
# ==============================================================================
def limpar_texto_legenda(texto):
    if not texto:
        return ""

    if re.match(r'^(?:video|post)\s+by\s+', texto, re.IGNORECASE):
        return ""

    t = html.unescape(texto)

    if any(w in t.lower() for w in ["likes", "curtidas", "comments", "comentários", "video from"]):
        m_aspas = re.search(r'["“]([^"”]{5,})["”]', t)
        if m_aspas:
            t = m_aspas.group(1)
        else:
            m_resto = re.search(r':\s*["\']?(.*)', t)
            if m_resto:
                t = m_resto.group(1)

    linhas = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith(('#', '@', '.', '-'))]
    if linhas:
        t = linhas[0]

    t = re.sub(r'#\S+', '', t)
    t = re.sub(r'@\S+', '', t)
    t = re.sub(r'https?://\S+', '', t)
    t = t.strip(' "\'“”-–:()[]{}')
    t = re.sub(r'\s+', ' ', t).strip()

    if re.match(r'^(?:video|post)\s+by\s+', t, re.IGNORECASE):
        return ""

    return t

def resolver_url_video_real(url_alvo):
    url_limpa = url_alvo.strip()
    titulo_extraido = ""

    if ".mp4" in url_limpa.split("?")[0] and not any(p in url_limpa for p in ["instagram.com", "tiktok.com", "kwai.com"]):
        return url_limpa, "Cena Viral de Dorama"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9'
    }

    # 1. INSTAGRAM REELS
    if "instagram.com" in url_limpa:
        try:
            url_embed = re.sub(r'\?.*$', '', url_limpa).rstrip('/') + "/embed/captioned/"
            req = urllib.request.Request(url_embed, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html_ig = resp.read().decode('utf-8', errors='ignore')

            m_caption = re.search(r'class=["\']Caption["\'][^>]*>([\s\S]*?)<\/div>', html_ig)
            if m_caption:
                texto_sem_user = re.sub(r'<a[^>]*class=["\']CaptionUsername["\'][^>]*>[\s\S]*?<\/a>', '', m_caption.group(1))
                texto_puro = re.sub(r'<[^>]+>', '', texto_sem_user)
                candidato = limpar_texto_legenda(texto_puro)
                if candidato:
                    titulo_extraido = candidato

            if not titulo_extraido:
                m_og = re.search(r'<meta[^>]+(?:property|name)=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html_ig)
                if m_og:
                    candidato = limpar_texto_legenda(m_og.group(1))
                    if candidato:
                        titulo_extraido = candidato

            m_mp4 = re.search(r'video_url["\']\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']', html_ig) or \
                    re.search(r'src=["\'](https:\/\/[^"\']+\.mp4[^"\']*)["\']', html_ig)
            if m_mp4:
                stream_mp4 = m_mp4.group(1).replace(r'\u0026', '&').replace(r'\/', '/')
                return stream_mp4, (titulo_extraido or "ASSISTA ATÉ AO FIM")
        except Exception:
            pass

    # 2. TIKTOK
    if "tiktok.com" in url_limpa:
        try:
            api_url = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url_limpa)}"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                dados = json.loads(resp.read().decode('utf-8'))
                if dados.get("code") == 0 and dados.get("data"):
                    play_url = dados["data"].get("play") or dados["data"].get("wmplay")
                    if dados["data"].get("title"):
                        candidato = limpar_texto_legenda(dados["data"]["title"])
                        if candidato:
                            titulo_extraido = candidato
                    if play_url:
                        return play_url, (titulo_extraido or "ASSISTA ATÉ AO FIM")
        except Exception:
            pass

    # 3. KWAI
    if any(k in url_limpa for k in ["kwai.com", "kwai-video.com", "k.kwai.com"]):
        try:
            req = urllib.request.Request(url_limpa, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html_raw = resp.read().decode('utf-8', errors='ignore')

            m_cap = re.search(r'"caption"\s*:\s*"((?:\\.|[^"\\])+)"', html_raw)
            if m_cap:
                try:
                    candidato = limpar_texto_legenda(json.loads('"' + m_cap.group(1) + '"'))
                except Exception:
                    candidato = limpar_texto_legenda(m_cap.group(1))
                if candidato:
                    titulo_extraido = candidato

            if not titulo_extraido:
                m_tit = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', html_raw, re.IGNORECASE)
                if m_tit and m_tit.group(1):
                    candidato = limpar_texto_legenda(m_tit.group(1))
                    if candidato:
                        titulo_extraido = candidato

            matches = re.findall(r'https://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html_raw.replace(r'\/', '/'))
            for m in matches:
                if "kwai" in m or "cdn" in m:
                    return m, (titulo_extraido or "ASSISTA ATÉ AO FIM")
            if matches:
                return matches[0], (titulo_extraido or "ASSISTA ATÉ AO FIM")
        except Exception:
            pass

    # 4. Fallback com yt-dlp
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best[ext=mp4]/best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_limpa, download=False)
            if info.get('description'):
                cand = limpar_texto_legenda(info.get('description'))
                if cand:
                    titulo_extraido = cand

            if not titulo_extraido and info.get('title'):
                cand = limpar_texto_legenda(info.get('title'))
                if cand:
                    titulo_extraido = cand

            if info.get('url'):
                return info['url'], (titulo_extraido or "ASSISTA ATÉ AO FIM")
    except Exception:
        pass

    return url_limpa, (titulo_extraido or "ASSISTA ATÉ AO FIM")

def tem_imagem_de_video(caminho_arquivo):
    if not os.path.exists(caminho_arquivo) or os.path.getsize(caminho_arquivo) < 5000:
        return False
    try:
        with open(caminho_arquivo, "rb") as f:
            cabecalho = f.read(256)
            if b"<!DOCTYPE" in cabecalho or b"<html" in cabecalho or b"<head" in cabecalho:
                return False
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

def baixar_video_com_extracao(url_alvo, pasta_destino):
    caminho_saida = os.path.join(pasta_destino, "preview.mp4")
    for f in glob.glob(os.path.join(pasta_destino, "preview*")):
        try: os.remove(f)
        except Exception: pass

    url_stream, titulo_detectado = resolver_url_video_real(url_alvo)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }

    sucesso = False
    try:
        req = urllib.request.Request(url_stream, headers=headers)
        with urllib.request.urlopen(req, timeout=35) as v_stream, open(caminho_saida, "wb") as f_out:
            f_out.write(v_stream.read())
        sucesso = True
    except Exception:
        try:
            urllib.request.urlretrieve(url_stream, caminho_saida)
            sucesso = True
        except Exception:
            sucesso = False

    if not sucesso or not tem_imagem_de_video(caminho_saida):
        try:
            cmd = ["yt-dlp", "-f", "best[ext=mp4]/best", "-o", caminho_saida, url_alvo, "--force-overwrites"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
            if tem_imagem_de_video(caminho_saida):
                sucesso = True
        except Exception:
            pass

    if os.path.exists(caminho_saida) and not tem_imagem_de_video(caminho_saida):
        try: os.remove(caminho_saida)
        except Exception: pass
        return False, None, ""

    return sucesso, caminho_saida, titulo_detectado

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

# ==============================================================================
# SESSÃO E PASTAS TEMPORÁRIAS
# ==============================================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

# Título Principal
st.markdown('<div style="text-align:center; font-size: 2.6rem; font-weight: 900; background: linear-gradient(90deg, #ff3366, #ff7676, #ff3366); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-top: 10px;">🎬 Studio Filmes/Dorama</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color: #94a3b8; font-size: 1rem; margin-bottom: 30px;">Editor de Cortes Virais para TikTok, Kwai e Reels</div>', unsafe_allow_html=True)

# ==============================================================================
# BANCADA DE IMPORTAÇÃO E IDENTIDADE VISUAL
# ==============================================================================
col_topo_1, col_topo_2 = st.columns([1, 1])

with col_topo_1:
    with st.container(border=True):
        st.markdown("### 📁 1. Arquivos de Identidade Visual")
        col_molde, col_fonte = st.columns(2)
        with col_molde:
            fundo_user = st.file_uploader("Molde / Moldura (PNG/JPG)", type=["jpg", "jpeg", "png"])
        with col_fonte:
            fonte_user = st.file_uploader("Fonte (TTF)", type=["ttf", "otf"])

with col_topo_2:
    with st.container(border=True):
        st.markdown("### 🔎 2. Importar Vídeo")
        link_avulso = st.text_input("Cole qualquer link (Instagram Reels, TikTok, Kwai ou MP4):")
        if st.button("📥 Carregar Vídeo", use_container_width=True):
            if not link_avulso or not link_avulso.startswith("http"):
                st.warning("⚠️ Insira um link válido iniciado por http ou https.")
            else:
                with st.spinner("A extrair vídeo original da plataforma..."):
                    sucesso, caminho_vid, tit_detectado = baixar_video_com_extracao(link_avulso, pasta_temp)
                    if sucesso and tem_imagem_de_video(caminho_vid):
                        st.session_state["video_original"] = caminho_vid
                        if tit_detectado and len(tit_detectado) > 3:
                            st.session_state["texto_input_armazenado"] = tit_detectado
                        else:
                            st.session_state["texto_input_armazenado"] = "ASSISTA ATÉ AO FIM"
                        st.session_state["preview_fixo"] = True
                        st.success("✅ Vídeo extraído com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível extrair o vídeo deste link.")

st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# PAINEL DE PERSONALIZAÇÃO E EXPORTAÇÃO
# ==============================================================================
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
            texto_final = st.text_input("Texto de Destaque no Topo:", value=valor_inicial)
            st.session_state["texto_input_armazenado"] = texto_final

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tamanho_fonte = st.slider("Tamanho da Fonte:", 30, 90, 65, 2)
            with col_t2:
                posicao_y = st.slider("Altura do Texto (Vertical):", 300, 700, 500, 10)

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

            if fundo_user and fonte_user:
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
                st.image(caminho_saida_prev, caption="Pré-visualização do layout", use_container_width=True)

            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

            modo_anti_copyright = st.checkbox("🛡️ Ativar Modo Anti-Copyright / Anti-Strike", value=True)
            duracao = st.selectbox("Duração Final do Vídeo:", ["30s", "50s", "60s", "120s", "150s", "Vídeo Completo"])
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

            btn_gerar = st.button("🚀 INICIAR RENDERIZAÇÃO FINAL", type="primary", use_container_width=True)

            if btn_gerar:
                if not fundo_user or not fonte_user:
                    st.error("⚠️ Envie o Molde e a Fonte no Passo 1 antes de renderizar.")
                else:
                    with st.status("🎬 A renderizar o corte...", expanded=True) as status:
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

                        mapa_dur = {"30s": "30", "50s": "50", "60s": "60", "120s": "120", "150s": "150"}
                        if duracao in mapa_dur:
                            comando.extend(["-t", mapa_dur[duracao]])
                        comando.append(caminho_saida)

                        subprocess.run(comando, check=True)
                        status.update(label="✅ Renderização concluída com sucesso!", state="complete", expanded=False)

                    with open(caminho_saida, "rb") as f_video:
                        st.success("O corte está pronto!")
                        st.download_button(
                            label="⬇️ BAIXAR VÍDEO PRONTO", 
                            data=f_video.read(), 
                            file_name="corte_final.mp4", 
                            mime="video/mp4", 
                            use_container_width=True
                        )
