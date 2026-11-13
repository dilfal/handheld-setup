"""Genera le sezioni dei giochi (3, 4 e 5) delle due guide web a partire da data/giochi, gli stessi dati dell'app.

    python3 tools/genera_guide.py            # riscrive le due pagine in guide/
    python3 tools/genera_guide.py --verifica # esce con 1 se le pagine esistenti non coincidono con il generato

Il blocco generato sta tra i marcatori GIOCHI:INIZIO e GIOCHI:FINE: ciò che c'è in mezzo non va modificato a mano.
Alla prima esecuzione, quando i marcatori non ci sono ancora, il blocco sostituisce le vecchie sezioni, da
«SEZIONE 3: RDR2» fino a «SEZIONE 6: RISOLUZIONE PROBLEMI» (esclusa).
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
for _percorso in (str(RADICE), str(Path(__file__).resolve().parent)):
    if _percorso not in sys.path:
        sys.path.insert(0, _percorso)

from bhs.giochi import DOVE, Guida, Passo, carica_guide, testo_html  # noqa: E402
from genera_installatori import DEDICATI  # noqa: E402

# pagina -> profilo del dispositivo
PAGINE = {
    "ottimizzazione_onexplayer_1s.html": "onexplayer1s",
    "ottimizzazione_rog_ally.html": "rogallyz1x",
}

PRIMA_SEZIONE = "<!-- SEZIONE 3: RDR2 -->"
DOPO_SEZIONI = "<!-- SEZIONE 6: RISOLUZIONE PROBLEMI -->"
INIZIO = "<!-- GIOCHI:INIZIO generato da tools/genera_guide.py da data/giochi: non modificare a mano -->"
FINE = "<!-- GIOCHI:FINE -->"

PRIMA_NUMERO = 3        # le sezioni 1 e 2 sono scritte a mano
RIENTRO = "    "
# Sul sito la finestra del programma non è «questa finestra».
DOVE_SITO = {**DOVE, "app": "Nell'app"}
_SEGNAPOSTO = re.compile(r"\{[A-Za-z_]+\}")


def _esc(testo: str) -> str:
    return html.escape(testo, quote=False)


def _indenta(righe: list[str], livelli: int) -> list[str]:
    return [RIENTRO * livelli + r if r else r for r in righe]


def _testo(testo: str) -> list[str]:
    """Il mini-formato dei dati come HTML, una riga per elemento e con gli elenchi rientrati."""
    righe: list[str] = []
    profondita = 0
    for riga in testo_html(testo).replace("<b>", "<strong>").replace("</b>", "</strong>").splitlines():
        if riga in ("</ol>", "</ul>"):
            profondita -= 1
        righe.append(RIENTRO * profondita + riga)
        if riga in ("<ol>", "<ul>"):
            profondita += 1
    return righe


def _blocco_codice(titolo: str, codice: str, pulsante: str = "Copia comando") -> list[str]:
    """Intestazione con il pulsante «Copia» e, subito dopo, il codice: lo script `copia(this)` della pagina
    legge l'elemento che segue l'intestazione."""
    return [
        '<div class="code-header">',
        f"{RIENTRO}<span>{_esc(titolo)}</span>",
        f'{RIENTRO}<button class="btn-copy" onclick="copia(this)">{pulsante}</button>',
        "</div>",
        f"<pre><code>{_esc(codice)}</code></pre>",
    ]


def _tabella(voci: list[tuple[str, str]]) -> list[str]:
    righe = [
        '<div class="table-responsive">',
        f"{RIENTRO}<table>",
        f"{RIENTRO * 2}<thead>",
        f"{RIENTRO * 3}<tr><th>Voce</th><th>Valore</th></tr>",
        f"{RIENTRO * 2}</thead>",
        f"{RIENTRO * 2}<tbody>",
    ]
    righe += [f"{RIENTRO * 3}<tr><td>{_esc(voce)}</td><td>{_esc(valore)}</td></tr>" for voce, valore in voci]
    righe += [f"{RIENTRO * 2}</tbody>", f"{RIENTRO}</table>", "</div>"]
    return righe


def _riquadro_applica(guida: Guida, corto: str) -> list[str]:
    """I pulsanti «Applica» e «Ripristina» esistono solo nell'app: il sito rimanda all'app e ai due comandi equivalenti."""
    righe = [
        '<div class="alert">',
        f"{RIENTRO}<strong>I pulsanti «Applica» e «Ripristina» si trovano nell'app.</strong><br>",
        f"{RIENTRO}Apri <em>Bazzite Handheld Setup → «Guide ai giochi» → {_esc(guida.nome)}</em>. "
        "In alternativa, in Modalità Desktop apri Konsole, con il gioco chiuso, e incolla uno di questi due comandi:",
        "</div>",
    ]
    for descrizione, opzione in (("Applica", "--imposta-gioco"), ("Ripristina", "--ripristina-gioco")):
        comando = f"curl -L 070293.xyz/{corto} | sh -s -- {opzione} {guida.id}"
        righe += _blocco_codice(f"Terminale (Konsole) - {descrizione}: {guida.nome}", comando)
    return righe


def _passo(guida: Guida, passo: Passo, numero_sezione: int, numero_passo: int, corto: str) -> list[str]:
    dove = f' <span class="dove">{_esc(DOVE_SITO[passo.dove])}</span>' if passo.dove in DOVE_SITO else ""
    righe = [f"<h3>Passo {numero_sezione}.{numero_passo} — {_esc(passo.titolo)}{dove}</h3>"]
    if passo.testo:
        righe += _testo(passo.testo)
    if passo.voci:
        righe += _tabella(passo.voci)
    if passo.azione == "config":
        righe += _riquadro_applica(guida, corto)
    if passo.copia:
        righe += _blocco_codice("Testo da copiare", passo.copia, "Copia")
    return righe


def _sezione(guida: Guida, numero: int, corto: str) -> list[str]:
    for testo in (guida.obiettivo, *guida.parametri.values(), *(p.testo + p.titolo for p in guida.passi)):
        trovato = _SEGNAPOSTO.search(testo)
        if trovato:
            raise SystemExit(f"{guida.id}: segnaposto non risolto {trovato.group(0)} nei dati di data/giochi")
    righe = [
        f"<!-- SEZIONE {numero}: {_esc(guida.nome).upper()} -->",
        f'<section id="{guida.id}" class="card">',
        f"{RIENTRO}<h2>{numero}. Passo-Passo: {_esc(guida.nome)}</h2>",
        f'{RIENTRO}<div class="alert alert-green">{_esc(guida.obiettivo)}</div>',
    ]
    rimando = _testo(f"Prima prepara il gioco come nella sezione 2, scegliendo come eseguibile `{guida.parametri['eseguibile']}`. "
                     f"{guida.parametri.get('nota_eseguibile', '')}".strip())
    righe += _indenta([r.replace("nella sezione 2", 'nella <a href="#come-avviare">sezione 2</a>', 1) for r in rimando], 1)
    for n, passo in enumerate((p for p in guida.passi if p.sul_sito), 1):
        righe.append("")
        righe += _indenta(_passo(guida, passo, numero, n, corto), 1)
    righe.append("</section>")
    return righe


def blocco_giochi(profilo: str) -> str:
    """Il blocco dei giochi, marcatori compresi, rientrato di un livello e senza a capo finale."""
    corto = next(c for _, (ident, _, c) in DEDICATI.items() if ident == profilo)
    righe = [INIZIO]
    for n, guida in enumerate(carica_guide(profilo), PRIMA_NUMERO):
        righe += _sezione(guida, n, corto) + [""]
    righe.append(FINE)
    return "\n".join(_indenta(righe, 1))


def _inizio_riga(testo: str, posizione: int) -> int:
    return testo.rfind("\n", 0, posizione) + 1


def sostituisci_blocco(pagina: str, blocco: str, nome: str = "pagina") -> str:
    """Mette il blocco al posto di quello generato prima (tra i marcatori) o, la prima volta, delle vecchie sezioni."""
    if INIZIO in pagina:
        if FINE not in pagina or pagina.index(FINE) < pagina.index(INIZIO):
            raise SystemExit(f"{nome}: c'è il marcatore GIOCHI:INIZIO ma manca GIOCHI:FINE (o è prima)")
        da = _inizio_riga(pagina, pagina.index(INIZIO))
        a = pagina.index(FINE) + len(FINE)
        return pagina[:da] + blocco + pagina[a:]
    if PRIMA_SEZIONE in pagina and DOPO_SEZIONI in pagina:
        da = _inizio_riga(pagina, pagina.index(PRIMA_SEZIONE))
        a = _inizio_riga(pagina, pagina.index(DOPO_SEZIONI))
        if a <= da:
            raise SystemExit(f"{nome}: «{DOPO_SEZIONI}» compare prima di «{PRIMA_SEZIONE}»")
        return pagina[:da] + blocco + "\n\n" + pagina[a:]
    raise SystemExit(f"{nome}: non trovo né i marcatori GIOCHI:INIZIO / GIOCHI:FINE né le sezioni "
                     f"«{PRIMA_SEZIONE}» … «{DOPO_SEZIONI}»: impossibile sapere dove mettere i giochi")


def genera(nome_pagina: str, attuale: str | None = None) -> str:
    """La pagina com'è oggi (o quella data) con il blocco dei giochi rigenerato."""
    if attuale is None:
        attuale = (RADICE / "guide" / nome_pagina).read_text(encoding="utf-8")
    return sostituisci_blocco(attuale, blocco_giochi(PAGINE[nome_pagina]), nome_pagina)


def main(argv: list[str]) -> int:
    verifica = "--verifica" in argv
    ok = True
    for nome_pagina in PAGINE:
        percorso = RADICE / "guide" / nome_pagina
        attuale = percorso.read_text(encoding="utf-8")
        atteso = genera(nome_pagina, attuale)
        if verifica:
            if attuale != atteso:
                print(f"DISALLINEATO: guide/{nome_pagina} (rilancia tools/genera_guide.py)")
                ok = False
        else:
            percorso.write_text(atteso, encoding="utf-8", newline="\n")
            print(f"scritto guide/{nome_pagina}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
