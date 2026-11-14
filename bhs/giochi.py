"""Guide passo passo ai giochi, lette da data/giochi/*.toml, e modifica dei loro file di impostazioni.

Ogni guida è un elenco di passi già adattato al dispositivo (profilo). Il passo «config» può scrivere da sé
le impostazioni grafiche nel file del gioco, con tre regole:

* si cambiano solo le chiavi elencate nella guida, il resto del file resta com'è (niente file riscritti da zero:
  i giochi scartano i file che non hanno la loro struttura);
* prima della prima modifica si salva una copia accanto al file (`<nome>.bhs-originale`), che «Ripristina» rimette;
* nei file XML non si aggiunge mai una chiave che il gioco non ha scritto;
* ogni scrittura passa da un file temporaneo rinominato alla fine: il file del gioco e la sua copia sono sempre interi.
"""

from __future__ import annotations

import codecs
import html
import json
import os
import re
import shutil
import stat
import tempfile
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .profiles import DATI, carica_profili, profilo_per_id

CARTELLA_GUIDE = DATI / "giochi"
SUFFISSO_COPIA = ".bhs-originale"
DOVE = {"desktop": "Modalità Desktop", "gaming": "Gaming Mode", "gioco": "Dentro il gioco", "app": "In questa finestra",
        "winhanced": "In Winhanced", "windows": "Su Windows"}
SISTEMI = ("bazzite", "windows")      # il sistema del dispositivo: la guida di Windows usa i valori `*_windows` dei dati


# ── Dati ──────────────────────────────────────────────────────────────
@dataclass
class ConfigGioco:
    tipo: str                    # "ini" | "xml"
    cartelle: list[str]          # sotto drive_c/users/steamuser del prefisso Proton
    file: list[str]
    valori: dict[str, str]       # "Sezione/chiave" -> valore, già scelti per il profilo
    aggiungi: bool = True        # solo "ini": aggiunge le chiavi che mancano


@dataclass
class Passo:
    titolo: str
    testo: str = ""
    dove: str = ""               # chiave di DOVE, oppure vuoto
    voci: list[tuple[str, str]] = field(default_factory=list)   # (voce del menu, valore da scegliere)
    copia: str = ""              # testo da copiare (es. opzioni di avvio)
    azione: str = ""             # "config": mostra «Applica» e «Ripristina»
    nota_app: str = ""           # riga in più solo per finestra e console (il sito non la mostra)
    sul_sito: bool = True        # False: il sito spiega già il passo per esteso nella sezione 2 della pagina


@dataclass
class Guida:
    id: str
    nome: str
    obiettivo: str
    passi: list[Passo]
    config: Optional[ConfigGioco] = None
    parametri: dict[str, str] = field(default_factory=dict)   # valori già scelti per il profilo (eseguibile, fps, tdp…)


def _per_profilo(valore, profilo: str, _visti: frozenset = frozenset()):
    """Sceglie il valore del profilo; un valore stringa dentro una tabella rimanda a un altro profilo."""
    if not isinstance(valore, dict):
        return valore
    scelto = valore.get(profilo, valore.get("generico", valore.get("tutti")))
    if isinstance(scelto, str) and scelto in valore and scelto not in _visti:
        return _per_profilo(valore, scelto, _visti | {profilo})
    return scelto


class _Segnaposto(dict):
    def __missing__(self, chiave):          # un segnaposto sconosciuto resta visibile, non fa cadere la guida
        return "{" + chiave + "}"


def _riempi(testo: str, parametri: dict[str, str]) -> str:
    return testo.format_map(_Segnaposto(parametri)) if testo else ""


def _parametri(sorgente: dict, profilo: str) -> dict[str, str]:
    """Valori semplici (uguali per tutti) più quelli della tabella del profilo."""
    comuni = {k: str(v) for k, v in sorgente.items() if not isinstance(v, dict)}
    tabelle = {k: v for k, v in sorgente.items() if isinstance(v, dict)}
    return {**comuni, **{k: str(v) for k, v in (_per_profilo(tabelle, profilo) or {}).items()}}


def _passo(d: dict, profilo: str, parametri: dict[str, str], sistema: str = "bazzite") -> Optional[Passo]:
    solo = d.get("solo")
    if solo and profilo not in solo:
        return None
    windows = sistema == "windows"
    if windows and d.get("windows", True) is False:
        return None
    if not windows and d.get("bazzite", True) is False:
        return None

    def scelto(chiave: str, base=None):
        """Su Windows vale `<chiave>_windows` se c'è; altrimenti il valore di base."""
        if windows and f"{chiave}_windows" in d:
            return d[f"{chiave}_windows"]
        return d.get(chiave, base)

    voci = _per_profilo(scelto("voci"), profilo) or []
    return Passo(
        titolo=_riempi(scelto("titolo"), parametri),
        testo=_riempi(_per_profilo(scelto("testo", ""), profilo) or "", parametri).strip(),
        dove=scelto("dove", ""),
        voci=[(_riempi(str(v[0]), parametri), _riempi(str(v[1]), parametri)) for v in voci],
        copia=_riempi(_per_profilo(d.get("copia", ""), profilo) or "", parametri),
        azione="" if windows else d.get("azione", ""),          # su Windows non c'è il pulsante «Applica»
        nota_app="" if windows else _riempi(_per_profilo(d.get("nota_app", ""), profilo) or "", parametri),
        sul_sito=bool(d.get("sul_sito", True)),
    )


def _config(d: Optional[dict], profilo: str) -> Optional[ConfigGioco]:
    if not d:
        return None
    valori = dict(_per_profilo(d.get("qualita", {}), profilo) or {})
    # Le chiavi dello schermo (risoluzione) valgono solo per il dispositivo per cui sono scritte: niente ripiego.
    valori.update(d.get("schermo", {}).get(profilo, {}))
    if not valori:
        return None
    file = d["file"] if isinstance(d["file"], list) else [d["file"]]
    return ConfigGioco(tipo=d["tipo"], cartelle=list(d["cartelle"]), file=file,
                       valori={k: str(v) for k, v in valori.items()}, aggiungi=d.get("aggiungi", True))


def carica_guide(profilo: str, sistema: str = "bazzite", cartella: Path = CARTELLA_GUIDE) -> list[Guida]:
    """Guide ordinate, con testi e valori già scelti per il profilo (quelli sconosciuti usano «generico»).

    `sistema="windows"` dà la variante per Winhanced: ai parametri si sovrappongono le tabelle `[parametri_windows…]`;
    ogni passo può avere `titolo_windows`, `testo_windows`, `dove_windows`, `voci_windows`, `windows = false`
    (il passo non compare) e `bazzite = false` (il passo compare solo su Windows). Con il sistema predefinito i dati sono quelli di sempre.
    """
    if sistema not in SISTEMI:
        raise ValueError(f"sistema sconosciuto: {sistema!r} (valori ammessi: {', '.join(SISTEMI)})")
    if profilo_per_id(carica_profili(), profilo) is None:       # anche per i passi con `solo = [...]`, non solo per i valori
        profilo = "generico"
    comune: dict = {}
    file_comune = cartella / "_comune.toml"
    if file_comune.is_file():
        with file_comune.open("rb") as fh:
            comune = tomllib.load(fh)
    guide: list[tuple[int, Guida]] = []
    for file in sorted(cartella.glob("*.toml")):
        if file.name.startswith("_"):
            continue
        with file.open("rb") as fh:
            d = tomllib.load(fh)
        parametri = {"nome": d["nome"], **_parametri(comune.get("parametri", {}), profilo),
                     **_parametri(d.get("parametri", {}), profilo)}
        if sistema == "windows":
            parametri.update(_parametri(comune.get("parametri_windows", {}), profilo))
            parametri.update(_parametri(d.get("parametri_windows", {}), profilo))
        for _ in range(3):         # un parametro può citarne un altro (es. «potenza» cita «tdp»)
            parametri = {k: _riempi(v, parametri) for k, v in parametri.items()}
        grezzi = comune.get("preparazione", []) + d.get("passo", []) + comune.get("chiusura", [])
        passi = [p for p in (_passo(x, profilo, parametri, sistema) for x in grezzi) if p is not None]
        guide.append((d.get("ordine", 99), Guida(
            id=d["id"], nome=d["nome"], obiettivo=_riempi(_per_profilo(d.get("obiettivo", ""), profilo) or "", parametri),
            passi=passi, config=_config(d.get("config"), profilo), parametri=parametri)))
    return [g for _, g in sorted(guide, key=lambda x: (x[0], x[1].nome))]


def guida_per_id(guide: list[Guida], ident: str) -> Optional[Guida]:
    return next((g for g in guide if g.id == ident), None)


# ── Testo: un formato minimo (grassetto, codice, elenchi) per finestra, sito e console ──
_GRASSETTO = re.compile(r"\*\*(.+?)\*\*")
_CODICE = re.compile(r"`([^`]+)`")
_NUMERATA = re.compile(r"^\d+\.\s+")


def _in_linea(riga: str) -> str:
    riga = html.escape(riga, quote=False)
    riga = _GRASSETTO.sub(r"<b>\1</b>", riga)
    return _CODICE.sub(r"<code>\1</code>", riga)


def testo_html(testo: str) -> str:
    """Paragrafi, elenchi numerati («1. ») ed elenchi puntati («- ») come HTML semplice (lo capisce anche Qt)."""
    blocchi: list[str] = []
    aperto = ""                     # "ol" | "ul" | ""

    def chiudi():
        nonlocal aperto
        if aperto:
            blocchi.append(f"</{aperto}>")
            aperto = ""

    for riga in testo.splitlines():
        riga = riga.strip()
        if not riga:
            chiudi()
            continue
        tipo = "ol" if _NUMERATA.match(riga) else ("ul" if riga.startswith("- ") else "")
        if tipo:
            if aperto != tipo:
                chiudi()
                blocchi.append(f"<{tipo}>")
                aperto = tipo
            corpo = _NUMERATA.sub("", riga) if tipo == "ol" else riga[2:]
            blocchi.append(f"<li>{_in_linea(corpo)}</li>")
        else:
            chiudi()
            blocchi.append(f"<p>{_in_linea(riga)}</p>")
    chiudi()
    return "\n".join(blocchi)


def testo_semplice(testo: str) -> str:
    return _CODICE.sub(r"\1", _GRASSETTO.sub(r"\1", testo))


def testo_guida(g: Guida) -> str:
    """La guida come testo per la console (`--guida ID`)."""
    righe = [f"== {g.nome} ==", g.obiettivo, ""]
    for n, p in enumerate(g.passi, 1):
        dove = f" [{DOVE[p.dove]}]" if p.dove in DOVE else ""
        righe.append(f"Passo {n} di {len(g.passi)}: {p.titolo}{dove}")
        righe += ["  " + r for r in testo_semplice(p.testo).splitlines()]
        if p.nota_app:
            righe.append("  " + testo_semplice(p.nota_app))
        if p.copia:
            righe.append(f"  Da copiare: {p.copia}")
        if p.voci:
            largo = max(len(v) for v, _ in p.voci)
            righe += [f"    {v:<{largo}}  {x}" for v, x in p.voci]
        if p.azione == "config":
            righe.append(f"  In automatico: python3 -m bhs --imposta-gioco {g.id}   (annulla: --ripristina-gioco {g.id})")
        righe.append("")
    return "\n".join(righe).rstrip() + "\n"


# ── Ricerca dei file del gioco nei prefissi Proton ────────────────────
_PERCORSO_VDF = re.compile(r'"path"\s+"([^"]+)"')


def radici_steam(home: Path) -> list[Path]:
    """Cartelle di Steam e delle sue librerie (anche su scheda SD), senza doppioni."""
    candidati = [home / ".local/share/Steam", home / ".steam/steam",
                 home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"]
    for base in list(candidati):
        try:
            testo = (base / "steamapps" / "libraryfolders.vdf").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        candidati += [Path(p.replace("\\\\", "/")) for p in _PERCORSO_VDF.findall(testo)]
    viste: set[Path] = set()
    radici = []
    for c in candidati:
        try:
            reale = c.resolve()
        except OSError:
            continue
        if reale not in viste and (c / "steamapps").is_dir():
            viste.add(reale)
            radici.append(c)
    return radici


def trova_file(cfg: ConfigGioco, home: Path = Path.home()) -> list[Path]:
    """File di impostazioni del gioco in tutti i prefissi Proton, dal più recente."""
    trovati: dict[Path, Path] = {}
    for radice in radici_steam(home):
        for utente in (radice / "steamapps" / "compatdata").glob("*/pfx/drive_c/users/steamuser"):
            for cartella in cfg.cartelle:
                for nome in cfg.file:
                    f = utente / cartella / nome
                    if f.is_file():
                        trovati.setdefault(f.resolve(), f)
    return sorted(trovati.values(), key=lambda f: f.stat().st_mtime, reverse=True)


def file_ammesso(cfg: ConfigGioco, percorso) -> bool:
    """Vero se il nome del file (maiuscole escluse) è uno di quelli che la guida sa modificare."""
    return Path(percorso).name.casefold() in {n.casefold() for n in cfg.file}


# ── Modifica dei file ─────────────────────────────────────────────────
@dataclass
class Esito:
    chiave: str
    stato: str                   # "cambiata" | "uguale" | "aggiunta" | "assente"
    prima: Optional[str] = None
    dopo: Optional[str] = None


def _dividi(percorso: str) -> tuple[str, str]:
    sezione, _, chiave = percorso.rpartition("/")
    return sezione, chiave


# Le righe si dividono solo su \r\n, \r e \n (non su U+0085 e simili, che in una codifica a un byte per carattere
# sono lettere del file): ogni riga porta con sé il proprio fine riga, così quelli misti restano com'erano.
_RIGA = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+")
_INTESTAZIONE = re.compile(r"\s*\[([^\]]*)\]\s*(?:[;#].*)?")      # «[Sezione]» con un commento facoltativo dopo
_COMMENTO_IN_LINEA = re.compile(r"[ \t]+;")      # in un valore, il commento comincia al primo «;» preceduto da spazio o tab


def _fine_riga(riga: str) -> str:
    return riga[len(riga.rstrip("\r\n")):]


def _termina(righe: list[str], a_capo: str) -> None:
    """Se l'ultima riga non ha il fine riga (file senza a capo finale), glielo dà: sta per seguirne un'altra."""
    if righe and not _fine_riga(righe[-1]):
        righe[-1] += a_capo


def modifica_ini(testo: str, valori: dict[str, str], aggiungi: bool = True) -> tuple[str, list[Esito]]:
    """Cambia `chiave=valore` dentro `[Sezione]`; maiuscole e spazi attorno alla chiave non contano.

    Ogni riga tiene il suo fine riga; le righe nuove usano quello più frequente nel file.
    """
    for percorso in valori:
        if not _dividi(percorso)[0].strip():
            raise ValueError(f"chiave senza sezione: {percorso}")
    righe = _RIGA.findall(testo)
    fini = Counter(f for f in map(_fine_riga, righe) if f)
    a_capo = fini.most_common(1)[0][0] if fini else "\n"
    esiti: list[Esito] = []
    for percorso, nuovo in valori.items():
        sezione, chiave = _dividi(percorso)
        inizio = fine = None
        for i, riga in enumerate(righe):
            m = _INTESTAZIONE.fullmatch(riga.rstrip("\r\n"))
            if m:
                if inizio is not None:
                    fine = i
                    break
                if m.group(1).strip().lower() == sezione.lower():
                    inizio = i
        if inizio is None:
            if not aggiungi:
                esiti.append(Esito(percorso, "assente"))
                continue
            _termina(righe, a_capo)          # niente si toglie: nemmeno le righe che sembrano vuote
            righe += [f"[{sezione}]{a_capo}", f"{chiave}={nuovo}{a_capo}"]
            esiti.append(Esito(percorso, "aggiunta", None, nuovo))
            continue
        fine = len(righe) if fine is None else fine
        for i in range(inizio + 1, fine):
            nome, uguale, vecchio = righe[i].rstrip("\r\n").partition("=")
            if uguale and not nome.lstrip().startswith((";", "#")) and nome.strip().lower() == chiave.lower():
                inline = _COMMENTO_IN_LINEA.search(vecchio)       # «y=0 ; nota»: il commento resta com'è
                commento = vecchio[inline.start():] if inline else ""
                vecchio_pulito = (vecchio[:inline.start()] if inline else vecchio).strip()
                if vecchio_pulito == nuovo:
                    esiti.append(Esito(percorso, "uguale", vecchio_pulito, nuovo))
                else:
                    spazio = " " if nome.endswith(" ") else ""
                    righe[i] = f"{nome}={spazio}{nuovo}{commento}{_fine_riga(righe[i])}"
                    esiti.append(Esito(percorso, "cambiata", vecchio_pulito, nuovo))
                break
        else:
            if not aggiungi:
                esiti.append(Esito(percorso, "assente"))
                continue
            ultimo = fine
            while ultimo > inizio + 1 and not righe[ultimo - 1].strip():
                ultimo -= 1          # in coda alla sezione, prima delle righe vuote
            if ultimo == len(righe):
                _termina(righe, a_capo)
            righe.insert(ultimo, f"{chiave}={nuovo}{a_capo}")
            esiti.append(Esito(percorso, "aggiunta", None, nuovo))
    return "".join(righe), esiti


def modifica_xml(testo: str, valori: dict[str, str]) -> tuple[str, list[Esito]]:
    """Cambia `<chiave>valore</chiave>` o `<chiave value="valore" />` dentro `<sezione>`; non aggiunge nulla."""
    esiti: list[Esito] = []
    for percorso, nuovo in valori.items():
        sezione, chiave = _dividi(percorso)
        blocco = re.search(rf"<{re.escape(sezione)}>.*?</{re.escape(sezione)}>", testo, re.DOTALL)
        if not blocco:
            esiti.append(Esito(percorso, "assente"))
            continue
        k = re.escape(chiave)
        m = re.search(rf'(<{k}>)([^<]*)(</{k}>)|(<{k}\s+value=")([^"]*)("\s*/>)', blocco.group(0))
        if not m:
            esiti.append(Esito(percorso, "assente"))
            continue
        gruppo = 2 if m.group(1) else 5
        vecchio = m.group(gruppo)
        if vecchio == nuovo:
            esiti.append(Esito(percorso, "uguale", vecchio, nuovo))
            continue
        da, a = blocco.start() + m.start(gruppo), blocco.start() + m.end(gruppo)
        testo = testo[:da] + nuovo + testo[a:]
        esiti.append(Esito(percorso, "cambiata", vecchio, nuovo))
    return testo, esiti


_ERRORE_CODIFICA = "codifica non riconosciuta: file non modificato"
_ERRORE_SOLA_LETTURA = "file di sola lettura: non modificato"
_BOM16 = {"utf-16-le": codecs.BOM_UTF16_LE, "utf-16-be": codecs.BOM_UTF16_BE}      # nome della codifica -> BOM da rimettere


def _decodifica(dati: bytes) -> tuple[str, str]:
    """Testo e codifica (i giochi Windows usano UTF-8, UTF-16 con BOM o la codifica ANSI).

    Senza BOM e non UTF-8 si ripiega su latin-1: ogni byte diventa un carattere e torna byte per byte uguale, anche
    quelli che cp1252 non ha (0x81, 0x8D…). Un file con byte nulli e senza BOM non è testo che sappiamo leggere.
    """
    for codifica, bom in _BOM16.items():
        if dati.startswith(bom):
            if dati.startswith(codecs.BOM_UTF32_LE):         # FF FE 00 00: è UTF-32, non UTF-16
                raise ValueError(_ERRORE_CODIFICA)
            return dati[len(bom):].decode(codifica), codifica
    if dati.startswith(codecs.BOM_UTF8):
        return dati.decode("utf-8-sig"), "utf-8-sig"
    if b"\x00" in dati:
        raise ValueError(_ERRORE_CODIFICA)
    try:
        return dati.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return dati.decode("latin-1"), "latin-1"


def _codifica(testo: str, codifica: str) -> bytes:
    return _BOM16.get(codifica, b"") + testo.encode(codifica)


def _leggi(file: Path) -> tuple[str, str]:
    return _decodifica(file.read_bytes())


def _scrivi_atomico(percorso: Path, dati: bytes) -> None:
    """Scrive su un temporaneo nella stessa cartella e lo rinomina: il file o c'è intero o non cambia.

    Se `percorso` è un collegamento si scrive il file a cui punta; in caso di errore il temporaneo viene tolto.
    """
    finale = percorso.resolve()
    fd, temporaneo = tempfile.mkstemp(dir=finale.parent, prefix=f".{finale.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dati)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            shutil.copymode(finale, temporaneo)          # il file del gioco mantiene i suoi permessi
        except OSError:
            pass                                         # file nuovo (la copia): restano quelli del temporaneo
        os.replace(temporaneo, finale)
    except BaseException:
        try:
            os.chmod(temporaneo, stat.S_IWRITE | stat.S_IREAD)      # su Windows un file di sola lettura non si toglie
            os.unlink(temporaneo)
        except OSError:
            pass
        raise


@dataclass
class Rapporto:
    file: Path
    esiti: list[Esito] = field(default_factory=list)
    errore: Optional[str] = None
    scritto: bool = False
    nota: Optional[str] = None           # riga informativa che non è un errore (ripristino senza copia, simulazione)
    senza_copia: bool = False            # ripristino: il file non ha mai avuto una copia, quindi non c'è nulla da fare

    def conta(self, stato: str) -> int:
        return sum(1 for e in self.esiti if e.stato == stato)


def applica_config(cfg: ConfigGioco, file: list[Path], simulazione: bool = False) -> list[Rapporto]:
    rapporti = []
    for f in file:
        r = Rapporto(f)
        rapporti.append(r)
        try:
            originale = f.read_bytes()
            testo, codifica = _decodifica(originale)
            if cfg.tipo == "xml":
                nuovo, r.esiti = modifica_xml(testo, cfg.valori)
            else:
                nuovo, r.esiti = modifica_ini(testo, cfg.valori, cfg.aggiungi)
            if nuovo == testo:
                continue
            if not os.access(f, os.W_OK):            # spesso è l'utente a bloccare il file apposta: non lo si tocca
                r.errore = _ERRORE_SOLA_LETTURA
                continue
            if simulazione:
                continue
            dati = _codifica(nuovo, codifica)           # prima di scrivere qualsiasi cosa: se non si può, il file resta com'è
            copia = f.with_name(f.name + SUFFISSO_COPIA)
            if not copia.exists():           # la copia è lo stato di partenza: non si sovrascrive mai
                _scrivi_atomico(copia, originale)
            _scrivi_atomico(f, dati)
            r.scritto = True
        except UnicodeError:
            r.errore = _ERRORE_CODIFICA
        except (OSError, ValueError) as e:
            r.errore = str(e)
    return rapporti


def ripristina_config(file: list[Path], simulazione: bool = False) -> list[Rapporto]:
    """Rimette la copia salvata prima della prima modifica (e la toglie, così una nuova modifica ne crea un'altra).

    Un file senza copia non è un errore: non è mai stato modificato da noi. In simulazione non si scrive né si toglie nulla.
    """
    rapporti = []
    for f in file:
        r = Rapporto(f)
        rapporti.append(r)
        copia = f.with_name(f.name + SUFFISSO_COPIA)
        if not copia.is_file():
            r.senza_copia = True
            r.nota = "niente da ripristinare (nessuna copia salvata)"
            continue
        if f.exists() and not os.access(f, os.W_OK):
            r.errore = _ERRORE_SOLA_LETTURA
            continue
        try:
            dati = copia.read_bytes()
            if simulazione:
                r.nota = f"simulazione: rimetterei {copia.name} al posto del file e poi la toglierei"
                continue
            _scrivi_atomico(f, dati)
            r.scritto = True
            copia.unlink()
        except OSError as e:
            r.errore = str(e)
    return rapporti


def testo_rapporti(rapporti: list[Rapporto], simulazione: bool = False) -> str:
    righe = []
    for r in rapporti:
        righe.append(str(r.file))
        if r.errore:
            righe.append(f"  ✗ {r.errore}")
            continue
        if r.nota:
            righe.append(f"  {r.nota}")
        for e in r.esiti:
            if e.stato == "cambiata":
                righe.append(f"  {e.chiave}: {e.prima} → {e.dopo}")
            elif e.stato == "aggiunta":
                righe.append(f"  {e.chiave}: aggiunta = {e.dopo}")
            elif e.stato == "assente":
                righe.append(f"  {e.chiave}: non c'è nel file, impostala dal menu del gioco")
        uguali = r.conta("uguale")
        if uguali:
            righe.append(f"  {uguali} voci erano già a posto")
        if r.esiti:
            if simulazione:
                righe.append("  (simulazione: file non modificato)")
            elif r.scritto:
                righe.append(f"  ✓ salvato; copia di prima in {r.file.name}{SUFFISSO_COPIA}")
        elif r.scritto:
            righe.append("  ✓ ripristinato")
    if rapporti and all(r.senza_copia for r in rapporti):
        righe.append("Nessuna copia salvata: non c'era niente da ripristinare")
    return "\n".join(righe)


# ── A che passo si era arrivati ───────────────────────────────────────
FILE_PROGRESSI = Path.home() / ".config" / "bazzite-handheld-setup" / "guide.json"


def leggi_progressi(file: Path = FILE_PROGRESSI) -> dict[str, int]:
    try:
        dati = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in dati.items() if isinstance(k, str) and isinstance(v, int)} if isinstance(dati, dict) else {}


def salva_progresso(ident: str, passo: int, file: Path = FILE_PROGRESSI) -> None:
    dati = leggi_progressi(file)
    dati[ident] = passo
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(dati), encoding="utf-8")
    except OSError:
        pass                       # il segnalibro è una comodità: se non si può scrivere, la guida funziona lo stesso
