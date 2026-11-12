"""Genera i due installatori dedicati a partire da install.sh.

    python3 tools/genera_installatori.py            # scrive install-onexplayer.sh e install-rog-ally.sh
    python3 tools/genera_installatori.py --verifica # esce con 1 se i file esistenti non coincidono con install.sh

Gli script dedicati differiscono da install.sh solo per due variabili (profilo e nome) e per il nome del file
nei commenti: così una correzione in install.sh si propaga a entrambi, e la verifica impedisce che si disallineino.
"""

from __future__ import annotations

import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

# file generato -> (id del profilo, nome mostrato nel menu, scorciatoia su 070293.xyz)
DEDICATI = {
    "install-onexplayer.sh": ("onexplayer1s", "OneXPlayer 1S", "oxp"),
    "install-rog-ally.sh": ("rogallyz1x", "ROG Ally", "ally"),
}


def genera(nome_file: str, base: str | None = None) -> str:
    ident, nome, corto = DEDICATI[nome_file]
    testo = base if base is not None else (RADICE / "install.sh").read_text(encoding="utf-8")
    for vecchio, nuovo in (('PROFILO_FISSO=""', f'PROFILO_FISSO="{ident}"'), ('NOME_FISSO=""', f'NOME_FISSO="{nome}"')):
        if testo.count(vecchio) != 1:
            raise SystemExit(f"install.sh: attesa esattamente una riga {vecchio}")
        testo = testo.replace(vecchio, nuovo)
    testo = testo.replace("070293.xyz/bhs", f"070293.xyz/{corto}")
    # Prima il nome del file negli esempi d'uso, poi il paragrafo che presenta lo script generico, che diventa
    # una riga sullo script dedicato (e cita install.sh, quindi va inserita dopo la sostituzione).
    righe = testo.replace("install.sh", nome_file).splitlines(keepends=True)
    inizio = next(i for i, r in enumerate(righe) if r.startswith("# Questo è lo script GENERICO"))
    fine = next(i for i, r in enumerate(righe) if r.startswith("#   install-onexplayer.sh"))
    righe[inizio:fine + 1] = [f"# Script DEDICATO a {nome}: generato da install.sh con tools/genera_installatori.py, non modificarlo a mano.\n"]
    testo = "".join(righe)
    if ident != "onexplayer1s":  # la correzione dello schermo nero riguarda solo il OneXPlayer
        testo = testo.replace("--applica intel_norbc   # da console (Ctrl+Alt+F3) se lo schermo è nero",
                              "--elenco              # mostra i tweak e il loro stato")
    return testo


def main(argv: list[str]) -> int:
    verifica = "--verifica" in argv
    base = (RADICE / "install.sh").read_text(encoding="utf-8")
    ok = True
    for nome_file in DEDICATI:
        atteso = genera(nome_file, base)
        percorso = RADICE / nome_file
        if verifica:
            attuale = percorso.read_text(encoding="utf-8") if percorso.exists() else None
            if attuale != atteso:
                print(f"DISALLINEATO: {nome_file} (rilancia tools/genera_installatori.py)")
                ok = False
        else:
            percorso.write_text(atteso, encoding="utf-8", newline="\n")
            print(f"scritto {nome_file}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
