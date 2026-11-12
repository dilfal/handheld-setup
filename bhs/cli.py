"""Modalità senza interfaccia: serve quando lo schermo è nero e si lavora da console (Ctrl+Alt+F3)."""

from __future__ import annotations

from typing import Callable

from .detect import Sistema
from .runner import Azione, esegui_azioni
from .tweaks import tutti_i_tweak

ETICHETTE = {"attivo": "già attivo", "inattivo": "da applicare", "non_supportato": "non supportato qui",
             "in_attesa": "in attesa di riavvio", "sconosciuto": "stato sconosciuto"}


def testo_elenco(s: Sistema) -> str:
    righe = ["Tweak disponibili (usa l'ID con --applica):"]
    tweaks = tutti_i_tweak()
    largo = max(len(i) for i in tweaks)   # colonne allineate anche con gli ID più lunghi
    for t in tweaks.values():
        stato = ETICHETTE.get(t.stato(s), "?")
        extra = "  [riavvio]" if t.richiede_riavvio else ""
        righe.append(f"  {t.id:<{largo}} {stato:<20} {t.titolo}{extra}")
    return "\n".join(righe)


def applica(ids: list[str], dry_run: bool, s: Sistema, log: Callable[[str], None]) -> int:
    """Applica i tweak indicati. Codice di uscita: 0 ok, 1 errore di un comando, 2 richiesta non valida."""
    tweaks = tutti_i_tweak()
    sconosciuti = [i for i in ids if i not in tweaks]
    if sconosciuti:
        log(f"Tweak sconosciuti: {', '.join(sconosciuti)}. Usa --elenco per vedere gli ID.")
        return 2
    azioni: list[Azione] = []
    for i in ids:
        t = tweaks[i]
        if t.stato(s) == "non_supportato":
            log(f"«{t.id}» non è supportato su questo sistema: salto.")
            continue
        comandi = t.comandi_per(s)
        if not comandi:
            log(f"«{t.id}» non ha comandi per questo sistema: salto.")
            continue
        azioni += [Azione(t.titolo if n == 0 else f"{t.titolo} ({n + 1})", c) for n, c in enumerate(comandi)]
    if not azioni:
        log("Niente da fare.")
        return 2
    risultati = esegui_azioni(azioni, dry_run, log)
    errori = [r for r in risultati if r.esito == "errore"]
    if errori:
        log(f"\n{len(errori)} comandi non riusciti.")
        return 1
    if any(tweaks[i].richiede_riavvio for i in ids) and not dry_run:
        log("\nFatto. Per applicare le modifiche riavvia: systemctl reboot")
    return 0
