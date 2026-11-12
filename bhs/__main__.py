"""Punto di ingresso: `python3 -m bhs [--dry-run] [--diagnosi]`."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .cli import applica, testo_elenco
from .detect import raccogli, testo_diagnosi
from .profiles import carica_profili, profilo_per_id


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bhs", description="Configurazione guidata di Bazzite (KDE Plasma) per handheld.")
    ap.add_argument("--dry-run", action="store_true", help="mostra cosa farebbe senza modificare nulla")
    ap.add_argument("--diagnosi", action="store_true", help="stampa il rapporto di sistema e esce (senza interfaccia)")
    ap.add_argument("--elenco", action="store_true", help="elenca i tweak disponibili e il loro stato, senza interfaccia")
    ap.add_argument("--applica", nargs="+", metavar="ID",
                    help="applica solo questi tweak, senza interfaccia (utile da console con lo schermo nero)")
    ap.add_argument("--profilo", metavar="ID",
                    help="fissa il profilo del dispositivo (usato dagli script dedicati): onexplayer1s o rogallyz1x")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = ap.parse_args(argv)

    if a.diagnosi:
        print(testo_diagnosi(raccogli()))
        return 0
    if a.elenco:
        print(testo_elenco(raccogli()))
        return 0
    if a.applica:
        return applica(a.applica, a.dry_run, raccogli(), print)

    if a.profilo and profilo_per_id(carica_profili(), a.profilo) is None:
        ids = ", ".join(p.id for p in carica_profili())
        print(f"Profilo sconosciuto: {a.profilo}. Profili disponibili: {ids}", file=sys.stderr)
        return 2

    try:
        from .gui import avvia
    except (ImportError, ValueError) as e:
        print(f"Impossibile caricare l'interfaccia grafica Qt (PySide6): {e}\n"
              "Assicurati che PySide6 sia installato nell'ambiente Python.", file=sys.stderr)
        return 2
    return avvia(a.dry_run, a.profilo)


if __name__ == "__main__":
    raise SystemExit(main())
