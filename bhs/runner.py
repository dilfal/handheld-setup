"""Esecuzione delle azioni, con simulazione (--dry-run) e log riga per riga."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Azione:
    titolo: str
    argv: Optional[list[str]]     # None = solo informativa (es. app "manuale")
    nota: Optional[str] = None


@dataclass
class Risultato:
    azione: Azione
    esito: str                    # "ok" | "errore" | "simulata" | "saltata"
    codice: Optional[int] = None


def descrivi_comando(argv: list[str]) -> list[str]:
    """Righe di log per un comando; un argomento su più righe (uno script) viene mostrato come blocco."""
    prima = []
    for i, x in enumerate(argv):
        if "\n" in x:
            testa = "  $ " + " ".join(prima) + " <<script>>"
            corpo = ["      " + r for r in x.rstrip("\n").splitlines()]
            coda = [" ".join(shlex.quote(y) for y in argv[i + 1:])] if i + 1 < len(argv) else []
            return [testa, *corpo, *[("  " + c) for c in coda if c]]
        prima.append(shlex.quote(x))
    return ["  $ " + " ".join(prima)]


def riassunto_comando(argv: list[str] | None) -> str:
    """Il comando su una riga sola; un argomento su più righe (uno script) diventa «‹script›»."""
    if not argv:
        return ""
    return " ".join("‹script›" if "\n" in x else shlex.quote(x) for x in argv)


def esegui_azioni(azioni: list[Azione], dry_run: bool,
                  log: Callable[[str], None],
                  avanzamento: Callable[[int, int, str], None] = lambda i, n, t: None) -> list[Risultato]:
    risultati: list[Risultato] = []
    n = len(azioni)
    for i, a in enumerate(azioni, 1):
        avanzamento(i - 1, n, a.titolo)
        log(f"\n▶ {a.titolo}")
        if a.argv is None:
            log(f"  Da fare a mano. {a.nota or ''}".rstrip())
            risultati.append(Risultato(a, "saltata"))
            continue
        for riga in descrivi_comando(a.argv):
            log(riga)
        if dry_run:
            log("  (simulazione: non eseguito)")
            risultati.append(Risultato(a, "simulata"))
            continue
        try:
            with subprocess.Popen(a.argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                  errors="replace") as p:
                assert p.stdout is not None
                for riga in p.stdout:
                    log("  " + riga.rstrip())
                codice = p.wait()
        except OSError as e:
            log(f"  ✗ impossibile avviare: {e}")
            risultati.append(Risultato(a, "errore"))
            continue
        esito = "ok" if codice == 0 else "errore"
        log(f"  {'✓' if esito == 'ok' else '✗'} codice {codice}")
        risultati.append(Risultato(a, esito, codice))
    avanzamento(n, n, "Fine")
    return risultati
