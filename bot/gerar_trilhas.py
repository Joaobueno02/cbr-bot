"""Gera as trilhas próprias dos Reels, uma por editoria (pedido do João, 27/10/2026).

A busca de músicas da API do Instagram volta vazia para a conta da CBR (radar/musicas.json), então
o Reels leva uma trilha nossa embutida no vídeo. As trilhas são sintetizadas aqui (numpy), sem
amostra de ninguém: não há direito autoral de terceiros nem risco de bloqueio por cópia.

Uso: python bot/gerar_trilhas.py  → grava trilhas/<editoria>.m4a (40 s, AAC 160 kbps, estéreo; precisa de ffmpeg).
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
DUR = 40.0
RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "trilhas"
NOTAS = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
         "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def hz(nota: str, oit: int) -> float:
    return 440.0 * 2 ** ((NOTAS[nota] + 12 * (oit + 1) - 69) / 12)


def acorde(raiz: str, menor: bool, oit: int = 3) -> list[float]:
    r = hz(raiz, oit)
    return [r, r * 2 ** ((3 if menor else 4) / 12), r * 2 ** (7 / 12)]


def env(n: int, a: float, r: float) -> np.ndarray:
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def passa_baixa(x: np.ndarray, corte: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # filtro de 1 polo; rápido o bastante para 40 s
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def pad(freqs: list[float], seg: float, corte: float = 1800) -> np.ndarray:
    n = int(seg * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):  # serra levemente desafinada
            ff = f * 2 ** (det / 12)
            s += 2 * ((t * ff) % 1.0) - 1
    s = passa_baixa(s / (len(freqs) * 3), corte)
    return s * env(n, min(0.6, seg / 3), min(0.8, seg / 3))


def pluck(f: float, seg: float, brilho: float = 0.996) -> np.ndarray:
    """Karplus-Strong: corda dedilhada (violão/viola)."""
    n = int(seg * SR)
    p = max(2, int(SR / f))
    buf = np.random.default_rng(int(f * 100)).uniform(-1, 1, p)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = brilho * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out * env(n, 0.002, 0.05)


def piano(f: float, seg: float) -> np.ndarray:
    n = int(seg * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.6 for k in range(1, 6))
    return s * np.exp(-t * 2.2) * env(n, 0.004, 0.1) * 0.5


def sino(f: float, seg: float) -> np.ndarray:
    n = int(seg * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t)
    return s * np.exp(-t * 3.0) * env(n, 0.002, 0.05) * 0.35


def bumbo(seg: float = 0.35) -> np.ndarray:
    n = int(seg * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def chimbal(seg: float = 0.05) -> np.ndarray:
    n = int(seg * SR)
    r = np.random.default_rng(7).uniform(-1, 1, n)
    r = r - passa_baixa(r, 6000)
    return r * np.exp(-np.arange(n) / SR * 80) * 0.5


def batida(seg: float = 0.03) -> np.ndarray:  # clave/madeira
    n = int(seg * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 160)


def por(trilha: np.ndarray, som: np.ndarray, t0: float, ganho: float = 1.0) -> None:
    i = int(t0 * SR)
    if i >= len(trilha):
        return
    j = min(len(trilha), i + len(som))
    trilha[i:j] += som[: j - i] * ganho


def compor(cfg: dict) -> np.ndarray:
    n = int(DUR * SR)
    tr = np.zeros(n)
    bpm, prog, compasso = cfg["bpm"], cfg["prog"], cfg.get("tempos", 4)
    beat = 60 / bpm
    bar = beat * compasso
    t, k = 0.0, 0
    while t < DUR:
        raiz, menor = prog[k % len(prog)]
        notas = acorde(raiz, menor, cfg.get("oit", 3))
        if cfg.get("pad"):
            por(tr, pad(notas, bar + 0.4, cfg.get("corte", 1500)), t, cfg["pad"])
        if cfg.get("baixo"):
            por(tr, pad([notas[0] / 2], bar, 400), t, cfg["baixo"])
        for b in range(compasso):
            tb = t + b * beat
            if cfg.get("bumbo") and b in cfg.get("bumbo_tempos", range(compasso)):
                por(tr, bumbo(), tb, cfg["bumbo"])
            if cfg.get("chimbal"):
                por(tr, chimbal(), tb + beat / 2, cfg["chimbal"])
        arp = cfg.get("arpejo")
        if arp:
            inst, sub, ganho = arp
            passo = beat / sub
            ordem = cfg.get("ordem", [0, 1, 2, 1])
            for s_ in range(int(compasso * sub)):
                f = notas[ordem[s_ % len(ordem)]] * cfg.get("arp_oit", 2)
                som = {"pluck": lambda: pluck(f, passo * 3, cfg.get("brilho", 0.996)),
                       "piano": lambda: piano(f, passo * 4), "sino": lambda: sino(f, passo * 3)}[inst]()
                por(tr, som, t + s_ * passo, ganho)
        if cfg.get("clave"):  # clave 3-2 (América Latina), em 2 compassos
            for pos in ([0, 1.5, 3] if k % 2 == 0 else [1, 2]):
                por(tr, batida(), t + pos * beat, cfg["clave"])
        t += bar
        k += 1
    tr *= env(n, 0.8, 2.5)
    tr /= np.max(np.abs(tr)) + 1e-9
    return tr * 0.7


def estereo(m: np.ndarray) -> np.ndarray:
    d = int(0.012 * SR)  # leve abertura estéreo
    r = np.concatenate([np.zeros(d), m[:-d]])
    return np.stack([m, 0.85 * r + 0.15 * m], axis=1)


EDITORIAS = {
    # tensão contida: menor, pulso de bumbo e chimbal
    "politica": {"bpm": 96, "prog": [("A", True), ("F", False), ("D", True), ("E", False)], "pad": 0.5, "baixo": 0.6,
                 "bumbo": 0.8, "chimbal": 0.25, "arpejo": ("pluck", 2, 0.25), "corte": 1200},
    # épico: menor com bumbo em todos os tempos e sino
    "eleicoes": {"bpm": 104, "prog": [("D", True), ("Bb", False), ("F", False), ("C", False)], "pad": 0.6, "baixo": 0.7,
                 "bumbo": 0.9, "chimbal": 0.3, "arpejo": ("sino", 2, 0.25), "corte": 2000},
    # investigação: drone escuro, batimento e piano esparso
    "gerais": {"bpm": 72, "prog": [("E", True), ("E", True), ("C", False), ("B", False)], "pad": 0.6, "baixo": 0.7,
               "bumbo": 0.7, "bumbo_tempos": [0, 1], "arpejo": ("piano", 1, 0.35), "ordem": [0, 2, 1, 2], "corte": 900},
    # noticiário: maior, dedilhado rápido
    "economia": {"bpm": 112, "prog": [("C", False), ("G", False), ("A", True), ("F", False)], "pad": 0.35, "baixo": 0.6,
                 "bumbo": 0.6, "chimbal": 0.3, "arpejo": ("pluck", 4, 0.3), "corte": 1800},
    # esperança: sino e pad maior, sem bateria
    "educacao": {"bpm": 90, "prog": [("F", False), ("C", False), ("G", False), ("A", True)], "pad": 0.5, "baixo": 0.4,
                 "arpejo": ("sino", 2, 0.4), "ordem": [0, 1, 2, 1, 2, 1], "corte": 2200},
    # emoção: piano lento sobre pad suave
    "saude": {"bpm": 70, "prog": [("A", True), ("F", False), ("C", False), ("G", False)], "pad": 0.35, "baixo": 0.4,
              "arpejo": ("piano", 2, 0.45), "corte": 1200},
    # América Latina: violão dedilhado em menor com clave 3-2
    "america_latina": {"bpm": 100, "prog": [("D", True), ("A", False), ("D", True), ("G", True)], "pad": 0.2, "baixo": 0.6,
                       "bumbo": 0.5, "bumbo_tempos": [0, 2], "clave": 0.35, "arpejo": ("pluck", 4, 0.4),
                       "ordem": [0, 2, 1, 2], "brilho": 0.997, "corte": 1000},
    # da roça: viola dedilhada em compasso ternário, maior
    "roca": {"bpm": 92, "tempos": 3, "prog": [("G", False), ("C", False), ("D", False), ("G", False)], "pad": 0.2,
             "baixo": 0.5, "arpejo": ("pluck", 2, 0.45), "ordem": [0, 1, 2, 1, 2, 1], "arp_oit": 4, "brilho": 0.998,
             "corte": 1000},
}


def main() -> None:
    SAIDA.mkdir(exist_ok=True)
    for ed, cfg in EDITORIAS.items():
        st = estereo(compor(cfg))
        pcm = (st * 32767).astype("<i2")
        with wave.open(str(SAIDA / f"{ed}.wav"), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(SAIDA / f"{ed}.wav"),
                        "-c:a", "aac", "-b:a", "160k", str(SAIDA / f"{ed}.m4a")], check=True)
        (SAIDA / f"{ed}.wav").unlink()
        print(ed, "ok")


if __name__ == "__main__":
    main()
