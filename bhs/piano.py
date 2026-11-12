"""Dalla selezione dell'utente all'elenco ordinato di azioni da eseguire."""

from __future__ import annotations

from .catalog import App
from .detect import Sistema
from .runner import Azione
from .tweaks import Tweak

FLATHUB_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"


def nota_manuale(app: App) -> str:
    if app.tipo == "brew":
        return "Homebrew non trovato: installalo da https://brew.sh e rilancia lo script."
    return f"Apri {app.rif}"


def costruisci_piano(catalogo: list[App], tweaks: dict[str, Tweak], sel_app: set[str], sel_tweak: set[str],
                     sistema: Sistema) -> list[Azione]:
    """App nell'ordine del catalogo, poi i tweak nell'ordine in cui sono definiti (non quello casuale dell'insieme).

    Se si installa almeno un Flatpak si collega prima il repository Flathub dell'utente: i comandi usano `--user`
    e, senza quel repository, fallirebbero con «remote flathub non trovato». L'operazione è idempotente.
    """
    azioni: list[Azione] = []
    scelte = [a for a in catalogo if a.id in sel_app]
    if any(a.tipo == "flatpak" for a in scelte):
        azioni.append(Azione("Collega Flathub (utente)",
                             ["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB_URL]))
    for app in scelte:
        cmd = app.comando(sistema)
        azioni.append(Azione(f"Installa {app.nome}", cmd, nota=nota_manuale(app) if cmd is None else None))
    for tid, t in tweaks.items():
        if tid not in sel_tweak:
            continue
        for i, cmd in enumerate(t.comandi_per(sistema)):
            azioni.append(Azione(t.titolo if i == 0 else f"{t.titolo} ({i + 1})", cmd))
    return azioni
