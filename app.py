import os
import re
import json
import uuid
import html
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# Tenta carregar pilmoji para renderizar emojis coloridos
try:
    from pilmoji import Pilmoji
except ImportError:
    Pilmoji = None

st.set_page_config(
    page_title="Studio Filmes/Dorama", 
    page_icon="🎬", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# DESIGN SYSTEM: OTIMIZADO PARA MOBILE
# ==============================================================================
st.markdown("""
<style>
    #MainMenu, header, footer, .stDeployButton { display: none !important; visibility: hidden !important; }
    html, body, [class*="css"] { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; }
    .stApp {
        background: radial-gradient(circle at 50% -10%, #1a1025 0%, #0c0f17 55%, #06080d 100%) !important;
        color: #f1f5f9 !important;
    }
    div[data-testid="stContainer"] {
        background: rgba(18, 23, 33, 0.75) !important;
        backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
        padding: 18px !important;
        margin-bottom: 12px !important;
    }
    @media (max-width: 768px) {
        div[data-testid="stContainer"] { padding: 12px !important; }
        h3 { font-size: 1.25rem !important; }
        h4 { font-size: 1.05rem !important; }
    }
    button[kind="primary"] {
        background: linear-gradient(135deg, #ff3366 0%, #ff1f44 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
        box-shadow: 0 4px 20px rgba(255, 31, 68, 0.35) !important;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0b0e14 !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    div[data-baseweb="slider"] div { background-color: #ff3366 !important; }
    video, img {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# PASTAS PERSISTENTES E ARQUIVOS FIXOS
# ==============================================================================
PASTA_STORAGE = os.path.abspath("storage_app")
os.makedirs(PASTA_STORAGE, exist_ok=True)

CAMINHO_MOLDE_FIXO = os.path.join(PASTA_STORAGE, "molde_padrao.png")
CAMINHO_FONTE_FIXA = os.path.join(PASTA_STORAGE, "fonte_padrao.ttf")
CAMINHO_VIDEO_ATUAL = os.path.join(PASTA_STORAGE, "video_atual.mp4")
CAMINHO_FRAME_REF = os.path.join(PASTA_STORAGE, "frame_ref.jpg")

# ==============================================================================
# DOWNLOAD ULTRA-RÁPIDO E EXTRAÇÃO
# ==============================================================================
def limpar_texto_legenda(texto):
    if not texto: return ""
    if re.match(r'^(?:video|post)\s+by\s+', texto, re.IGNORECASE): return ""
    t = html.unescape(texto)
    linhas = [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith(('#', '@', '.', '-'))]
    if linhas: t = linhas[0]
    t = re.sub(r'#\S+', '', t)
    t = re.sub(r'@\S+', '', t)
    t = re.sub(r'https?://\S+', '', t)
    return t.strip(' "\'“”-–:()[]{}').strip()

def baixar_video_rapido(url_alvo, destino_mp4):
    url_limpa = url_alvo.strip()
    titulo_detectado = ""

    # TikTok: API direta sem overhead de scraping
    if "tiktok.com" in url_limpa:
        try:
            api_url = f"https://www.tikwm.com/api/?url={urllib.parse.quote(url_limpa)}"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                dados = json.loads(resp.read().decode('utf-8'))
                if dados.get("code") == 0 and dados.get("data"):
                    play_url = dados["data"].get("play") or dados["data"].get("wmplay")
                    if dados["data"].get("title"):
                        titulo_detectado = limpar_texto_legenda(dados["data"]["title"])
                    if play_url:
                        req_v = urllib.request.Request(play_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_v, timeout=15) as r, open(destino_mp4, 'wb') as f:
                            while chunk := r.read(64 * 1024):
                                f.write(chunk)
                        return True, titulo_detectado or "ASSISTA ATÉ AO FIM"
        except Exception:
            pass

    # Instagram, Kwai, Shorts: Download direto via yt-dlp em passo único
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-warnings",
        "-f", "best[ext=mp4]/best",
        "-o", destino_mp4,
        "--force-overwrites",
        "--socket-timeout", "12",
        "--print", "title",
        url_limpa
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if res.stdout:
            titulo_detectado = limpar_texto_legenda(res.stdout.splitlines()[0])
        if os.path.exists(destino_mp4) and os.path.getsize(destino_mp4) > 5000:
            return True, titulo_detectado or "ASSISTA ATÉ AO FIM"
    except Exception:
        pass

    return False, ""

# ==============================================================================
# DETECÇÃO INTELIGENTE DE CORTES (OPENCV)
# ==============================================================================
def detectar_crop_inteligente(caminho_video):
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        return 0, 0, 1080, 1920, None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    indices = [int(total_frames * 0.2), int(total_frames * 0.45), int(total_frames * 0.7)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(idx, max(0, total_frames - 5)))
        ret, frame = cap.read()
        if ret: frames.append(frame)
    cap.release()

    if len(frames) < 2:
        return 0, 0, width, height, frames[0] if frames else None

    diff_acumulada = np.zeros((height, width), dtype=np.uint8)
    base_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for f in frames[1:]:
        f_gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        diff_acumulada = np.maximum(diff_acumulada, cv2.absdiff(base_gray, f_gray))

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
# RENDERIZADOR DE TEXTO COM EMOJIS (PIL / PILMOJI)
# ==============================================================================
def quebrar_duas_linhas(frase):
    palavras = frase.split()
    if not palavras: return "ASSISTA ATÉ AO FIM", ""
    if len(palavras) <= 3: return frase, ""
    melhor_corte = max(1, len(palavras) // 2)
    menor_dif = float('inf')
    for i in range(1, len(palavras)):
        l1, l2 = " ".join(palavras[:i]), " ".join(palavras[i:])
        dif = abs(len(l1) - len(l2))
        if dif < menor_dif:
            menor_dif, melhor_corte = dif, i
    return " ".join(palavras[:melhor_corte]), " ".join(palavras[melhor_corte:])

def gerar_camada_texto_emoji(texto, tamanho_fonte, posicao_y, cor_nome, borda_largura, caminho_fonte, caminho_saida_png):
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    
    # Carrega fonte personalizada ou fallback
    try:
        font = ImageFont.truetype(caminho_fonte, tamanho_fonte)
    except Exception:
        font = ImageFont.load_default()

    l1, l2 = quebrar_duas_linhas(texto)
    linhas = [l for l in [l1, l2] if l]

    mapa_cores = {"Preto": (0, 0, 0, 255), "Branco": (255, 255, 255, 255), "Amarelo": (255, 220, 0, 255)}
    cor_fill = mapa_cores.get(cor_nome, (0, 0, 0, 255))
    cor_stroke = (255, 255, 255, 255) if cor_nome == "Preto" else (0, 0, 0, 255)

    espacamento = int(tamanho_fonte * 1.25)
    
    # Renderização com suporte completo a Emojis coloridos
    if Pilmoji:
        with Pilmoji(img) as pilmoji:
            for idx, linha in enumerate(linhas):
                bbox = pilmoji.getsize(linha, font=font)
                largura_linha = bbox[0]
                x = (1080 - largura_linha) // 2
                y = posicao_y + (idx * espacamento)
                pilmoji.text(
                    (x, y), linha, fill=cor_fill, font=font,
                    stroke_width=borda_largura, stroke_fill=cor_stroke if borda_largura > 0 else None
                )
    else:
        draw = ImageDraw.Draw(img)
        for idx, linha in enumerate(linhas):
            bbox = draw.textbbox((0, 0), linha, font=font)
            largura_linha = bbox[2] - bbox[0]
            x = (1080 - largura_linha) // 2
            y = posicao_y + (idx * espacamento)
            draw.text(
                (x, y), linha, fill=cor_fill, font=font,
                stroke_width=borda_largura, stroke_fill=cor_stroke if borda_largura > 0 else None
            )

    img.save(caminho_saida_png, "PNG")
    return caminho_saida_png

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.markdown('<div style="text-align:center; font-size: 2.2rem; font-weight: 900; background: linear-gradient(90deg, #ff3366, #ff7676, #ff3366); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🎬 Studio Filmes/Dorama</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color: #94a3b8; font-size: 0.92rem; margin-bottom: 20px;">Cortes Verticais com Enquadramento Inteligente</div>', unsafe_allow_html=True)

# 1. IDENTIDADE VISUAL FIXA E IMPORTAÇÃO
col_topo_1, col_topo_2 = st.columns([1, 1])

with col_topo_1:
    with st.container(border=True):
        st.markdown("### 📁 1. Molde e Fonte (Salvos)")
        molde_existente = os.path.exists(CAMINHO_MOLDE_FIXO)
        fonte_existente = os.path.exists(CAMINHO_FONTE_FIXA)

        st.caption(f"Status: Molde {'✅ Salvo' if molde_existente else '❌ Ausente'} | Fonte {'✅ Salva' if fonte_existente else '❌ Ausente'}")
        
        col_m, col_f = st.columns(2)
        with col_m:
            fundo_user = st.file_uploader("Trocar Molde Rosa", type=["jpg", "jpeg", "png"])
            if fundo_user:
                with open(CAMINHO_MOLDE_FIXO, "wb") as f: f.write(fundo_user.getbuffer())
                st.success("Molde atualizado!")
                st.rerun()
        with col_f:
            fonte_user = st.file_uploader("Trocar Fonte", type=["ttf", "otf"])
            if fonte_user:
                with open(CAMINHO_FONTE_FIXA, "wb") as f: f.write(fonte_user.getbuffer())
                st.success("Fonte atualizada!")
                st.rerun()

with col_topo_2:
    with st.container(border=True):
        st.markdown("### 🔎 2. Importar Vídeo")
        link_avulso = st.text_input("Cole o link (Instagram, TikTok, Kwai):")
        if st.button("📥 Carregar Vídeo", use_container_width=True):
            if not link_avulso or not link_avulso.startswith("http"):
                st.warning("⚠️ Insira um link válido.")
            else:
                with st.spinner("Baixando em alta velocidade e calculando corte com IA..."):
                    sucesso, titulo = baixar_video_rapido(link_avulso, CAMINHO_VIDEO_ATUAL)
                    if sucesso:
                        st.session_state["texto_input_armazenado"] = titulo if titulo else "ASSISTA ATÉ AO FIM"
                        x, y, w, h, frame_ref = detectar_crop_inteligente(CAMINHO_VIDEO_ATUAL)
                        st.session_state["crop_x"], st.session_state["crop_y"] = x, y
                        st.session_state["crop_w"], st.session_state["crop_h"] = w, h
                        if frame_ref is not None:
                            st.session_state["orig_h"], st.session_state["orig_w"] = frame_ref.shape[:2]
                            cv2.imwrite(CAMINHO_FRAME_REF, frame_ref)
                        st.success("✅ Vídeo pronto!")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível baixar o vídeo deste link.")

# 2. EDIÇÃO INTEGRADA COM EMOJIS E MOLDE
if os.path.exists(CAMINHO_VIDEO_ATUAL):
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
            st.markdown("#### 📺 Vídeo Original")
            st.video(CAMINHO_VIDEO_ATUAL)

    with col_editor:
        with st.container(border=True):
            st.markdown("#### 🎛️ Título com Emojis e Posição")
            
            valor_inicial = st.session_state.get("texto_input_armazenado", "ASSISTA ATÉ AO FIM")
            texto_final = st.text_input("Texto de Destaque no Topo:", value=valor_inicial)
            st.session_state["texto_input_armazenado"] = texto_final

            col_t1, col_t2 = st.columns(2)
            with col_t1: tamanho_fonte = st.slider("Tamanho da Fonte:", 30, 90, 60, 2)
            with col_t2: posicao_y = st.slider("Altura do Texto:", 150, 700, 310, 10)

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                cor_nome = st.selectbox("Cor do Texto:", ["Preto", "Branco", "Amarelo"], index=0)
            with col_c2:
                opcoes_borda = {"Sem Borda": 0, "Borda Fina": 3, "Borda Marcante": 5}
                borda_nome = st.selectbox("Contorno / Borda:", list(opcoes_borda.keys()), index=0)
                largura_borda = opcoes_borda[borda_nome]

            with st.expander("✂️ Ajustar Corte Manualmente (A IA já fatiou o vídeo)", expanded=False):
                corte_topo = st.slider("✂️ Cortar do Topo (pixels):", 0, int(orig_h * 0.7), min(init_top, int(orig_h * 0.7)), step=2)
                corte_base = st.slider("✂️ Cortar da Base (pixels):", 0, int(orig_h * 0.7), min(init_bottom, int(orig_h * 0.7)), step=2)
                
                col_l1, col_l2 = st.columns(2)
                with col_l1: corte_esq = st.slider("Cortar Esquerda:", 0, int(orig_w * 0.4), min(init_left, int(orig_w * 0.4)), step=2)
                with col_l2: corte_dir = st.slider("Cortar Direita:", 0, int(orig_w * 0.4), min(init_right, int(orig_w * 0.4)), step=2)

                pos_y_video = st.slider("📍 Altura do Vídeo na Moldura:", 350, 1000, 640, 10)

                if st.button("🔄 Recalcular Corte com IA"):
                    x, y, w, h, _ = detectar_crop_inteligente(CAMINHO_VIDEO_ATUAL)
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

            # PRÉ-VISUALIZAÇÃO COMPLETA INSTANTÂNEA
            if os.path.exists(CAMINHO_MOLDE_FIXO):
                caminho_overlay_png = os.path.join(PASTA_STORAGE, "overlay_texto.png")
                gerar_camada_texto_emoji(
                    texto_final, tamanho_fonte, posicao_y, cor_nome, largura_borda,
                    CAMINHO_FONTE_FIXA, caminho_overlay_png
                )

                caminho_preview_final = os.path.join(PASTA_STORAGE, "preview_pronto.jpg")
                filtro_prev = (
                    f"[1:v]scale=1080:1920[fundo];"
                    f"[0:v]crop={final_w}:{final_h}:{final_x}:{final_y},scale=1080:-2[vid];"
                    f"[fundo][vid]overlay=(W-w)/2:{pos_y_video}[base];"
                    f"[base][2:v]overlay=0:0[v]"
                )
                cmd_prev = [
                    "ffmpeg", "-y",
                    "-ss", "1.5", "-i", CAMINHO_VIDEO_ATUAL,
                    "-i", CAMINHO_MOLDE_FIXO,
                    "-i", caminho_overlay_png,
                    "-filter_complex", filtro_prev,
                    "-map", "[v]", "-frames:v", "1", "-update", "1",
                    caminho_preview_final
                ]
                try:
                    subprocess.run(cmd_prev, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    if os.path.exists(caminho_preview_final):
                        st.image(caminho_preview_final, caption="✨ Prévia Final com Emojis", use_container_width=True)
                except Exception:
                    pass

            # 3. EXPORTAÇÃO
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1: modo_anti_copyright = st.checkbox("🛡️ Modo Anti-Copyright (+3% de Velocidade)", value=True)
            with col_cfg2: duracao = st.selectbox("Duração do Vídeo:", ["30s", "50s", "60s", "120s", "150s", "Vídeo Completo"])

            btn_gerar = st.button("🚀 INICIAR RENDERIZAÇÃO FINAL", type="primary", use_container_width=True)

            if btn_gerar:
                if not os.path.exists(CAMINHO_MOLDE_FIXO):
                    st.error("⚠️ Envie o Molde Rosa no Passo 1.")
                else:
                    with st.status("🎬 Renderizando corte em alta resolução...", expanded=True) as status:
                        caminho_saida = os.path.join(PASTA_STORAGE, "resultado.mp4")
                        caminho_overlay_png = os.path.join(PASTA_STORAGE, "overlay_texto.png")

                        gerar_camada_texto_emoji(
                            texto_final, tamanho_fonte, posicao_y, cor_nome, largura_borda,
                            CAMINHO_FONTE_FIXA, caminho_overlay_png
                        )

                        speed_cmd = ",setpts=PTS/1.03" if modo_anti_copyright else ""
                        filtro_video = f"[1:v]crop={final_w}:{final_h}:{final_x}:{final_y},scale=1080:-2{speed_cmd}[vid];"
                        filtro_audio = "[1:a]atempo=1.03[a];" if modo_anti_copyright else ""
                        mapa_audio = ["[a]"] if modo_anti_copyright else ["1:a?"]

                        filtro_completo = (
                            f"[0:v]scale=1080:1920[fundo];"
                            f"{filtro_video}{filtro_audio}"
                            f"[fundo][vid]overlay=(W-w)/2:{pos_y_video}[base];"
                            f"[base][2:v]overlay=0:0[v]"
                        )

                        comando = [
                            "ffmpeg", "-y",
                            "-i", CAMINHO_MOLDE_FIXO,
                            "-i", CAMINHO_VIDEO_ATUAL,
                            "-i", caminho_overlay_png,
                            "-filter_complex", filtro_completo,
                            "-map", "[v]"
                        ]
                        if mapa_audio: comando.extend(["-map", mapa_audio[0], "-c:a", "aac"])
                        comando.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])

                        mapa_dur = {"30s": "30", "50s": "50", "60s": "60", "120s": "120", "150s": "150"}
                        if duracao in mapa_dur: comando.extend(["-t", mapa_dur[duracao]])
                        comando.append(caminho_saida)

                        subprocess.run(comando, check=True)
                        status.update(label="✅ Renderização concluída com sucesso!", state="complete", expanded=False)

                    with open(caminho_saida, "rb") as f_video:
                        st.success("O vídeo está pronto!")
                        st.download_button(
                            label="⬇️ BAIXAR VÍDEO PRONTO", 
                            data=f_video.read(), 
                            file_name="corte_final.mp4", 
                            mime="video/mp4", 
                            use_container_width=True
                        )
