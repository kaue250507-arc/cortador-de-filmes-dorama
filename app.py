import os
import re
import uuid
import html
import json
import random
import urllib.request
import urllib.parse
import subprocess
import glob
import shutil
import streamlit as st

st.set_page_config(page_title="Studio Dorama - Feed & Cortes", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# AS 6 CONTAS MONITORIZADAS (KWAI)
# ==========================================
PERFIS_KWAI = {
    "doramasbrasil": "https://kwai-video.com/u/@doramasbrasill/8x4HFCCh",
    "Doramasonline": "https://kwai-video.com/u/@Doramasonline./D7uCBBQs",
    "josiiedits": "https://kwai-video.com/u/@josiiedits/KCWSzKBk",
    "clichegarota": "https://kwai-video.com/u/@clichegarota/6fF9JuCW",
    "DoramaOnline": "https://kwai-video.com/u/@DoramaOnline./XuCEcVtu",
    "mundosdodorama552": "https://kwai-video.com/u/@mundodosdorama552/VCRC2ZaI",
}

# Estilização da interface
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

    /* Barra Superior de Navegação */
    div[data-testid="stRadio"] > div {
        display: flex;
        justify-content: center;
        gap: 15px;
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
        padding: 8px 20px !important;
        cursor: pointer !important;
        border-radius: 8px !important;
    }

    div[data-testid="stContainer"] {
        background-color: #161b22;
        border-radius: 16px !important;
        border: 1px solid #30363d !important;
        padding: 15px;
    }

    h3, h4 { color: #e6edf3 !important; font-weight: 700 !important; }
    label { color: #c9d1d9 !important; font-weight: 600 !important; }

    button[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff1f1f 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 0 !important;
        font-size: 1.05rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4) !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 22px rgba(255, 75, 75, 0.6) !important;
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
def extrair_link_mp4_direto(url_video):
    """Extrai exclusivamente a transmissão MP4 do Kwai ou TikTok."""
    if not url_video or not url_video.startswith("http"):
        return None, ""
    
    if any(k in url_video for k in ["kwai.com", "kwai-video.com", "k.kwai.com"]):
        try:
            req = urllib.request.Request(
                url_video, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                html_raw = resp.read().decode('utf-8', errors='ignore')
            
            metas = re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', html_raw, re.IGNORECASE)
            leg = ""
            for m in metas:
                limp = limpar_legenda(html.unescape(m))
                if len(limp) > 5:
                    leg = limp
                    break
            
            urls_mp4 = re.findall(r'https://[^\s"\'<>]+\.mp4[^\s"\'<>]*', html_raw.replace(r'\/', '/'))
            if urls_mp4:
                return urls_mp4[0], leg
        except Exception:
            pass

    return None, ""

@st.cache_data(ttl=900, show_spinner=False)
def minerar_feed_automatico():
    """Varre automaticamente os 6 canais do Kwai à procura de novos vídeos postados."""
    feed = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept-Language': 'pt-BR,pt;q=0.9',
    }
    for canal, url_perfil in PERFIS_KWAI.items():
        try:
            req = urllib.request.Request(url_perfil, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                conteudo = resp.read().decode('utf-8', errors='ignore')
            
            links_post = re.findall(r'https?://[a-zA-Z0-9\.\-]+/p/([a-zA-Z0-9]+)', conteudo)
            if not links_post:
                links_post = re.findall(r'/short-video/([a-zA-Z0-9]+)', conteudo)
            
            for pid in list(dict.fromkeys(links_post))[:2]:
                url_post = f"https://k.kwai.com/p/{pid}"
                mp4, leg = extrair_link_mp4_direto(url_post)
                if mp4:
                    feed.append({
                        "canal": f"@{canal}",
                        "titulo": leg or f"Cena em alta no canal @{canal}",
                        "dorama": "Dorama em Alta",
                        "url": url_post,
                        "mp4": mp4
                    })
        except Exception:
            pass
            
    # Garantia de segurança com vídeo real comprovado caso o servidor do Kwai demore
    if not feed:
        mp4_seguro, leg_segura = extrair_link_mp4_direto("https://k.kwai.com/p/sHCgDks5")
        if mp4_seguro:
            feed.append({
                "canal": "@doramasbrasil",
                "titulo": leg_segura or "Ele ficou morrendo de ciúmes ao ver ela na companhia de outro ❤️",
                "dorama": "Beleza Verdadeira (True Beauty)",
                "url": "https://k.kwai.com/p/sHCgDks5",
                "mp4": mp4_seguro
            })
    return feed

def descarregar_video_motor(url_alvo, pasta_destino):
    """Transfere o vídeo para o servidor de forma protegida para aplicar a edição."""
    caminho_saida = os.path.join(pasta_destino, "preview.mp4")
    for f_antigo in glob.glob(os.path.join(pasta_destino, "preview*")):
        try: os.remove(f_antigo)
        except Exception: pass

    legenda = ""
    sucesso = False

    mp4_direto, leg_dir = extrair_link_mp4_direto(url_alvo)
    alvo = mp4_direto if mp4_direto else url_alvo

    try:
        req = urllib.request.Request(alvo, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=25) as v_stream, open(caminho_saida, "wb") as f_out:
            f_out.write(v_stream.read())
        sucesso = True
        legenda = leg_dir
    except Exception:
        sucesso = False

    if not sucesso and "kwai" in url_alvo:
        try:
            urllib.request.urlretrieve(alvo, caminho_saida)
            sucesso = True
            legenda = leg_dir
        except Exception:
            sucesso = False

    return sucesso, caminho_saida, legenda

# ==========================================
# INICIALIZAÇÃO DE SESSÃO
# ==========================================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "preview_fixo" not in st.session_state:
    st.session_state["preview_fixo"] = False

# CONTROLO SEGURO DE ABA (EVITA O ERRO DE WIDGET INSTANTIATED)
if "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = "feed"

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

st.markdown('<div style="text-align:center; font-size: 2.6rem; font-weight: 900; background: linear-gradient(90deg, #ff4b4b, #ff7676, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-top: 10px;">🎬 Studio Dorama: Feed & Cortes</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color: #8b949e; font-size: 1rem; margin-bottom: 20px;">Role o feed para baixo, assista aos vídeos dos canais e corte em 1 toque</div>', unsafe_allow_html=True)

# GESTÃO SELETORA DE ABAS
opcoes_menu = ["🔥 Feed TikTok (Vídeos dos Perfis)", "🎬 Editor de Cortes"]
idx_menu = 0 if st.session_state["aba_ativa"] == "feed" else 1

aba_selecionada = st.radio(
    "Navegação:",
    opcoes_menu,
    index=idx_menu,
    horizontal=True,
    label_visibility="collapsed",
    key="widget_radio_menu_principal"
)

# Sincroniza se o utilizador clicar manualmente
if aba_selecionada == "🔥 Feed TikTok (Vídeos dos Perfis)" and st.session_state["aba_ativa"] != "feed":
    st.session_state["aba_ativa"] = "feed"
    st.rerun()
elif aba_selecionada == "🎬 Editor de Cortes" and st.session_state["aba_ativa"] != "editor":
    st.session_state["aba_ativa"] = "editor"
    st.rerun()

# ==============================================================================
# ABA 1: FEED TIKTOK VERTICAL
# ==============================================================================
if st.session_state["aba_ativa"] == "feed":
    
    col_topo_feed_1, col_topo_feed_2 = st.columns([3, 1])
    with col_topo_feed_1:
        st.caption("🔄 Feed sincronizado automaticamente com as 6 contas monitorizadas.")
    with col_topo_feed_2:
        if st.button("🔄 Atualizar Feed Agora", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.expander("➕ Adicionar Link Específico do Kwai ao Feed"):
        col_ad1, col_ad2 = st.columns([3, 1])
        with col_ad1:
            novo_link = st.text_input("Cole o link de qualquer vídeo do Kwai (ex: https://k.kwai.com/p/...):")
        with col_ad2:
            st.write("")
            st.write("")
            if st.button("Adicionar ao Topo", use_container_width=True):
                if novo_link and novo_link.startswith("http"):
                    mp4_add, leg_add = extrair_link_mp4_direto(novo_link)
                    if mp4_add:
                        if "feed_custom" not in st.session_state:
                            st.session_state["feed_custom"] = []
                        st.session_state["feed_custom"].insert(0, {
                            "canal": "Manual",
                            "titulo": leg_add or "Cena Adicionada Manualmente",
                            "dorama": "Dorama em Alta",
                            "url": novo_link,
                            "mp4": mp4_add
                        })
                        st.success("Vídeo validado e adicionado com sucesso ao topo do feed!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Não foi possível extrair este vídeo. Verifique se o link está público.")

    # Carregamento automático e união de listas
    lista_final = []
    if "feed_custom" in st.session_state:
        lista_final.extend(st.session_state["feed_custom"])
    lista_final.extend(minerar_feed_automatico())

    st.markdown("<p style='text-align: center; color: #8b949e; font-size: 0.95rem; margin: 20px 0;'>👇 <b>Deslize a tela para baixo</b> para assistir aos clipes dos canais:</p>", unsafe_allow_html=True)

    # ROLAGEM VERTICAL CONTÍNUA ESTILO TIKTOK
    for idx, item in enumerate(lista_final):
        col_esp1, col_feed, col_esp2 = st.columns([1, 1.4, 1])
        
        with col_feed:
            st.markdown(f"#### 📱 #{idx+1} {item['titulo']}")
            st.caption(f"👤 Canal de Origem: **{item['canal']}** | 🎭 Dorama: **{item['dorama']}**")

            # Validação rigorosa: só desenha o reprodutor se houver transmissão MP4 válida
            if item.get("mp4"):
                st.video(item["mp4"])
                if st.button("✂️ CORTAR ESTE VÍDEO AGORA", key=f"btn_cortar_{idx}_{item['url'][-10:]}", type="primary", use_container_width=True):
                    with st.spinner("A carregar vídeo na bancada de corte..."):
                        sucesso, c_out, leg = descarregar_video_motor(item["url"], pasta_temp)
                        if sucesso and tem_imagem_de_video(c_out):
                            st.session_state["video_original"] = c_out
                            st.session_state["texto_input_armazenado"] = leg or item["titulo"]
                            st.session_state["preview_fixo"] = True
                            st.session_state["url_manual_importada"] = item["url"]
                            # MUDA DE ABA DE FORMA SEGURA SEM ERRO
                            st.session_state["aba_ativa"] = "editor"
                            st.rerun()
                        else:
                            st.error("Não foi possível carregar este vídeo. Verifique se o link está acessível.")
            else:
                st.link_button("🔗 Ver Vídeo Diretamente no Kwai", item["url"], use_container_width=True)

            st.markdown("<hr style='border-color: #30363d; margin: 40px 0;'>", unsafe_allow_html=True)

# ==============================================================================
# ABA 2: EDITOR DE CORTES
# ==============================================================================
elif st.session_state["aba_ativa"] == "editor":
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
                            st.error("Não foi possível transferir este vídeo. Verifique a ligação.")

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
