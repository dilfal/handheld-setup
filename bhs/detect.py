"""Rilevamento di sistema, dispositivo e strumenti presenti.

Niente ipotesi: ogni dato viene letto dal sistema. Se non si riesce a leggerlo
resta `None` (o una lista vuota) e l'interfaccia lo mostra come "sconosciuto".
Le funzioni accettano `root` e `esegui` per poter essere provate su qualsiasi PC.
"""

from __future__ import annotations

import glob
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

Esegui = Callable[[list[str]], Optional[str]]


def esegui_semplice(argv: list[str], timeout: int = 15) -> Optional[str]:
    """Lancia un comando e restituisce lo stdout, oppure None se fallisce."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def _leggi(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def leggi_os_release(root: Path = Path("/")) -> dict[str, str]:
    testo = _leggi(root / "etc" / "os-release") or ""
    dati: dict[str, str] = {}
    for riga in testo.splitlines():
        if "=" in riga and not riga.startswith("#"):
            k, v = riga.split("=", 1)
            dati[k.strip()] = v.strip().strip('"')
    return dati


def leggi_dmi(root: Path = Path("/")) -> dict[str, Optional[str]]:
    base = root / "sys" / "class" / "dmi" / "id"
    return {
        "fornitore": _leggi(base / "sys_vendor"),
        "prodotto": _leggi(base / "product_name"),
        "versione": _leggi(base / "product_version"),
        "scheda_fornitore": _leggi(base / "board_vendor"),  # il kernel riconosce i OneXPlayer da qui
        "scheda_nome": _leggi(base / "board_name"),
        "bios": _leggi(base / "bios_version"),
    }


def flatpak_installati(esegui: Esegui = esegui_semplice) -> set[str]:
    out = esegui(["flatpak", "list", "--app", "--columns=application"])
    if not out:
        return set()
    return {r.strip() for r in out.splitlines() if r.strip()}


def parametri_kernel(root: Path = Path("/")) -> list[str]:
    testo = _leggi(root / "proc" / "cmdline") or ""
    return testo.split()


def soglie_carica(root: Path = Path("/")) -> list[str]:
    """File sysfs che permettono di limitare la carica (se il kernel li espone)."""
    modello = str(root / "sys" / "class" / "power_supply" / "*" / "charge_control_end_threshold")
    return sorted(glob.glob(modello))


def leggi_soglia(percorso: str) -> Optional[str]:
    return _leggi(Path(percorso))


def retroilluminazione(root: Path = Path("/")) -> list[str]:
    """Dispositivi di /sys/class/backlight, come «nome (tipo, valore/massimo)»."""
    voci = []
    for d in sorted(glob.glob(str(root / "sys" / "class" / "backlight" / "*"))):
        p = Path(d)
        voci.append(f"{p.name} ({_leggi(p / 'type') or '?'}, "
                    f"{_leggi(p / 'brightness') or '?'}/{_leggi(p / 'max_brightness') or '?'})")
    return voci


QUIRK_GAMESCOPE = Path("usr") / "share" / "gamescope-session-plus" / "device-quirks"
_PANEL_TYPE = re.compile(r"^\s*(?:export\s+)?PANEL_TYPE=[\"']?(\w+)")


def quirk_pannello(prodotto: Optional[str], root: Path = Path("/")) -> Optional[str]:
    """Tipo di pannello (`internal`/`external`) che la sessione di gamescope assegna a questo prodotto.

    Il file è uno script bash: si cerca la riga che nomina il prodotto come voce di un elenco e si prende
    il primo PANEL_TYPE delle righe seguenti. Se non si trova nulla resta None (nessuna ipotesi).
    """
    testo = _leggi(root / QUIRK_GAMESCOPE)
    if not testo or not prodotto:
        return None
    voce = re.compile(r"[\":]" + re.escape(prodotto).replace(r"\ ", " ").replace(" ", r"\\? ") + r"[\":]")
    righe = testo.splitlines()
    for n, riga in enumerate(righe):
        if riga.lstrip().startswith("#") or not voce.search(riga):
            continue
        for seguente in righe[n:n + 8]:
            m = _PANEL_TYPE.match(seguente)
            if m:
                return m.group(1)
    return None


def pannello_utente(home: Path) -> Optional[str]:
    """PANEL_TYPE scelto dall'utente in ~/.config/environment.d/*.conf (vince l'ultimo, come nella sessione)."""
    valore = None
    for f in sorted(glob.glob(str(home / ".config" / "environment.d" / "*.conf"))):
        for riga in (_leggi(Path(f)) or "").splitlines():
            m = _PANEL_TYPE.match(riga)
            if m:
                valore = m.group(1)
    return valore


def gpu(esegui: Esegui = esegui_semplice) -> list[str]:
    out = esegui(["lspci", "-nn"])
    if not out:
        return []
    return [r.split(": ", 1)[-1] for r in out.splitlines() if "VGA" in r or "3D controller" in r or "Display" in r]


def immagine_ostree(esegui: Esegui = esegui_semplice) -> Optional[str]:
    """Immagine Bazzite in uso (es. ostree-image-signed:docker://ghcr.io/ublue-os/bazzite-deck-gnome:stable)."""
    out = esegui(["rpm-ostree", "status", "--booted"])
    if not out:
        return None
    for riga in out.splitlines():
        riga = riga.strip().lstrip("●").strip()
        if riga.startswith(("ostree", "docker://", "ghcr.io")):
            return riga
    return None


BREW_BIN = "/home/linuxbrew/.linuxbrew/bin/brew"  # dove Bazzite mette Homebrew (non sempre nel PATH di una sessione grafica)


def pacchetti_aggiunti(esegui: Esegui = esegui_semplice) -> set[str]:
    """Pacchetti aggiunti al sistema con `rpm-ostree install`, anche se attesi dal prossimo riavvio."""
    out = esegui(["rpm-ostree", "status"])
    if not out:
        return set()
    trovati: set[str] = set()
    dentro = False
    for riga in out.splitlines():
        if "LayeredPackages:" in riga:
            trovati.update(riga.split("LayeredPackages:", 1)[1].split())
            dentro = True
        elif dentro and riga.startswith((" ", "	")) and ":" not in riga:
            trovati.update(riga.split())   # continuazione dell'elenco su più righe
        else:
            dentro = False
    return trovati


def servizio_attivo(nome: str, esegui: Esegui = esegui_semplice) -> bool:
    out = esegui(["systemctl", "is-enabled", nome])
    return bool(out) and out.strip() == "enabled"


STRUMENTI = [
    "flatpak", "ujust", "rpm-ostree", "steamosctl", "hhd", "steamos-manager", "asusctl",
    "powerprofilesctl", "pkexec", "distrobox", "brew", "steam", "mullvad", "curl",
    "plasma-apply-colorscheme", "kscreen-doctor", "kwriteconfig6", "kreadconfig6", "qdbus6"
]


@dataclass
class Sistema:
    os: dict[str, str] = field(default_factory=dict)
    dmi: dict[str, Optional[str]] = field(default_factory=dict)
    kernel: Optional[str] = None
    immagine: Optional[str] = None
    gpu: list[str] = field(default_factory=list)
    strumenti: dict[str, bool] = field(default_factory=dict)
    flatpak: set[str] = field(default_factory=set)
    param_kernel: list[str] = field(default_factory=list)
    soglie_carica: list[str] = field(default_factory=list)
    brew: Optional[str] = None                      # comando per Homebrew ("brew" o il percorso completo)
    layer: set[str] = field(default_factory=set)    # pacchetti aggiunti con rpm-ostree
    mullvad_servizio: bool = False                  # mullvad-daemon.service abilitato
    retroilluminazione: list[str] = field(default_factory=list)
    quirk_pannello: Optional[str] = None            # PANEL_TYPE che la sessione di gamescope dà a questo prodotto

    @property
    def e_bazzite(self) -> bool:
        blocco = " ".join(self.os.get(k, "") for k in ("ID", "NAME", "VARIANT_ID", "ID_LIKE")).lower()
        return "bazzite" in blocco or "bazzite" in (self.immagine or "").lower()

    @property
    def orientamento_pannello(self) -> Optional[str]:
        for p in self.param_kernel:
            if "panel_orientation" in p:
                return p
        return None


def raccogli(root: Path = Path("/"), esegui: Esegui = esegui_semplice,
             esiste: Callable[[str], bool] = lambda n: shutil.which(n) is not None) -> Sistema:
    kernel = esegui(["uname", "-r"])
    dmi = leggi_dmi(root)
    return Sistema(
        retroilluminazione=retroilluminazione(root),
        quirk_pannello=quirk_pannello(dmi.get("prodotto"), root),
        os=leggi_os_release(root),
        dmi=dmi,
        kernel=kernel.strip() if kernel else None,
        immagine=immagine_ostree(esegui),
        gpu=gpu(esegui),
        strumenti={n: esiste(n) for n in STRUMENTI},
        flatpak=flatpak_installati(esegui),
        param_kernel=parametri_kernel(root),
        soglie_carica=soglie_carica(root),
        brew="brew" if esiste("brew") else (BREW_BIN if (root / BREW_BIN.lstrip("/")).exists() else None),
        layer=pacchetti_aggiunti(esegui),
        mullvad_servizio=servizio_attivo("mullvad-daemon.service", esegui),
    )


def testo_diagnosi(s: Sistema) -> str:
    """Rapporto leggibile e incollabile in una segnalazione: non modifica nulla."""
    n = lambda v: v if v else "sconosciuto"
    righe = [
        "== Diagnosi Bazzite Handheld Setup ==",
        f"Sistema:      {n(s.os.get('PRETTY_NAME'))} (Bazzite: {'sì' if s.e_bazzite else 'no/non rilevato'})",
        f"Immagine:     {n(s.immagine)}",
        f"Kernel:       {n(s.kernel)}",
        f"Fornitore:    {n(s.dmi.get('fornitore'))}",
        f"Prodotto:     {n(s.dmi.get('prodotto'))}",
        f"Versione:     {n(s.dmi.get('versione'))}",
        f"Scheda:       {n(s.dmi.get('scheda_fornitore'))} · {n(s.dmi.get('scheda_nome'))}",
        f"GPU:          {'; '.join(s.gpu) if s.gpu else 'sconosciuta'}",
        f"Orientamento: {n(s.orientamento_pannello)}",
        "Luminosità:   " + ("; ".join(s.retroilluminazione) if s.retroilluminazione
                            else "nessun dispositivo in /sys/class/backlight"),
        f"Pannello:     quirk di gamescope = {s.quirk_pannello or 'nessuno trovato'}"
        f" · scelta utente (PANEL_TYPE) = {pannello_utente(Path.home()) or 'nessuna'}",
        "Limite carica: " + (", ".join(f"{p} = {leggi_soglia(p) or '?'}" for p in s.soglie_carica)
                             if s.soglie_carica else "non esposto dal kernel"),
        "Strumenti:    " + ", ".join(f"{k}={'sì' if v else 'no'}" for k, v in s.strumenti.items()),
        f"Flatpak installati: {len(s.flatpak)}",
        f"Homebrew:     {s.brew or 'non trovato'}",
        f"Aggiunti con rpm-ostree: {', '.join(sorted(s.layer)) if s.layer else 'nessuno'}",
    ]
    return "\n".join(righe)
