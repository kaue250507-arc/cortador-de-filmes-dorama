import os
import re
import json
import uuid
import html
import subprocess
import glob
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

st.set_page_config(
    page_title="Studio Filmes/Dorama", 
    page_icon="🎬", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# DESIGN SYSTEM: OTIMIZADO PARA MOBILE E DESKTOP
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
        border-radius: 16px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
        padding: 18px !important;
        margin-bottom: 12px !important;
    }

    @media (max-width: 768px) {
        div[data-testid="stContainer"] {
            padding: 12px !important;
            border-radius: 14px !important;
        }
        h3 { font-size: 1.25rem !important; }
        h4 { font-size: 1.05rem !important; }
    }

    h3, h4 {
        color: #ffffff !important;
        font-weight: 800 !important;
        letter-spacing: -0.4px !important;
    }
    label {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, #ff3366 0%, #ff1f44 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.5px !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
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

    div[data-baseweb="slider"] div {
        background-color: #ff3366 !important;
    }

    video, img {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important;
    }

    hr { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# ALGORITMO DE DETECÇÃO INTELIGENTE DE CORTES (OPENCV)
# ==============================================================================
def detectar_crop_inteligente(caminho_video):
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        return 0, 0, 1080, 1920, None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    indices = [
        int(total_frames * 0.15),
        int(total_frames * 0.35),
        int(total_frames * 0.55),
        int(total_frames * 0.75)
    ]
    
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, max(0, total_frames - 5)))
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()

    if len(frames) < 2:
        return 0, 0, width, height, frames[0] if frames else None

    diff_acumulada = np.zeros((height, width), dtype=np.uint8)
    base_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

    for f in frames[1:]:
        f_gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        d = cv2.absdiff(base_gray, f_gray)
        diff_acumulada = np.maximum(diff_acumulada, d)

    blurred = cv2.GaussianBlur(diff_acumulada, (9, 9), 0)
    _, thresh = cv2.threshold(blurred, 18, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
    mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        maior = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(maior)

        if w * h > (width * height * 0.12):
            if w > width * 0.85:
                x = 0
                w = width
            return x, y, w, h, frames[0]

    h_padrao = int(width * 9 / 16)
    y_padrao = max(0, (height - h_padrao) // 2)
    return 0, y_padrao, width, h_padrao, frames[0]

# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO, DOWNLOAD RÁPIDO E PROCESSAMENTO
# ==============================================================================
def limpar_texto_legenda(texto):
    if not texto: return ""
    if re.match(r'^(?:video|post)\s+by\s+', texto, re.IGNORECASE): return ""
    t = html.unescape(texto)
    if any(w in t.lower() for w in ["likes", "curtidas", "comments", "comentários", "video from"]):
        m_aspas = re.search(r'["“]([^"”]{5,})["”]', t)
        if m_aspas: t = m_aspas.group(1)
        else:
            m_resto = re.search(r':\s*["\']?(.*)', t)
            if m_resto: t = m_resto.group(1)
    linhas = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith(('#', '@', '.', '-'))]
    if linhas: t = linhas[0]
    t = re.sub(r'#\S+', '', t)
    t = re.sub(r'@\S+', '', t)
    t = re.sub(r'https?://\S+', '', t)
    t = t.strip(' "\'“”-–:()[]{}')
    t = re.sub(r'\s+', ' ', t).strip()
    return "" if re.match(r'^(?:video|post)\s+by\s+', t, re.IGNORECASE) else t

def tem_imagem_de_video(caminho_arquivo):
    if not os.path.exists(caminho_arquivo) or os.path.getsize(caminho_arquivo) < 5000: return False
    try:
        res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", caminho_arquivo], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "video" in res.stdout.lower()
    except: return True

def tem_audio(caminho_arquivo):
    try:
        res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", caminho_arquivo], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return "audio" in res.stdout.lower()
    except: return True

def baixar_video_com_extracao(url_alvo, pasta_destino):
    caminho_saida = os.path.join(pasta_destino, "video_base.mp4")
    url_limpa = url_alvo.strip()
    titulo_detectado = ""

    # 1. TIKTOK DIRETO (API instantânea em menos de 2s)
    if "tiktok.com" in url_limpa:
        try:
            import urllib.request
            import urllib.parse
            api_url = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url_limpa)}"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                dados = json.loads(resp.read().decode('utf-8'))
                if dados.get("code") == 0 and dados.get("data"):
                    if dados["data"].get("title"):
                        titulo_detectado = limpar_texto_legenda(dados["data"]["title"])
                    play_url = dados["data"].get("play") or dados["data"].get("wmplay")
                    if play_url:
                        req_v = urllib.request.Request(play_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_v, timeout=20) as r, open(caminho_saida, 'wb') as f:
                            while chunk := r.read(64 * 1024):
                                f.write(chunk)
                        if tem_imagem_de_video(caminho_saida):
                            return True, caminho_saida, (titulo_detectado or "ASSISTA ATÉ AO FIM")
        except:
            pass

    # 2. INSTAGRAM, KWAI, SHORTS E OUTROS (yt-dlp direto e sem gargalos)
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-warnings",
        "-f", "best[ext=mp4]/best",
        "-o", caminho_saida,
        "--force-overwrites",
        "--socket-timeout", "12",
        "--print", "title",
        url_limpa
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=35)
        if res.stdout:
            titulo_detectado = limpar_texto_legenda(res.stdout.splitlines()[0])
        if tem_imagem_de_video(caminho_saida):
            return True, caminho_saida, (titulo_detectado or "ASSISTA ATÉ AO FIM")
    except:
        pass

    return False, None, ""

def quebrar_duas_linhas(frase):
    palavras = frase.split()
    if not palavras: return "ASSISTA ATÉ AO FIM", "MOMENTO SURPREENDENTE"
    if len(palavras) <= 3: return frase, ""
    melhor_corte = max(1, len(palavras) // 2)
    menor_dif = float('inf')
    for i in range(1, len(palavras)):
        l1, l2 = " ".join(palavras[:i]), " ".join(palavras[i:])
        dif = abs(len(l1) - len(l2))
        if dif < menor_dif:
            menor_dif, melhor_corte = dif, i
    return " ".join(palavras[:melhor_corte]), " ".join(palavras[melhor_corte:])

# ==============================================================================
# SUPORTE NATIVO A EMOJIS SEM DEPENDER DE DRAWTEXT
# ==============================================================================
def is_emoji_codepoint(cp):
    return (
        0x1F600 <= cp <= 0x1F64F or 0x1F300 <= cp <= 0x1F5FF or
        0x1F680 <= cp <= 0x1F6FF or 0x1F1E0 <= cp <= 0x1F1FF or
        0x2600 <= cp <= 0x26FF   or 0x2700 <= cp <= 0x27BF   or
        0xFE00 <= cp <= 0xFE0F   or 0x1F900 <= cp <= 0x1F9FF or
        0x1FA70 <= cp <= 0x1FAFF
    )

def separar_texto_e_emojis(texto):
    partes = []
    atual = ""
    for ch in texto:
        if is_emoji_codepoint(ord(ch)):
            if atual:
                partes.append(('texto', atual))
                atual = ""
            partes.append(('emoji', ch))
        else:
            atual += ch
    if atual:
        partes.append(('texto', atual))
    return partes

def calcular_largura_linha(draw, linha, font, tamanho_fonte, borda):
    w = 0
    for tipo, val in separar_texto_e_emojis(linha):
        if tipo == 'texto':
            bbox = draw.textbbox((0, 0), val, font=font, stroke_width=borda)
            w += (bbox[2] - bbox[0])
        else:
            w += tamanho_fonte + 6
    return w

def criar_overlay_titulo_emojis(texto, tamanho_fonte, posicao_y, cor_nome, borda_largura, caminho_fonte, caminho_saida_png):
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(caminho_fonte, tamanho_fonte)
    except Exception:
        font = ImageFont.load_default()

    # Tenta carregar a fonte de emojis nativa do sistema operacional
    emoji_font = None
    caminhos_emoji_sistema = [
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/NotoColorEmoji.ttf",
        "/system/fonts/NotoColorEmoji.ttf",
        "C:\\Windows\\Fonts\\seguiemj.ttf"
    ]
    for c in caminhos_emoji_sistema:
        if os.path.exists(c):
            try:
                emoji_font = ImageFont.truetype(c, 109)
                break
            except Exception:
                pass

    mapa_cores = {"Preto": (0, 0, 0, 255), "Branco": (255, 255, 255, 255), "Amarelo": (255, 220, 0, 255)}
    cor_fill = mapa_cores.get(cor_nome, (0, 0, 0, 255))
    cor_stroke = (255, 255, 255, 255) if cor_nome == "Preto" else (0, 0, 0, 255)

    l1, l2 = quebrar_duas_linhas(texto)
    linhas = [l for l in [l1, l2] if l]
    espacamento = int(tamanho_fonte * 1.25)

    for idx, linha in enumerate(linhas):
        largura_total = calcular_largura_linha(draw, linha, font, tamanho_fonte, borda_largura)
        cur_x = (1080 - largura_total) // 2
        cur_y = posicao_y + (idx * espacamento)

        for tipo, val in separar_texto_e_emojis(linha):
            if tipo == 'texto':
                bbox = draw.textbbox((cur_x, cur_y), val, font=font, stroke_width=borda_largura)
                draw.text(
                    (cur_x, cur_y), val, font=font, fill=cor_fill,
                    stroke_width=borda_largura, stroke_fill=cor_stroke if borda_largura > 0 else None
                )
                cur_x += (bbox[2] - bbox[0])
            else:
                if emoji_font:
                    em_canvas = Image.new("RGBA", (130, 130), (0, 0, 0, 0))
                    em_draw = ImageDraw.Draw(em_canvas)
                    em_draw.text((10, 10), val, font=emoji_font, embedded_color=True)
                    em_resized = em_canvas.resize((tamanho_fonte, tamanho_fonte), Image.Resampling.LANCZOS)
                    img.alpha_composite(em_resized, (int(cur_x), int(cur_y)))
                    cur_x += tamanho_fonte + 6
                else:
                    cur_x += tamanho_fonte + 6

    img.save(caminho_saida_png, "PNG")
    return caminho_saida_png

# ==============================================================================
# SESSÃO E ARMAZENAMENTO PERSISTENTE (NÃO SOME NO CELULAR)
# ==============================================================================
PASTA_STORAGE = os.path.abspath("storage_app")
os.makedirs(PASTA_STORAGE, exist_ok=True)

MOLDE_PERSISTENTE = os.path.join(PASTA_STORAGE, "molde_salvo.png")
FONTE_PERSISTENTE = os.path.join(PASTA_STORAGE, "fonte_salva.ttf")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

st.markdown('<div style="text-align:center; font-size: 2.3rem; font-weight: 900; background: linear-gradient(90deg, #ff3366, #ff7676, #ff3366); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-top: 10px;">🎬 Studio Filmes/Dorama</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color: #94a3b8; font-size: 0.95rem; margin-bottom: 25px;">Editor Inteligente: Enquadramento e Corte Automático</div>', unsafe_allow_html=True)

# ==============================================================================
# 1. IDENTIDADE VISUAL E IMPORTAÇÃO
# ==============================================================================
col_topo_1, col_topo_2 = st.columns([1, 1])

with col_topo_1:
    with st.container(border=True):
        st.markdown("### 📁 1. Identidade Visual")
        molde_ja_existe = os.path.exists(MOLDE_PERSISTENTE)
        fonte_ja_existe = os.path.exists(FONTE_PERSISTENTE)

        st.caption(f"Status no Celular: Molde {'✅ Ativo' if molde_ja_existe else '⚠️ Envie uma vez'} | Fonte {'✅ Ativa' if fonte_ja_existe else '⚠️ Envie uma vez'}")
        
        col_molde, col_fonte = st.columns(2)
        with col_molde:
            fundo_user = st.file_uploader("Molde Rosa (PNG/JPG)", type=["jpg", "jpeg", "png"])
            if fundo_user:
                with open(MOLDE_PERSISTENTE, "wb") as f: f.write(fundo_user.getbuffer())
                st.success("Molde gravado com sucesso!")
        with col_fonte:
            fonte_user = st.file_uploader("Fonte (TTF/OTF)", type=["ttf", "otf"])
            if fonte_user:
                with open(FONTE_PERSISTENTE, "wb") as f: f.write(fonte_user.getbuffer())
                st.success("Fonte gravada com sucesso!")

with col_topo_2:
    with st.container(border=True):
        st.markdown("### 🔎 2. Importar Vídeo")
        link_avulso = st.text_input("Cole o link (Reels, TikTok, Kwai ou MP4):")
        if st.button("📥 Carregar Vídeo", use_container_width=True):
            if not link_avulso or not link_avulso.startswith("http"):
                st.warning("⚠️ Insira um link válido iniciado por http ou https.")
            else:
                with st.spinner("Baixando em alta velocidade e calculando corte com IA..."):
                    sucesso, caminho_vid, tit_detectado = baixar_video_com_extracao(link_avulso, pasta_temp)
                    if sucesso and tem_imagem_de_video(caminho_vid):
                        st.session_state["video_original"] = caminho_vid
                        st.session_state["texto_input_armazenado"] = tit_detectado if tit_detectado else "ASSISTA ATÉ AO FIM"
                        
                        x, y, w, h, frame_ref = detectar_crop_inteligente(caminho_vid)
                        st.session_state["crop_x"], st.session_state["crop_y"] = x, y
                        st.session_state["crop_w"], st.session_state["crop_h"] = w, h
                        
                        if frame_ref is not None:
                            st.session_state["orig_h"], st.session_state["orig_w"] = frame_ref.shape[:2]

                        st.success("✅ Vídeo cortado e inserido no molde automaticamente!")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível carregar este vídeo.")

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 2. EDITOR INTEGRADO (VÍDEO JÁ INSERIDO NO MOLDE)
# ==============================================================================
if "video_original" in st.session_state and os.path.exists(st.session_state["video_original"]):
    orig_w = st.session_state.get("orig_w", 1080)
    orig_h = st.session_state.get("orig_h", 1920)

    init_top = int(st.session_state.get("crop_y", 0))
    init_h = int(st.session_state.get("crop_h", orig_h))
    init_bottom = max(0, int(orig_h - (init_top + init_h)))
    init_left = int(st.session_state.get("crop_x", 0))
    init_w = int(st.session_state.get("crop_w", orig_w))
    init_right = max(0, int(orig_w - (init_left + init_w)))

    col_preview, col_editor = st.columns([1, 1.2])
    
    with col_preview:
        with st.container(border=True):
            st.markdown("#### 📺 Vídeo Original Baixado")
            st.video(st.session_state["video_original"])

    with col_editor:
        with st.container(border=True):
            st.markdown("#### 🎛️ Configuração do Título e Posição")
            
            valor_inicial = st.session_state.get("texto_input_armazenado", "ASSISTA ATÉ AO FIM")
            texto_final = st.text_input("Texto de Destaque no Topo:", value=valor_inicial)
            st.session_state["texto_input_armazenado"] = texto_final

            col_t1, col_t2 = st.columns(2)
            with col_t1: tamanho_fonte = st.slider("Tamanho da Fonte:", 30, 90, 65, 2)
            with col_t2: posicao_y = st.slider("Altura do Texto (Vertical):", 150, 700, 320, 10)

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                opcoes_cor = {"Preto": "black", "Branco": "white", "Amarelo": "yellow"}
                cor_nome = st.selectbox("Cor do Texto:", list(opcoes_cor.keys()), index=0)
            with col_c2:
                opcoes_borda = {"Sem Borda": 0, "Borda Fina": 3, "Borda Marcante": 5}
                borda_nome = st.selectbox("Contorno / Borda:", list(opcoes_borda.keys()), index=0)
                largura_borda = opcoes_borda[borda_nome]

            with st.expander("✂️ Ajustar Corte Manualmente (Opcional - Script já cortou sozinho)", expanded=False):
                st.write("A IA já calculou o melhor enquadramento. Se ainda sobrar algum pedaço indesejado, ajuste abaixo:")
                corte_topo = st.slider("✂️ Cortar do Topo (pixels):", 0, int(orig_h * 0.7), min(init_top, int(orig_h * 0.7)), step=2)
                corte_base = st.slider("✂️ Cortar da Base (pixels):", 0, int(orig_h * 0.7), min(init_bottom, int(orig_h * 0.7)), step=2)
                
                col_l1, col_l2 = st.columns(2)
                with col_l1: corte_esq = st.slider("Cortar Esquerda:", 0, int(orig_w * 0.4), min(init_left, int(orig_w * 0.4)), step=2)
                with col_l2: corte_dir = st.slider("Cortar Direita:", 0, int(orig_w * 0.4), min(init_right, int(orig_w * 0.4)), step=2)

                pos_y_video = st.slider("📍 Altura do Vídeo na Moldura:", 350, 1000, 640, 10, help="Onde o vídeo começa abaixo de 'Sinopse'")

                if st.button("🔄 Recalcular Corte com IA"):
                    x, y, w, h, _ = detectar_crop_inteligente(st.session_state["video_original"])
                    st.session_state["crop_x"], st.session_state["crop_y"] = x, y
                    st.session_state["crop_w"], st.session_state["crop_h"] = w, h
                    st.rerun()
            
            if 'corte_topo' not in locals():
                corte_topo, corte_base = init_top, init_bottom
                corte_esq, corte_dir = init_left, init_right
                pos_y_video = 640

            final_x = corte_esq if corte_esq % 2 == 0 else corte_esq - 1
            final_y = corte_topo if corte_topo % 2 == 0 else corte_topo - 1
            final_w = max(100, orig_w - corte_esq - corte_dir)
            final_h = max(100, orig_h - corte_topo - corte_base)
            if final_w % 2 != 0: final_w -= 1
            if final_h % 2 != 0: final_h -= 1

            # ==================================================================
            # PRÉ-VISUALIZAÇÃO COMPLETA: VÍDEO NO MOLDE COM EMOJIS EM TEMPO REAL
            # ==================================================================
            molde_ativo = MOLDE_PERSISTENTE if os.path.exists(MOLDE_PERSISTENTE) else None
            fonte_ativa = FONTE_PERSISTENTE if os.path.exists(FONTE_PERSISTENTE) else None

            if molde_ativo and fonte_ativa:
                caminho_saida_prev = os.path.join(pasta_temp, "preview_completo.mp4")
                caminho_overlay_prev = os.path.join(pasta_temp, "overlay_prev.png")

                # Cria o overlay do texto com suporte a emojis
                criar_overlay_titulo_emojis(
                    texto_final, tamanho_fonte, posicao_y, cor_nome, largura_borda,
                    fonte_ativa, caminho_overlay_prev
                )

                filtro_prev = (
                    f"[1:v]scale=1080:1920[fundo];"
                    f"[0:v]crop={final_w}:{final_h}:{final_x}:{final_y},scale=1080:-2[vid];"
                    f"[fundo][vid]overlay=(W-w)/2:{pos_y_video}[base];"
                    f"[base][2:v]overlay=0:0[v]"
                )
                
                tem_som = tem_audio(st.session_state["video_original"])
                mapa_audio_prev = ["0:a?"] if tem_som else []
                
                comando_prev = [
                    "ffmpeg", "-y",
                    "-i", st.session_state["video_original"],
                    "-i", molde_ativo,
                    "-i", caminho_overlay_prev,
                    "-filter_complex", filtro_prev,
                    "-map", "[v]"
                ]
                if mapa_audio_prev:
                    comando_prev.extend(["-map", mapa_audio_prev[0], "-c:a", "aac"])
                
                comando_prev.extend([
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-t", "6",  # Renderiza um trecho curto de 6s instantaneamente
                    caminho_saida_prev
                ])
                
                try:
                    subprocess.run(comando_prev, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    if os.path.exists(caminho_saida_prev) and os.path.getsize(caminho_saida_prev) > 1000:
                        st.markdown("#### ✨ Prévia do Vídeo no Molde:")
                        st.video(caminho_saida_prev)
                except Exception:
                    pass
            else:
                st.info("💡 Envie o Molde e a Fonte no Passo 1 para ver o vídeo montado na moldura.")

            # ==================================================================
            # EXPORTAÇÃO
            # ==================================================================
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1: modo_anti_copyright = st.checkbox("🛡️ Modo Anti-Copyright (+3% de Velocidade)", value=True)
            with col_cfg2: duracao = st.selectbox("Duração do Vídeo:", ["30s", "50s", "60s", "120s", "150s", "Vídeo Completo"])

            btn_gerar = st.button("🚀 INICIAR RENDERIZAÇÃO FINAL", type="primary", use_container_width=True)

            if btn_gerar:
                if not molde_ativo or not fonte_ativa:
                    st.error("⚠️ Envie o Molde e a Fonte no Passo 1 antes de renderizar.")
                else:
                    with st.status("🎬 Renderizando vídeo final pronto para postar...", expanded=True) as status:
                        caminho_saida = os.path.join(pasta_temp, "resultado.mp4")
                        caminho_overlay_final = os.path.join(pasta_temp, "overlay_final.png")

                        criar_overlay_titulo_emojis(
                            texto_final, tamanho_fonte, posicao_y, cor_nome, largura_borda,
                            fonte_ativa, caminho_overlay_final
                        )

                        speed_cmd = ",setpts=PTS/1.03" if modo_anti_copyright else ""
                        filtro_video = f"[0:v]crop={final_w}:{final_h}:{final_x}:{final_y},scale=1080:-2{speed_cmd}[vid];"

                        tem_som = tem_audio(st.session_state["video_original"])
                        if modo_anti_copyright and tem_som:
                            filtro_audio = "[0:a]atempo=1.03[a];"
                            mapa_audio = ["[a]"]
                        elif tem_som:
                            filtro_audio = ""
                            mapa_audio = ["0:a?"]
                        else:
                            filtro_audio = ""
                            mapa_audio = []

                        filtro_completo = (
                            f"[1:v]scale=1080:1920[fundo];"
                            f"{filtro_video}{filtro_audio}"
                            f"[fundo][vid]overlay=(W-w)/2:{pos_y_video}[base];"
                            f"[base][2:v]overlay=0:0[v]"
                        )

                        comando = [
                            "ffmpeg", "-y",
                            "-i", st.session_state["video_original"],
                            "-i", molde_ativo,
                            "-i", caminho_overlay_final,
                            "-filter_complex", filtro_completo,
                            "-map", "[v]"
                        ]
                        if mapa_audio: comando.extend(["-map", mapa_audio[0], "-c:a", "aac"])
                        comando.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])

                        mapa_dur = {"30s": "30", "50s": "50", "60s": "60", "120s": "120", "150s": "150"}
                        if duracao in mapa_dur: comando.extend(["-t", mapa_dur[duracao]])
                        comando.append(caminho_saida)

                        subprocess.run(comando, check=True)
                        status.update(label="✅ Vídeo renderizado com sucesso!", state="complete", expanded=False)

                    with open(caminho_saida, "rb") as f_video:
                        st.success("O corte final está pronto!")
                        st.download_button(
                            label="⬇️ BAIXAR VÍDEO PRONTO", 
                            data=f_video.read(), 
                            file_name="corte_final.mp4", 
                            mime="video/mp4", 
                            use_container_width=True
                        )
