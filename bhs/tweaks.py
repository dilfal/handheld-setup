"""Tweak di sistema: ognuno sa dire in che stato è e cosa eseguire.

Stati: "attivo", "inattivo", "in_attesa" (fatto, serve un riavvio), "non_supportato", "sconosciuto".
Un tweak con `comandi` vuoto è solo rilevamento: l'interfaccia lo mostra come "in arrivo".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .detect import Sistema, esegui_semplice, leggi_soglia, pannello_utente


@dataclass
class Tweak:
    id: str
    titolo: str
    descrizione: str
    comandi: list[list[str]] = field(default_factory=list)
    genera: Optional[Callable[[Sistema], list[list[str]]]] = None  # comandi che dipendono dal sistema
    stato: Callable[[Sistema], str] = lambda s: "sconosciuto"
    avanzato: bool = False
    richiede_riavvio: bool = False
    avviso: Optional[str] = None
    nota_stato: Optional[Callable[[Sistema], str]] = None  # testo in più accanto allo stato (es. la fase)

    def comandi_per(self, s: Sistema) -> list[list[str]]:
        return self.genera(s) if self.genera else self.comandi


def _schema_colori_kde(s: Sistema, home: Path = Path.home()) -> str:
    try:
        cfg = home / ".config" / "kdeglobals"
        if cfg.is_file():
            for riga in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                if riga.strip().startswith("ColorScheme="):
                    val = riga.split("=", 1)[1].strip()
                    return "attivo" if ("Dark" in val or val == "BreezeDark") else "inattivo"
    except OSError:
        pass
    if s.strumenti.get("kreadconfig6"):
        out = esegui_semplice(["kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme"])
        if out is not None:
            return "attivo" if ("Dark" in out or out.strip() == "BreezeDark") else "inattivo"
    if not s.strumenti.get("plasma-apply-colorscheme") and not s.strumenti.get("kreadconfig6"):
        return "non_supportato"
    return "inattivo"


def _scala_display(scala_attesa: float, home: Path = Path.home()) -> Callable[[Sistema], str]:
    def f(s: Sistema) -> str:
        if s.strumenti.get("kscreen-doctor"):
            out = esegui_semplice(["kscreen-doctor", "-j"])
            if out:
                try:
                    import json
                    dati = json.loads(out)
                    outputs = dati.get("outputs", [])
                    if outputs:
                        scale = float(outputs[0].get("scale", 1.0))
                        return "attivo" if abs(scale - scala_attesa) < 0.05 else "inattivo"
                except Exception:
                    pass
        try:
            cfg = home / ".config" / "kdeglobals"
            if cfg.is_file():
                for riga in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                    if riga.strip().startswith("ScaleFactor="):
                        val = float(riga.split("=", 1)[1].strip())
                        return "attivo" if abs(val - scala_attesa) < 0.05 else "inattivo"
        except (OSError, ValueError):
            pass
        if not s.strumenti.get("kscreen-doctor"):
            return "non_supportato"
        return "inattivo"
    return f


SCRIPT_TASTIERA_KDE = (
    "set -e\n"
    'for f in /usr/share/applications/*maliit*.desktop /usr/share/applications/org.kde.plasma.keyboard.desktop; do\n'
    '  if [ -f "$f" ]; then\n'
    '    kwriteconfig6 --notify --file kwinrc --group Wayland --key InputMethod "$f"\n'
    '    exit 0\n'
    '  fi\n'
    'done\n'
    'kwriteconfig6 --notify --file kwinrc --group Wayland --key InputMethod "/usr/share/applications/com.github.maliit.keyboard.desktop"\n'
)


def _tastiera_kde(s: Sistema, home: Path = Path.home()) -> str:
    try:
        cfg = home / ".config" / "kwinrc"
        if cfg.is_file():
            in_wayland = False
            for riga in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                r = riga.strip()
                if r.startswith("[") and r.endswith("]"):
                    in_wayland = (r.lower() == "[wayland]")
                elif in_wayland and r.startswith("InputMethod="):
                    val = r.split("=", 1)[1].strip()
                    return "attivo" if val else "inattivo"
    except OSError:
        pass
    if s.strumenti.get("kreadconfig6"):
        out = esegui_semplice(["kreadconfig6", "--file", "kwinrc", "--group", "Wayland", "--key", "InputMethod"])
        if out is not None:
            return "attivo" if out.strip() else "inattivo"
    if not s.strumenti.get("kwriteconfig6") and not s.strumenti.get("kreadconfig6"):
        return "non_supportato"
    return "inattivo"


LIMITE_CARICA = 80
SERVIZIO_CARICA = "bhs-limite-carica.service"
_PERCORSO_SOGLIA = re.compile(r"^/sys/class/power_supply/[A-Za-z0-9_.-]+/charge_control_end_threshold$")


def _soglie_valide(s: Sistema) -> list[str]:
    # I percorsi finiscono in uno script eseguito come root: si accetta solo la forma attesa.
    return [p for p in s.soglie_carica if _PERCORSO_SOGLIA.match(p)]


def _soglia_carica(s: Sistema) -> str:
    validi = _soglie_valide(s)
    if not validi:
        return "non_supportato"
    valori = [leggi_soglia(p) for p in validi]
    return "attivo" if all(v == str(LIMITE_CARICA) for v in valori) else "inattivo"


def script_limite_carica(percorsi: list[str], limite: int = LIMITE_CARICA) -> str:
    """Script (per `pkexec sh -c`) che imposta il limite subito e crea un servizio che lo riapplica a ogni avvio.

    /etc è scrivibile anche su Bazzite (immutabile). Il trattino davanti a ExecStart ignora gli errori,
    per non bloccare l'avvio se la batteria non è ancora pronta.
    """
    exec_riga = "\n".join(f"ExecStart=-/bin/sh -c 'echo {limite} > {p}'" for p in percorsi)
    unita = (
        "[Unit]\n"
        "Description=Limite di carica della batteria (Bazzite Handheld Setup)\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"{exec_riga}\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )
    return (
        "set -e\n"
        f"cat > /etc/systemd/system/{SERVIZIO_CARICA} <<'BHS_EOF'\n{unita}BHS_EOF\n"
        "systemctl daemon-reload\n"
        f"systemctl enable --now {SERVIZIO_CARICA}\n"
    )


def _comandi_carica(s: Sistema) -> list[list[str]]:
    validi = _soglie_valide(s)
    return [["pkexec", "sh", "-c", script_limite_carica(validi)]] if validi else []


RIGA_NORBC = "INTEL_DEBUG=norbc"
FILE_NORBC = Path(".config") / "environment.d" / "10-gamescope-session.conf"

# Aggiunge la riga una sola volta (idempotente) e la mostra. Nessun root: è un file dell'utente.
SCRIPT_NORBC = (
    "set -e\n"
    'f="$HOME/.config/environment.d/10-gamescope-session.conf"\n'
    'mkdir -p "$(dirname "$f")"\n'
    f"grep -qx '{RIGA_NORBC}' \"$f\" 2>/dev/null || echo '{RIGA_NORBC}' >> \"$f\"\n"
    'cat "$f"\n'
)


def _norbc(s: Sistema, home: Path = Path.home()) -> str:
    try:
        righe = (home / FILE_NORBC).read_text(encoding="utf-8").splitlines()
    except OSError:
        return "inattivo"
    return "attivo" if RIGA_NORBC in (r.strip() for r in righe) else "inattivo"


# ── Luminosità in Game Mode ──────────────────────────────────────────────────────────────────
# /usr/share/gamescope-session-plus/device-quirks mette il «ONE XPLAYER» tra i dispositivi con
# PANEL_TYPE=external: gamescope parte con --force-panel-type external e Steam, su uno schermo che crede
# esterno, non mostra il cursore della luminosità. La sessione legge ~/.config/environment.d/*.conf dopo
# i quirk, quindi basta ridefinire lì la variabile (stesso file di INTEL_DEBUG=norbc, niente root).
RIGA_PANNELLO = "PANEL_TYPE=internal"

# Toglie ogni PANEL_TYPE precedente e mette il nostro in fondo: rilanciarlo non duplica la riga.
SCRIPT_PANNELLO = (
    "set -e\n"
    'f="$HOME/.config/environment.d/10-gamescope-session.conf"\n'
    'mkdir -p "$(dirname "$f")"\n'
    'touch "$f"\n'
    "grep -v '^PANEL_TYPE=' \"$f\" > \"$f.tmp\" || true\n"
    f"echo '{RIGA_PANNELLO}' >> \"$f.tmp\"\n"
    'mv "$f.tmp" "$f"\n'
    'cat "$f"\n'
)


def _pannello(s: Sistema, home: Path = Path.home()) -> str:
    return "attivo" if pannello_utente(home) == "internal" else "inattivo"


def _nota_pannello(s: Sistema) -> str:
    if s.quirk_pannello == "external":
        return "causa confermata: la sessione dichiara lo schermo «esterno»"
    if s.quirk_pannello:
        return f"la sessione dichiara già lo schermo «{s.quirk_pannello}»: la causa è un'altra, manda la diagnosi"
    return "causa non confermata su questo sistema (nessun quirk trovato)"



# ── aria2: aria2.conf (guida Retro Think «aria2c», sezione 5) ────────────────────────────────
# Valori della tabella della sezione 4 della guida. La fascia FTTC/VDSL è quella dell'esempio completo.
FASCE_ARIA2 = {
    "adsl": ("ADSL (sotto 30 Mbit)", dict(x=4, s=4, k="10M", j=2, cache="16M", tries=10, wait=10)),
    "fttc": ("FTTC/VDSL (30-200 Mbit)", dict(x=8, s=8, k="5M", j=3, cache="32M", tries=10, wait=5)),
    "ftth": ("FTTH (100-1000 Mbit)", dict(x=16, s=16, k="1M", j=5, cache="64M", tries=5, wait=3)),
}
FILE_ARIA2 = Path(".config") / "aria2" / "aria2.conf"


def intestazione_aria2(fascia: str) -> str:
    return f"# aria2.conf - {FASCE_ARIA2[fascia][0]}"


def testo_aria2(fascia: str) -> str:
    """Contenuto di aria2.conf; `$DL` e `$ALLOC` li espande la shell (cartella dei download e allocazione).

    I commenti stanno su righe a parte: in aria2 un `#` a fine riga fa parte del valore e rompe l'opzione.
    """
    v = FASCE_ARIA2[fascia][1]
    return (
        f"{intestazione_aria2(fascia)}\n\n"
        "# Cartella di destinazione\n"
        "dir=$DL\n\n"
        "# Connessioni\n"
        f"max-connection-per-server={v['x']}\n"
        f"split={v['s']}\n"
        f"min-split-size={v['k']}\n"
        f"max-concurrent-downloads={v['j']}\n\n"
        "# Ripresa e tentativi\n"
        "continue=true\n"
        f"max-tries={v['tries']}\n"
        f"retry-wait={v['wait']}\n"
        "connect-timeout=10\n"
        "timeout=30\n\n"
        "# Disco: falloc riserva lo spazio subito (ext4, btrfs, xfs, f2fs). Su FAT32 o exFAT usa none\n"
        "file-allocation=$ALLOC\n"
        f"disk-cache={v['cache']}\n\n"
        "# Banda: 0 = nessun limite. Linea in Mbit diviso 8 = MB/s: per lasciare banda libera usa circa l'80%\n"
        "max-overall-download-limit=0\n\n"
        "# Varie\n"
        "remote-time=true\n"
        "console-log-level=warn\n"
    )


def script_aria2(fascia: str) -> str:
    """Script (utente, niente root) che scrive aria2.conf, con copia di sicurezza di quello esistente."""
    return (
        "set -e\n"
        'd="$HOME/.config/aria2"\n'
        'f="$d/aria2.conf"\n'
        'mkdir -p "$d"\n'
        'DL="$(xdg-user-dir DOWNLOAD 2>/dev/null || true)"\n'
        '[ -n "$DL" ] && [ "$DL" != "$HOME" ] || DL="$HOME/Downloads"\n'
        'mkdir -p "$DL"\n'
        'fs="$(stat -f -c %T "$DL" 2>/dev/null || echo ?)"\n'
        'case "$fs" in\n'
        "  ext2/ext3|ext4|btrfs|xfs|f2fs) ALLOC=falloc ;;\n"
        "  *) ALLOC=none ;;\n"
        "esac\n"
        '[ ! -f "$f" ] || cp "$f" "$f.bak-$(date +%Y%m%d-%H%M%S)"\n'
        "cat > \"$f\" <<BHS_ARIA2\n"
        f"{testo_aria2(fascia)}"
        "BHS_ARIA2\n"
        'echo "Scritto $f (cartella: $DL, allocazione: $ALLOC)"\n'
    )


def _stato_aria2(fascia: str) -> Callable[[Sistema], str]:
    def f(s: Sistema, home: Path = Path.home()) -> str:
        try:
            prima = (home / FILE_ARIA2).read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            return "inattivo"
        return "attivo" if prima.strip() == intestazione_aria2(fascia) else "inattivo"
    return f


# ── Mullvad VPN (guida Retro Think sul OneXPlayer 1S, sezione 7.6) ───────────────────────────
# Non ha un Flatpak ufficiale: va aggiunto al sistema con rpm-ostree, che la documentazione di Bazzite
# sconsiglia (può bloccare gli aggiornamenti). Per questo il primo passo è bloccare la versione attuale.
URL_REPO_MULLVAD = "https://repository.mullvad.net/rpm/stable/mullvad.repo"
CACHE_REPO_MULLVAD = Path(".cache") / "bazzite-handheld-setup" / "mullvad.repo"
SERVIZIO_MULLVAD = "mullvad-daemon.service"

# Il file .repo ufficiale è di 7 righe. Prima di darlo a root si controlla riga per riga: qualsiasi riga
# diversa (un altro baseurl, un comando, gpgcheck=0...) blocca tutto. La variabile $t è la copia di root.
VALIDA_REPO_MULLVAD = (
    '[ -s "$t" ] || { echo "File .repo vuoto: mi fermo."; exit 1; }\n'
    "grep -vE '^(\\[mullvad-stable\\]|name=Mullvad VPN"
    "|baseurl=https://repository\\.mullvad\\.net/[A-Za-z0-9/_$.-]+"
    "|type=rpm|enabled=1|gpgcheck=1"
    "|gpgkey=https://repository\\.mullvad\\.net/[A-Za-z0-9/_.-]+)?$' \"$t\" "
    "&& { echo \"File .repo inatteso (righe sopra): mi fermo.\"; exit 1; }\n"
    "grep -qx 'gpgcheck=1' \"$t\" && grep -qx '\\[mullvad-stable\\]' \"$t\" "
    "|| { echo \"File .repo incompleto: mi fermo.\"; exit 1; }\n"
)

SCRIPT_SCARICA_REPO_MULLVAD = (
    "set -e\n"
    'd="$HOME/.cache/bazzite-handheld-setup"\n'
    'mkdir -p "$d"\n'
    f'curl -fsSL --retry 3 --connect-timeout 15 --max-time 60 {URL_REPO_MULLVAD} -o "$d/mullvad.repo"\n'
    'echo "Scaricato $d/mullvad.repo"\n'
)

# Come root, con $1 = file scaricato: copia, controlla, blocca la versione, aggiunge il repository, installa.
SCRIPT_INSTALLA_MULLVAD = (
    "set -e\n"
    't="$(mktemp)"\n'
    "trap 'rm -f \"$t\"' EXIT\n"
    'cat "$1" > "$t"\n'
    + VALIDA_REPO_MULLVAD +
    'ostree admin pin 0 || echo "Avviso: blocco della versione non riuscito (forse è già bloccata)."\n'
    'install -m 644 "$t" /etc/yum.repos.d/mullvad.repo\n'
    "rpm-ostree install mullvad-vpn\n"
)


def _fase_mullvad(s: Sistema) -> str:
    """'attivo' | 'da_attivare' | 'in_attesa' (installato, serve il riavvio) | 'da_installare' | 'non_supportato'."""
    if s.strumenti.get("mullvad"):
        return "attivo" if s.mullvad_servizio else "da_attivare"
    if "mullvad-vpn" in s.layer:
        return "in_attesa"
    if all(s.strumenti.get(x) for x in ("rpm-ostree", "pkexec", "curl")):
        return "da_installare"
    return "non_supportato"


def _stato_mullvad(s: Sistema) -> str:
    return {"attivo": "attivo", "da_attivare": "inattivo", "in_attesa": "in_attesa",
            "da_installare": "inattivo"}.get(_fase_mullvad(s), "non_supportato")


def _nota_mullvad(s: Sistema) -> str:
    return {"da_attivare": "installato: manca da attivare il servizio",
            "in_attesa": "installato: riavvia, poi rilancia per attivare il servizio",
            "da_installare": "prima fase: installazione (poi riavvio)"}.get(_fase_mullvad(s), "")


def _comandi_mullvad(s: Sistema, home: Path = Path.home()) -> list[list[str]]:
    fase = _fase_mullvad(s)
    if fase == "da_installare":
        return [["sh", "-c", SCRIPT_SCARICA_REPO_MULLVAD],
                ["pkexec", "sh", "-c", SCRIPT_INSTALLA_MULLVAD, "sh", str(home / CACHE_REPO_MULLVAD)]]
    if fase == "da_attivare" and s.strumenti.get("pkexec"):
        return [["pkexec", "systemctl", "enable", "--now", SERVIZIO_MULLVAD]]
    return []


def tutti_i_tweak() -> dict[str, Tweak]:
    elenco = [
        Tweak(
            "tema_scuro", "Tema scuro (Breeze Dark)",
            "Imposta lo schema colori scuro Breeze Dark per KDE Plasma e le applicazioni.",
            comandi=[["plasma-apply-colorscheme", "BreezeDark"]],
            stato=_schema_colori_kde,
        ),
        Tweak(
            "scala_display_125", "Scala display 125% (Wayland)",
            "Imposta la scala del display al 125% via kscreen-doctor (consigliata per schermi 1080p come ROG Ally).",
            comandi=[["kscreen-doctor", "output.1.scale.1.25"]],
            stato=_scala_display(1.25),
        ),
        Tweak(
            "scala_display_150", "Scala display 150% (Wayland)",
            "Imposta la scala del display al 150% via kscreen-doctor (consigliata per schermi 1600p come OneXPlayer 1S).",
            comandi=[["kscreen-doctor", "output.1.scale.1.5"]],
            stato=_scala_display(1.5),
        ),
        Tweak(
            "tastiera_schermo", "Tastiera su schermo (Wayland)",
            "Abilita la tastiera virtuale di KDE Plasma 6 (Maliit) al tocco dello schermo.",
            comandi=[["sh", "-c", SCRIPT_TASTIERA_KDE]],
            stato=_tastiera_kde,
        ),
        Tweak(
            "limite_carica_80", "Limite di carica all'80%",
            "Allunga la vita della batteria. Il kernel deve esporre il controllo di carica.",
            genera=_comandi_carica,
            stato=_soglia_carica,
            avviso="Chiede la password di amministratore e crea un servizio di sistema. "
                   "Da provare sul dispositivo: su alcune immagini di Bazzite il valore tornava a 100 al riavvio.",
        ),
        Tweak(
            "intel_norbc", "Correzione schermo nero in Game Mode (Intel)",
            "Imposta INTEL_DEBUG=norbc per la sessione di gioco: serve al pannello verticale del OneXPlayer con Intel Tiger Lake.",
            comandi=[["sh", "-c", SCRIPT_NORBC]],
            stato=_norbc, richiede_riavvio=True,
            avviso="Verificata sul OneXPlayer 1S (Bazzite #6240). Se lo schermo è già nero, applicala da console: "
                   "Ctrl+Alt+F3 e poi `python3 -m bhs --applica intel_norbc`.",
        ),
        Tweak(
            "luminosita_game_mode", "Correzione della luminosità in Game Mode",
            "Imposta PANEL_TYPE=internal per la sessione di gioco: Steam torna a mostrare il cursore della luminosità "
            "che sul OneXPlayer manca perché lo schermo viene dichiarato esterno.",
            comandi=[["sh", "-c", SCRIPT_PANNELLO]],
            stato=_pannello, nota_stato=_nota_pannello, richiede_riavvio=True,
            avviso="Mai provata su un dispositivo. Se dopo il riavvio la Game Mode è ruotata male o nera, annulla da "
                   "console (Ctrl+Alt+F3): `sed -i '/^PANEL_TYPE=/d' ~/.config/environment.d/10-gamescope-session.conf` "
                   "e riavvia.",
        ),
        Tweak(
            "blocca_versione", "Blocca la versione di sistema attuale",
            "Esegue `ostree admin pin 0`: Bazzite non cancellerà più questa versione e potrai tornarci con un rollback.",
            comandi=[["pkexec", "ostree", "admin", "pin", "0"]],
            stato=lambda s: "inattivo" if s.strumenti.get("pkexec") else "non_supportato",
            avanzato=True,
            avviso="Fallo dopo aver visto che Gaming Mode, controlli e giochi funzionano.",
        ),
        Tweak(
            "aria2_conf", "Configura aria2 (linea FTTC/VDSL)",
            "Scrive ~/.config/aria2/aria2.conf con 8 connessioni, ripresa dei download e tentativi (guida Retro Think). "
            "Per misurare la tua linea: aria2-ottimizza.sh.",
            genera=lambda s: [["sh", "-c", script_aria2("fttc")]],
            stato=_stato_aria2("fttc"), avanzato=True,
            avviso="Se esiste già un aria2.conf ne salva una copia (aria2.conf.bak-DATA). Serve aria2 (voce nelle app).",
        ),
        Tweak(
            "aria2_conf_adsl", "Configura aria2 (linea ADSL)",
            "Come sopra, con i valori per una linea sotto i 30 Mbit (4 connessioni).",
            genera=lambda s: [["sh", "-c", script_aria2("adsl")]],
            stato=_stato_aria2("adsl"), avanzato=True,
        ),
        Tweak(
            "aria2_conf_ftth", "Configura aria2 (linea FTTH)",
            "Come sopra, con i valori per una fibra da 100-1000 Mbit (16 connessioni).",
            genera=lambda s: [["sh", "-c", script_aria2("ftth")]],
            stato=_stato_aria2("ftth"), avanzato=True,
        ),
        Tweak(
            "mullvad_vpn", "Mullvad VPN",
            "Aggiunge il repository ufficiale e installa Mullvad con rpm-ostree; dopo il riavvio attiva il servizio. "
            "Si fa in due tempi: rilancia lo script dopo il riavvio.",
            genera=_comandi_mullvad, stato=_stato_mullvad, nota_stato=_nota_mullvad,
            avanzato=True, richiede_riavvio=True,
            avviso="Usa rpm-ostree, che la documentazione di Bazzite sconsiglia perché può bloccare gli aggiornamenti: "
                   "blocca da sé la versione attuale e controlla il file del repository prima di darlo a root. "
                   "Poi apri l'app Mullvad VPN e inserisci il tuo numero di account. "
                   "Se un aggiornamento fallisce: rpm-ostree uninstall mullvad-vpn.",
        ),
        Tweak(
            "aggiorna_sistema", "Aggiorna sistema, app e container",
            "Esegue `ujust update`. Sulle immagini per handheld gli aggiornamenti automatici sono spenti.",
            comandi=[["ujust", "update"]],
            stato=lambda s: "inattivo" if s.strumenti.get("ujust") else "non_supportato",
            avanzato=True, richiede_riavvio=True,
            avviso="Può richiedere molto tempo e scaricare parecchi GB. Serve almeno il 3% di spazio libero. Da provare dall'interfaccia.",
        ),
    ]
    return {t.id: t for t in elenco}
