"""Profili dei dispositivi, letti da data/profiles/*.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATI = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Profilo:
    id: str
    nome: str
    descrizione: str
    fornitori: list[str] = field(default_factory=list)
    prodotti: list[str] = field(default_factory=list)
    consigliati: list[str] = field(default_factory=list)
    avanzati: list[str] = field(default_factory=list)
    note: list[str] = field(default_factory=list)

    def corrisponde(self, dmi: dict[str, Optional[str]]) -> bool:
        """Confronta i campi DMI: fornitore di sistema o di scheda, prodotto o nome scheda."""
        if not self.fornitori and not self.prodotti:
            return False  # il profilo generico non si abbina da solo
        f = " ".join(dmi.get(k) or "" for k in ("fornitore", "scheda_fornitore")).lower()
        p = " ".join(dmi.get(k) or "" for k in ("prodotto", "scheda_nome")).lower()
        ok_f = not self.fornitori or any(x.lower() in f for x in self.fornitori)
        ok_p = not self.prodotti or any(x.lower() in p for x in self.prodotti)
        return ok_f and ok_p


def carica_profili(cartella: Path = DATI / "profiles") -> list[Profilo]:
    profili = []
    for file in sorted(cartella.glob("*.toml")):
        with file.open("rb") as fh:
            d = tomllib.load(fh)
        m = d.get("match", {})
        t = d.get("tweak", {})
        profili.append(Profilo(
            id=d["id"], nome=d["nome"], descrizione=d.get("descrizione", ""),
            fornitori=m.get("fornitori", []), prodotti=m.get("prodotti", []),
            consigliati=t.get("consigliati", []), avanzati=t.get("avanzati", []),
            note=d.get("note", []),
        ))
    return profili


def profilo_per_id(profili: list[Profilo], ident: str) -> Optional[Profilo]:
    return next((p for p in profili if p.id == ident), None)


def avviso_incoerenza(profilo: Profilo, dmi: dict[str, Optional[str]]) -> Optional[str]:
    """Testo di avviso se il dispositivo non sembra quello del profilo scelto (il profilo generico non ha controlli)."""
    if not profilo.fornitori and not profilo.prodotti:
        return None
    if profilo.corrisponde(dmi):
        return None
    letto = f"{dmi.get('fornitore') or 'sconosciuto'} · {dmi.get('prodotto') or 'sconosciuto'}"
    return (f"Questo script è fatto per {profilo.nome}, ma il dispositivo risulta «{letto}». "
            "Se prosegui, alcune impostazioni potrebbero non essere adatte.")


def trova_profilo(profili: list[Profilo], dmi: dict[str, Optional[str]]) -> Profilo:
    for p in profili:
        if p.corrisponde(dmi):
            return p
    return next(p for p in profili if p.id == "generico")
