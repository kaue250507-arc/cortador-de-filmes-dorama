import os
import json
import yt_dlp

# AS 6 CONTAS MONITORIZADAS DO KWAI
PERFIS_KWAI = [
    {"canal": "@doramasbrasil", "url": "https://www.kwai.com/@doramasbrasill"},
    {"canal": "@Doramasonline", "url": "https://www.kwai.com/@Doramasonline."},
    {"canal": "@josiiedits", "url": "https://www.kwai.com/@josiiedits"},
    {"canal": "@clichegarota", "url": "https://www.kwai.com/@clichegarota"},
    {"canal": "@DoramaOnline", "url": "https://www.kwai.com/@DoramaOnline."},
    {"canal": "@mundosdodorama552", "url": "https://www.kwai.com/@mundodosdorama552"}
]

ARQUIVO_FEED = "feed_doramas.json"

def minerar():
    novos_videos = []
    
    # Carrega os vídeos existentes para não criar duplicados
    if os.path.exists(ARQUIVO_FEED):
        try:
            with open(ARQUIVO_FEED, "r", encoding="utf-8") as f:
                novos_videos = json.load(f)
        except Exception:
            novos_videos = []

    urls_existentes = {v.get("url_original") for v in novos_videos if "url_original" in v}

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'playlistend': 3,  # Recolhe os 3 vídeos mais recentes de cada canal
    }

    print("A iniciar mineração dos canais...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for perfil in PERFIS_KWAI:
            print(f"A verificar canal: {perfil['canal']}")
            try:
                info = ydl.extract_info(perfil["url"], download=False)
                entries = info.get('entries', []) or []
                
                for entry in entries:
                    link_post = entry.get('url') or entry.get('webpage_url')
                    if link_post and link_post not in urls_existentes:
                        try:
                            video_detalhe = ydl.extract_info(link_post, download=False)
                            mp4_direto = video_detalhe.get('url')
                            titulo = video_detalhe.get('title') or "Cena Viral de Dorama"
                            
                            # Limpeza de hashtags e menções
                            titulo_limpo = " ".join([p for p in titulo.split() if not p.startswith(('#', '@'))])

                            if mp4_direto:
                                novos_videos.insert(0, {
                                    "canal": perfil["canal"],
                                    "titulo": titulo_limpo or "Cena em Alta",
                                    "dorama": "Dorama em Alta",
                                    "url_original": link_post,
                                    "mp4": mp4_direto
                                })
                                urls_existentes.add(link_post)
                                print(f"✅ Adicionado com sucesso: {titulo_limpo}")
                        except Exception as e:
                            print(f"Erro ao extrair vídeo individual: {e}")
            except Exception as e:
                print(f"Erro no perfil {perfil['canal']}: {e}")

    # Mantém os 30 clipes mais recentes no catálogo
    novos_videos = novos_videos[:30]

    with open(ARQUIVO_FEED, "w", encoding="utf-8") as f:
        json.dump(novos_videos, f, ensure_ascii=False, indent=2)

    print(f"Mineração finalizada! Total de vídeos no feed: {len(novos_videos)}")

if __name__ == "__main__":
    minerar()
