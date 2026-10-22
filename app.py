import os
import re
import csv
import uuid
import html
import random
import urllib.request
import urllib.parse
import subprocess
import glob
import streamlit as st

st.set_page_config(page_title="Studio Dorama - Feed & Cortes", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

# ==============================================================================
# CONFIGURAÇÃO DIRETA DA SUA PLANILHA GOOGLE
# ==============================================================================
LINK_PLANILHA_GOOGLE = "https://docs.google.com/spreadsheets/d/1erUG1HU4oTtdMI_KI3nEjb1imPbxgfoS2aSn3B45nt8/edit?usp=sharing"

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

def converter_link_para_csv(link):
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', link)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    return link

@st.cache_data(ttl=15, show_spinner=False)
def ler_feed_da_planilha(url_compartilhamento):
    if not url_compartilhamento:
        return []

    url_csv = converter_link_para_csv(url_compartilhamento)
    videos = []

    try:
        req = urllib.request.Request(url_csv, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            linhas = resp.read().decode('utf-8', errors='ignore').splitlines()
            leitor = csv.reader(linhas)
            dados = list(leitor)

            for linha in dados[1:]:
                if len(linha) >= 5:
                    origem = linha[0].strip()
                    canal = linha[1].strip()
                    titulo = linha[2].strip()
                    url_orig = linha[3].strip()
                    url_mp4 = linha[4].strip()

                    if url_mp4 and url_mp4.startswith("http") and url_mp4 != "-":
                        videos.append({
                            "origem": origem or "Kwai",
                            "canal": canal or "@dorama",
                            "titulo": titulo or "Cena Viral de Dorama",
                            "url_original": url_orig,
                            "mp4": url_mp4
                        })
    except Exception as e:
        st.error(f"Erro ao carregar a folha de cálculo: {e}")

    return list(reversed(videos))

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

def tem_audio(caminho_arquivo):
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", caminho_arquivo],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return "audio" in res.stdout.lower()
    except Exception:
        return True

def baixar_video_direto(url_alvo, pasta_destino):
    caminho_saida = os.path.join(pasta_destino, "preview.mp4")
    for f in glob.glob(os.path.join(pasta_destino, "preview*")):
        try: os.remove(f)
        except Exception: pass

    sucesso = False
    try:
        req = urllib.request.Request(url_alvo, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=35) as v_stream, open(caminho_saida, "wb") as f_out:
            f_out.write(v_stream.read())
        sucesso = True
    except Exception:
        try:
            urllib.request.urlretrieve(url_alvo, caminho_saida)
            sucesso = True
        except Exception:
            sucesso = False

    return sucesso, caminho_saida

# ==============================================================================
# SESSÃO E PASTAS TEMPORÁRIAS
# ==============================================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = "feed"

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

st.markdown('<div style="text-align:center; font-size: 2.6rem; font-weight: 900; background: linear-gradient(90deg, #ff4b4b, #ff7676, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-top: 10px;">🎬 Studio Dorama: Feed & Cortes</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color: #8b949e; font-size: 1rem; margin-bottom: 25px;">Sincronizado diretamente com a Planilha de Produção</div>', unsafe_allow_html=True)

col_nav_1, col_nav_2 = st.columns(2)
with col_nav_1:
    tipo_feed = "primary" if st.session_state["aba_ativa"] == "feed" else "secondary"
    if st.button("🔥 Feed Vídeos", type=tipo_feed, use_container_width=True):
        st.session_state["aba_ativa"] = "feed"
        st.rerun()

with col_nav_2:
    tipo_editor = "primary" if st.session_state["aba_ativa"] == "editor" else "secondary"
    if st.button("🎬 Editor de Cortes", type=tipo_editor, use_container_width=True):
        st.session_state["aba_ativa"] = "editor"
        st.rerun()

st.markdown("<hr style='border-color: #30363d; margin: 15px 0 25px 0;'>", unsafe_allow_html=True)

# ==============================================================================
# ABA 1: FEED DE VÍDEOS (LIDO DA PLANILHA)
# ==============================================================================
if st.session_state["aba_ativa"] == "feed":
    videos_feed = ler_feed_da_planilha(LINK_PLANILHA_GOOGLE)

    col_topo_1, col_topo_2 = st.columns([3, 1])
    with col_topo_1:
        st.caption(f"🔄 Clipes prontos na planilha: **{len(videos_feed)}**")
    with col_topo_2:
        if st.button("🔄 Atualizar Feed Agora", use_container_width=True):
            st.cache_data.clear()
            st.toast("✅ Planilha sincronizada com sucesso!")
            st.rerun()

    if not videos_feed:
        st.warning("⚠️ Nenhum vídeo pronto encontrado na folha de cálculo. Verifique se a coluna URL_MP4 foi preenchida.")
    else:
        for idx, item in enumerate(videos_feed):
            col_esp1, col_feed, col_esp2 = st.columns([1, 1.4, 1])
            with col_feed:
                st.markdown(f"#### 📱 #{idx+1} {item['titulo']}")
                st.caption(f"📍 Rede: **{item['origem']}** | 👤 Canal: **{item['canal']}**")

                st.video(item["mp4"])

                if st.button("✂️ CORTAR ESTE VÍDEO AGORA", key=f"btn_{idx}_{item['titulo'][:10]}", type="primary", use_container_width=True):
                    with st.spinner("A carregar vídeo na bancada de corte..."):
                        sucesso, caminho_vid = baixar_video_direto(item["mp4"], pasta_temp)
                        if sucesso:
                            st.session_state["video_original"] = caminho_vid
                            st.session_state["texto_input_armazenado"] = item["titulo"]
                            st.session_state["preview_fixo"] = True
                            st.session_state["aba_ativa"] = "editor"
                            st.rerun()
                        else:
                            st.error("Erro ao transferir este vídeo.")

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
                fundo_user = st.file_uploader("Molde / Moldura (PNG/JPG)", type=["jpg", "jpeg", "png"])
            with col_fonte:
                fonte_user = st.file_uploader("Fonte (TTF)", type=["ttf", "otf"])

    with col_topo_2:
        with st.container(border=True):
            st.markdown("### 🔎 2. Importar Link Avulso")
            link_avulso = st.text_input("Cole o link direto do MP4 ou vídeo:")
            if st.button("📥 Importar para Edição", use_container_width=True):
                if link_avulso.startswith("http"):
                    with st.spinner("A transferir vídeo..."):
                        sucesso, caminho_vid = baixar_video_direto(link_avulso, pasta_temp)
                        if sucesso:
                            st.session_state["video_original"] = caminho_vid
                            st.session_state["texto_input_armazenado"] = "ASSISTA ATÉ AO FIM"
                            st.session_state["preview_fixo"] = True
                            st.rerun()
                        else:
                            st.error("Não foi possível transferir este vídeo.")

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
                            st.success("O corte está pronto!")
                            st.download_button(
                                label="⬇️ BAIXAR VÍDEO PRONTO", 
                                data=f_video.read(), 
                                file_name="corte_final.mp4", 
                                mime="video/mp4", 
                                use_container_width=True
                            )
