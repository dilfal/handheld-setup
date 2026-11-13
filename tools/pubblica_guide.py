"""Sincronizza le guide HTML sul sito guide.070293.xyz (siti-web/guide.070293.xyz).

Le pagine vengono da guide/*.html (tranne guide/index.html, che è l'indice del sito 070293.xyz) e da
guide/sottodominio/*.html (compreso l'indice di guide.070293.xyz). Sul sito stanno tutte nella radice.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

RADICE = Path(__file__).resolve().parent.parent
SITO = Path(r"C:\Users\df\Dev\GitHub\siti-web\guide.070293.xyz")

INDICE = "index.html"
ATTRIBUTI_COLLEGAMENTO = ("href", "src")

README = """# guide.070293.xyz
Sito delle guide, generato da `dilfal/handheld-setup` con `python tools/pubblica_guide.py`.
Non modificare a mano: le modifiche vanno fatte nel repository sorgente.
"""


class RaccoltaCollegamenti(HTMLParser):
    """Raccoglie i valori di href e src di una pagina."""

    def __init__(self) -> None:
        super().__init__()
        self.collegamenti: list[str] = []

    def handle_starttag(self, tag, attrs):
        for nome, valore in attrs:
            if nome in ATTRIBUTI_COLLEGAMENTO and valore:
                self.collegamenti.append(valore.strip())


def raccogli_pagine() -> dict[str, Path]:
    """Restituisce {nome file: percorso sorgente}; errore se due file hanno lo stesso nome."""
    pagine: dict[str, Path] = {}
    sorgenti = [p for p in sorted((RADICE / "guide").glob("*.html")) if p.name != INDICE]
    sorgenti += sorted((RADICE / "guide" / "sottodominio").glob("*.html"))
    for percorso in sorgenti:
        if percorso.name in pagine:
            raise SystemExit(
                f"Nome duplicato: {percorso.name} esiste in {pagine[percorso.name].relative_to(RADICE)} "
                f"e in {percorso.relative_to(RADICE)}"
            )
        pagine[percorso.name] = percorso
    return pagine


def collegamenti_locali(testo: str) -> list[str]:
    """Collegamenti href/src che puntano a un file locale (no http(s), mailto, #, data, altri schemi)."""
    raccolta = RaccoltaCollegamenti()
    raccolta.feed(testo)
    locali = []
    for valore in raccolta.collegamenti:
        parti = urlsplit(valore)
        if parti.scheme or parti.netloc or not parti.path:
            continue
        locali.append(valore)
    return locali


def controlla(pagine: dict[str, Path]) -> list[str]:
    """Elenco dei problemi trovati (vuoto se tutto a posto)."""
    problemi: list[str] = []
    if INDICE not in pagine:
        return [f"manca l'indice: guide/sottodominio/{INDICE}"]
    testi = {nome: percorso.read_text(encoding="utf-8") for nome, percorso in pagine.items()}

    # (a) ogni pagina pubblicata (tranne l'indice) è collegata dall'indice
    dall_indice = set()
    for valore in collegamenti_locali(testi[INDICE]):
        dall_indice.add(unquote(urlsplit(valore).path).removeprefix("./"))
    for nome in pagine:
        if nome != INDICE and nome not in dall_indice:
            problemi.append(f"{nome}: non è collegata dall'indice ({INDICE})")

    # (b) ogni collegamento locale punta a un file che sarà pubblicato
    for nome, testo in testi.items():
        for valore in collegamenti_locali(testo):
            percorso = unquote(urlsplit(valore).path).removeprefix("./")
            if percorso not in pagine:
                problemi.append(f"{nome}: collegamento locale non pubblicato: {valore}")
    return problemi


def sincronizza(dest: Path = SITO) -> int:
    if not dest.is_dir():
        raise SystemExit(f"Cartella del sito non trovata: {dest}")

    pagine = raccogli_pagine()
    problemi = controlla(pagine)
    if problemi:
        print("Pubblicazione annullata, problemi trovati:")
        for problema in problemi:
            print(f"  - {problema}")
        return 1

    # 1. Pagine nella radice del sito (UTF-8, fine riga LF)
    for nome, percorso in pagine.items():
        testo = percorso.read_text(encoding="utf-8")
        (dest / nome).write_text(testo, encoding="utf-8", newline="\n")

    # 2. Toglie le pagine che non sono più nella sorgente
    for vecchia in dest.glob("*.html"):
        if vecchia.name not in pagine:
            vecchia.unlink()
            print(f"Rimossa pagina non più in sorgente: {vecchia.name}")

    # 3. File di servizio del sito
    (dest / "CNAME").write_text("guide.070293.xyz\n", encoding="utf-8", newline="\n")
    (dest / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    (dest / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8", newline="\n")
    (dest / ".gitignore").write_text("desktop.ini\n", encoding="utf-8", newline="\n")
    (dest / "README.md").write_text(README, encoding="utf-8", newline="\n")

    print(f"Sincronizzate {len(pagine)} pagine in {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(sincronizza())
