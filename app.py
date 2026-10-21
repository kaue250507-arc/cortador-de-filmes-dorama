import os
import re
import uuid
import html
import urllib.request
import subprocess
import streamlit as st

# Configuração da página para ocupar todo o ecrã e com título atualizado
st.set_page_config(page_title="Studio DoramaX", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# INJEÇÃO DE CSS PREMIUM (DESIGN DA APP)
# ==========================================
st.markdown("""
<style>
    /* Esconder elementos padrão do Streamlit (menu, header e rodapé) */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Cor de fundo principal da aplicação */
    .stApp {
        background-color: #0b0f19;
    }

    /* Estilização do Título Principal */
    .titulo-app {
        text-align: center;
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(90deg, #ff4b4b, #ff7676, #ff4b4b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
        padding-top: 20px;
    }
    
    .subtitulo-app {
        text-align: center;
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 40px;
    }

    /* Estilizar os "Containers" (as caixas com bordas) para parecerem cartões de app */
    div[data-testid="stContainer"] {
        background-color: #161b22;
        border-radius: 16px !important;
        border: 1px solid #30363d !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
        padding: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    div[data-testid="stContainer"]:hover {
        border-color: #ff4b4b !important;
        box-shadow: 0 8px 24px rgba(255, 75, 75, 0.1) !important;
    }

    /* Estilizar os Textos e Labels */
    h3, h4 {
        color: #e6edf3 !important;
        font-weight: 700 !important;
    }
    label {
        color: #c9d1d9 !important;
        font-weight: 600 !important;
    }

    /* Botões Padrão (Upload, Analisar, Pré-visualizar) */
    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: 1px solid #30363d;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
    }

    /* Botão Principal (Renderização) com Efeito Premium */
    button[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff1f1f 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 15px 0 !important;
        font-size: 1.1rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4) !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(255, 75, 75, 0.6) !important;
    }

    /* Campos de Input (Texto e Slider) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0d1117 !important;
        color: white !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        border-color: #ff4b4b !important;
        box-shadow: 0 0 0 1px #ff4b4b !important;
    }
</style>
""", unsafe_allow_html=True)
# ==========================================

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

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

pasta_temp = os.path.abspath(f"temp_{st.session_state.session_id}")
os.makedirs(pasta_temp, exist_ok=True)

# Título Premium
st.markdown('<div class="titulo-app">🎬 Studio DoramaX</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-app">A sua ferramenta profissional de edição e cortes automáticos</div>', unsafe_allow_html=True)

col_topo_1, col_topo_2 = st.columns([1, 1])

with col_topo_1:
    with st.container(border=True):
        st.markdown("### 📁 1. Arquivos de Identidade Visual")
        col_molde, col_fonte = st.columns(2)
        with col_molde:
            fundo_user = st.file_uploader("Molde (PNG/JPG)", type=["jpg", "jpeg", "png"])
        with col_fonte:
            fonte_user = st.file_uploader("Fonte (TTF)", type=["ttf"])

with col_topo_2:
    with st.container(border=True):
        st.markdown("### 🔎 2. Importar do Kwai")
        link_kwai = st.text_input("Cole o link direto do Kwai aqui:")
        if st.button("📥 Analisar e Extrair Vídeo", use_container_width=True):
            if not link_kwai or not link_kwai.startswith("http"):
                st.warning("⚠️ Insira um link válido do Kwai.")
            else:
                with st.spinner("A estabelecer ligação com o Kwai e a transferir o vídeo..."):
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
                            st.rerun()
                        else:
                            st.error("Não foi possível encontrar o ficheiro MP4 no link fornecido.")
                    except Exception as e:
                        st.error(f"Erro na ligação ao Kwai: {e}")

st.markdown("<br>", unsafe_allow_html=True)

if "video_original" in st.session_state and os.path.exists(st.session_state["video_original"]):
    
    col_preview, col_editor = st.columns([1, 1.2])
    
    with col_preview:
        with st.container(border=True):
            st.markdown("#### 📺 Visualizador de Mídia")
            st.video(st.session_state["video_original"])

    with col_editor:
        with st.container(border=True):
            st.markdown("#### 🎛️ Painel de Edição")
            texto_final = st.text_input(
                "Texto de Destaque no Topo:", 
                value=st.session_state.get("legenda_detectada", "")
            )
            
            # SLIDER DE TAMANHO DA FONTE
            tamanho_fonte = st.slider("Tamanho da Fonte (reduza se o texto cortar no telemóvel):", min_value=30, max_value=90, value=65, step=5)
            
            # BOTÃO DE PRÉ-VISUALIZAÇÃO DE IMAGEM
            if st.button("👁️ Pré-visualizar Texto no Molde", use_container_width=True):
                if not fundo_user or not fonte_user:
                    st.warning("⚠️ Envie o Molde e a Fonte no Passo 1 para ver a pré-visualização.")
                else:
                    with st.spinner("A gerar imagem de teste..."):
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
                        draw_l1 = f"drawtext=fontfile='{caminho_fonte_prev}':textfile='{txt1_prev}':fontcolor=black:fontsize={tamanho_fonte}:x=(w-text_w)/2:y=500"
                        draw_l2 = f"drawtext=fontfile='{caminho_fonte_prev}':textfile='{txt2_prev}':fontcolor=black:fontsize={tamanho_fonte}:x=(w-text_w)/2:y=500+{espacamento}"

                        filtro_prev = f"[0:v]scale=1080:1920[fundo];[fundo]{draw_l1},{draw_l2}[v]"
                        comando_prev = [
                            "ffmpeg", "-y", "-i", caminho_molde_prev,
                            "-filter_complex", filtro_prev,
                            "-map", "[v]", "-frames:v", "1", "-update", "1",
                            caminho_saida_prev
                        ]
                        subprocess.run(comando_prev, check=True)
                        st.image(caminho_saida_prev, caption="Preview do Texto Final", use_column_width=True)

            st.markdown("<hr style='border-color: #30363d; margin: 20px 0;'>", unsafe_allow_html=True)
            
            duracao = st.selectbox("Duração Final do Vídeo:", ["30s", "50s", "60s", "Vídeo Completo"])
            st.markdown("<br>", unsafe_allow_html=True)
            
            btn_gerar = st.button("🚀 INICIAR RENDERIZAÇÃO FINAL", type="primary", use_container_width=True)

            if btn_gerar:
                if not fundo_user or not fonte_user:
                    st.error("⚠️ Envie o Molde e a Fonte no Passo 1 antes de renderizar.")
                else:
                    with st.status("🎬 A renderizar o corte (Não saia desta página)...", expanded=True) as status:
                        st.write("📥 A preparar os ficheiros base...")
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

                        st.write("📐 A calibrar enquadramento e aplicar tipografia...")
                        filtro_video = "[1:v]crop=in_w:in_w*9/16:0:(in_h-in_w*9/16)/2,scale=1080:608[vid];"
                        espacamento = tamanho_fonte + 20
                        draw_l1 = f"drawtext=fontfile='{caminho_fonte}':textfile='{txt1_path}':fontcolor=black:fontsize={tamanho_fonte}:x=(w-text_w)/2:y=500"
                        draw_l2 = f"drawtext=fontfile='{caminho_fonte}':textfile='{txt2_path}':fontcolor=black:fontsize={tamanho_fonte}:x=(w-text_w)/2:y=500+{espacamento}"

                        filtro_completo = (
                            f"[0:v]scale=1080:1920[fundo];"
                            f"{filtro_video}"
                            f"[fundo][vid]overlay=0:(H-h)/2[base];"
                            f"[base]{draw_l1},{draw_l2}[v]"
                        )

                        comando = [
                            "ffmpeg", "-y", "-i", caminho_molde, "-i", st.session_state["video_original"],
                            "-filter_complex", filtro_completo,
                            "-map", "[v]", "-map", "1:a?",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac"
                        ]

                        mapa_dur = {"30s": "30", "50s": "50", "60s": "60"}
                        if duracao in mapa_dur:
                            comando.extend(["-t", mapa_dur[duracao]])
                        comando.append(caminho_saida)

                        st.write("⚙️ A codificar o vídeo final em alta resolução...")
                        subprocess.run(comando, check=True)
                        status.update(label="✅ Renderização concluída com sucesso!", state="complete", expanded=False)

                    with open(caminho_saida, "rb") as f_video:
                        st.balloons()
                        st.success("O seu conteúdo está pronto!")
                        st.download_button(label="⬇️ BAIXAR VÍDEO PRONTO", data=f_video.read(), file_name="corte_doramax_final.mp4", mime="video/mp4", use_container_width=True)
