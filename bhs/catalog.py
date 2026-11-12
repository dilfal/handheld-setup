"""Catalogo delle app candidate, letto da data/catalog.toml."""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .detect import BREW_BIN, Sistema
from .profiles import DATI

CATEGORIE = {
    "launcher": "Launcher di giochi",
    "emulazione": "Emulazione",
    "handheld": "Strumenti per l'handheld",
    "utilita": "Utilità e multimedia",
}


@dataclass
class App:
    id: str
    nome: str
    descrizione: str
    categoria: str
    tipo: str            # "flatpak" | "brew" | "ujust" | "manuale"
    rif: str             # ID Flatpak, pacchetto Homebrew, ricetta ujust o URL
    rileva: Optional[str] = None      # percorso (con ~) che prova che è già installata
    rileva_cmd: Optional[str] = None  # comando che prova che è già installata (per i pacchetti Homebrew)
    verificato: bool = True

    def installata(self, flatpak: set[str], home: Path = Path.home(),
                   trova=shutil.which, bin_brew: Path = Path(BREW_BIN).parent) -> bool:
        if self.tipo == "flatpak":
            return self.rif in flatpak
        if self.tipo == "brew":
            cmd = self.rileva_cmd or self.rif
            return bool(trova(cmd)) or (bin_brew / cmd).exists()
        if self.rileva:
            return Path(self.rileva.replace("~", str(home), 1)).exists()
        return False

    def comando(self, sistema: Optional[Sistema] = None) -> Optional[list[str]]:
        if self.tipo == "flatpak":
            return ["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", self.rif]
        if self.tipo == "brew":
            brew = sistema.brew if sistema is not None else "brew"
            return [brew, "install", self.rif] if brew else None   # senza Homebrew: istruzioni a mano
        if self.tipo == "ujust":
            return ["ujust", self.rif]
        return None  # "manuale": nessun comando, lo script mostra il link


def carica_catalogo(file: Path = DATI / "catalog.toml") -> list[App]:
    with file.open("rb") as fh:
        d = tomllib.load(fh)
    return [App(**voce) for voce in d.get("app", [])]
