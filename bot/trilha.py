"""Põe a trilha da editoria no reels.mp4 recém-renderizado (pedido do João, 27/10/2026).

Roda no pipeline logo depois do render. Para cada fila/<id>/post.json com render.reels e sem
render.reels.trilha, junta trilhas/<editoria>.m4a ao vídeo (o vídeo não é recodificado: a arte
aprovada fica idêntica), cortada no tamanho do vídeo e com fade de 1,5 s no fim. Grava
render.reels.trilha. Post com "trilha": false fica mudo. Editoria sem arquivo usa a de política.
O arquivo de trilha fica fora de assets/, então não mexe na impressão visual.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRILHAS = RAIZ / "trilhas"


def duracao(video: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def aplicar(video: Path, trilha: Path) -> None:
    d = duracao(video)
    tmp = video.with_name("reels-trilha.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-stream_loop", "-1", "-i", str(trilha),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-af", f"afade=t=in:d=0.3,afade=t=out:st={max(0.0, d - 1.5):.2f}:d=1.5",
                    "-t", f"{d:.2f}", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(video)


def main() -> None:
    for arq in sorted((RAIZ / "fila").glob("*/post.json")):
        post = json.loads(arq.read_text(encoding="utf-8"))
        reels = (post.get("render") or {}).get("reels")
        if post.get("status") != "renderizado" or not reels or reels.get("trilha") or post.get("trilha") is False:
            continue
        video = arq.parent / reels["video"]
        if not video.exists():
            continue
        trilha = TRILHAS / f"{post.get('editoria')}.m4a"
        if not trilha.exists():
            trilha = TRILHAS / "politica.m4a"
        try:
            aplicar(video, trilha)
            reels["trilha"] = trilha.name
        except (subprocess.CalledProcessError, ValueError) as e:
            reels["trilha_erro"] = str(e)[:200]
        arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(arq.parent.name, reels.get("trilha") or reels.get("trilha_erro"))


if __name__ == "__main__":
    main()
