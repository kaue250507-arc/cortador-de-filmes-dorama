import os
import json
import yt_dlp

# TERMOS VIRALIZADOS DE DORAMAS
TERMOS_PESQUISA = [
    "ytsearch5:dorama cortes dublado shorts",
    "ytsearch5:melhores cenas doramas ciumes shorts",
    "ytsearch5:dorama romance cenas shorts"
]

ARQUIVO_FEED = "feed_doramas.json"

def minerar():
    novos_videos = []
    urls_existentes = set()

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
        'extract_flat': False,
    }

    print("A iniciar mineração de clipes de doramas...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for busca in TERMOS_PESQUISA:
            print(f"A pesquisar: {busca}")
            try:
                info = ydl.extract_info(busca, download=False)
                entries = info.get('entries', []) or []
                
                for entry in entries:
                    if not entry:
                        continue
                    
                    url_video = entry.get('url') or entry.get('webpage_url')
                    titulo = entry.get('title') or "Cena Incrível de Dorama"
                    canal = entry.get('uploader') or entry.get('channel') or "@dorama"
                    
                    # Procura o link direto de reprodução .mp4
                    mp4_direto = None
                    if entry.get('url') and '.mp4' in entry.get('url'):
                        mp4_direto = entry.get('url')
                    elif entry.get('formats'):
                        for f in entry['formats']:
                            if f.get('ext') == 'mp4' and f.get('url'):
                                mp4_direto = f['url']
                                break

                    link_reproducao = mp4_direto or url_video

                    if link_reproducao and url_video not in urls_existentes:
                        novos_videos.append({
                            "canal": canal,
                            "titulo": titulo,
                            "dorama": "Dorama em Alta",
                            "url_original": url_video,
                            "mp4": link_reproducao
                        })
                        urls_existentes.add(url_video)
                        print(f"✅ Encontrado: {titulo}")
            except Exception as e:
                print(f"Erro na pesquisa {busca}: {e}")

    # Mantém os 20 melhores vídeos
    novos_videos = novos_videos[:20]

    with open(ARQUIVO_FEED, "w", encoding="utf-8") as f:
        json.dump(novos_videos, f, ensure_ascii=False, indent=2)

    print(f"Finalizado com sucesso! Total de vídeos no feed: {len(novos_videos)}")

if __name__ == "__main__":
    minerar()
