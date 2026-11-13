"""Punto di ingresso: `python3 -m bhs [--dry-run] [--diagnosi]`."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .cli import applica, testo_elenco
from .detect import raccogli, testo_diagnosi
from .giochi import (applica_config, carica_guide, guida_per_id, ripristina_config, testo_guida, testo_rapporti,
                     trova_file)
from .profiles import carica_profili, profilo_per_id, trova_profilo


def _guida_da_console(ident: str, profilo: str | None, azione: str, dry_run: bool) -> int:
    """`--guida`, `--imposta-gioco` e `--ripristina-gioco`: 0 ok, 1 errore su un file, 2 richiesta non valida.

    Un file senza copia da ripristinare non è un errore.
    """
    profilo = profilo or trova_profilo(carica_profili(), raccogli().dmi).id
    guide = carica_guide(profilo)
    g = guida_per_id(guide, ident)
    if g is None:
        print(f"Guida sconosciuta: {ident}. Guide disponibili: {', '.join(x.id for x in guide)}", file=sys.stderr)
        return 2
    if azione == "leggi":
        print(testo_guida(g))
        return 0
    if g.config is None:
        print(f"«{g.nome}» non ha impostazioni automatiche per il profilo {profilo}.", file=sys.stderr)
        return 2
    file = trova_file(g.config)
    if not file:
        print(f"Non trovo i file di impostazioni di {g.nome} ({', '.join(g.config.file)}).\n"
              "Aggiungi il gioco a Steam, avvialo una volta fino al menu, chiudilo e riprova.", file=sys.stderr)
        return 1
    rapporti = ripristina_config(file, dry_run) if azione == "ripristina" else applica_config(g.config, file, dry_run)
    print(testo_rapporti(rapporti, dry_run))
    return 1 if any(r.errore for r in rapporti) else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bhs", description="Configurazione guidata di Bazzite (KDE Plasma) per handheld.")
    ap.add_argument("--dry-run", action="store_true", help="mostra cosa farebbe senza modificare nulla")
    ap.add_argument("--diagnosi", action="store_true", help="stampa il rapporto di sistema e esce (senza interfaccia)")
    ap.add_argument("--elenco", action="store_true", help="elenca i tweak disponibili e il loro stato, senza interfaccia")
    ap.add_argument("--applica", nargs="+", metavar="ID",
                    help="applica solo questi tweak, senza interfaccia (utile da console con lo schermo nero)")
    ap.add_argument("--profilo", metavar="ID",
                    help="fissa il profilo del dispositivo (usato dagli script dedicati): onexplayer1s o rogallyz1x")
    ap.add_argument("--guide", action="store_true", help="apre la finestra direttamente sulle guide ai giochi")
    ap.add_argument("--guida", metavar="GIOCO", help="stampa la guida passo passo di un gioco (rdr2, witcher3, skyrim)")
    ap.add_argument("--imposta-gioco", metavar="GIOCO",
                    help="scrive le impostazioni grafiche consigliate nel file del gioco (con --dry-run mostra solo cosa cambierebbe)")
    ap.add_argument("--ripristina-gioco", metavar="GIOCO",
                    help="rimette il file di impostazioni del gioco com'era prima di --imposta-gioco")
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
    for ident, azione in ((a.guida, "leggi"), (a.imposta_gioco, "imposta"), (a.ripristina_gioco, "ripristina")):
        if ident:
            return _guida_da_console(ident, a.profilo, azione, a.dry_run)

    try:
        from .gui import avvia
    except (ImportError, ValueError) as e:
        print(f"Impossibile caricare l'interfaccia grafica Qt (PySide6): {e}\n"
              "Assicurati che PySide6 sia installato nell'ambiente Python.", file=sys.stderr)
        return 2
    return avvia(a.dry_run, a.profilo, a.guide)


if __name__ == "__main__":
    raise SystemExit(main())
