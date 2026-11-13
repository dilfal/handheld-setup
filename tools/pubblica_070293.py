"""Sincronizza gli script, le scorciatoie (/oxp, /ally, /bhs) e le guide HTML sul sito 070293.xyz (siti-web/070293)."""

from __future__ import annotations

import shutil
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
SITO = Path(r"C:\Users\df\Dev\GitHub\siti-web\070293")

SCORCIATOIE = {
    "oxp": "install-onexplayer.sh",
    "ally": "install-rog-ally.sh",
    "bhs": "install.sh",
}


# Indirizzi brevi da aprire sul telefono (l'app li mostra nelle guide dei giochi): cartella -> pagina di destinazione.
SCORCIATOIE_PAGINE = {
    "giochi-oxp": "ottimizzazione_onexplayer_1s.html",
    "giochi-ally": "ottimizzazione_rog_ally.html",
}

PAGINA_RIMANDO = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0; url=/guide/{pagina}">
    <title>Guida ai giochi | Bazzite Handheld Setup</title>
</head>
<body>
    <p>Apro la guida ai giochi… Se non si apre da sola, <a href="/guide/{pagina}">tocca qui</a>.</p>
</body>
</html>
"""


def sincronizza(dest: Path = SITO) -> None:
    if not dest.is_dir():
        raise SystemExit(f"Cartella del sito non trovata: {dest}")

    # 1. Script completi e scorciatoie corte (sempre con fine riga LF per Linux/POSIX sh)
    for corto, script_nome in SCORCIATOIE.items():
        contenuto = (RADICE / script_nome).read_text(encoding="utf-8")
        (dest / script_nome).write_text(contenuto, encoding="utf-8", newline="\n")
        (dest / corto).write_text(contenuto, encoding="utf-8", newline="\n")

    # 2. Guide HTML sia nella radice (070293.xyz/) sia in /guide/ (070293.xyz/guide/)
    guide_dest = dest / "guide"
    guide_dest.mkdir(exist_ok=True)
    for html in (RADICE / "guide").glob("*.html"):
        testo = html.read_text(encoding="utf-8")
        (dest / html.name).write_text(testo, encoding="utf-8", newline="\n")
        (guide_dest / html.name).write_text(testo, encoding="utf-8", newline="\n")

    # 2b. Indirizzi brevi per il telefono: 070293.xyz/giochi-oxp e 070293.xyz/giochi-ally rimandano alla guida
    for cartella, pagina in SCORCIATOIE_PAGINE.items():
        (dest / cartella).mkdir(exist_ok=True)
        (dest / cartella / "index.html").write_text(PAGINA_RIMANDO.format(pagina=pagina), encoding="utf-8", newline="\n")

    # 2c. Utility Windows (OneXPlayer 1S): 070293.xyz/oxp-win serve lo script completo, byte per byte
    #     (ASCII senza BOM, LF: con il BOM `irm | iex` fallisce). I driver restano nelle Release di GitHub.
    shutil.copyfile(RADICE / "windows" / "oxp1s.ps1", dest / "oxp-win")

    # 3. Garantisce CNAME e .nojekyll
    (dest / "CNAME").write_text("070293.xyz\n", encoding="utf-8", newline="\n")
    (dest / ".nojekyll").write_text("", encoding="utf-8", newline="\n")
    (dest / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8", newline="\n")
    print(f"Sincronizzato {dest} con {RADICE}")


if __name__ == "__main__":
    sincronizza()
