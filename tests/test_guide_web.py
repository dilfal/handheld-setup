"""Test delle guide web dei giochi (tools/genera_guide.py) e delle scorciatoie per il telefono.
Eseguire dalla radice: python -I -m unittest discover -s tests -p "test_guide_web.py" """

import html
import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from bhs.giochi import carica_guide  # noqa: E402
from tools import genera_guide, pubblica_070293  # noqa: E402

ID_GIOCHI = ["rdr2", "witcher3", "skyrim"]
TAG_CONTROLLATI = {"section", "div", "table", "ol", "ul", "pre", "code", "h2", "h3"}
VECCHI_RESIDUI = ['cat > "$P/', "RADV_PERFTEST", "fMaxTime", "TextureQuality=", "INTEL_DEBUG=norbc %command%"]


class VerificaTag(HTMLParser):
    """Controlla che i tag elencati si aprano e si chiudano in ordine."""

    def __init__(self):
        super().__init__()
        self.pila: list[str] = []
        self.errori: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in TAG_CONTROLLATI:
            self.pila.append(tag)

    def handle_endtag(self, tag):
        if tag not in TAG_CONTROLLATI:
            return
        if not self.pila or self.pila[-1] != tag:
            self.errori.append(f"</{tag}> alla riga {self.getpos()[0]} ma aperto: {self.pila[-1:] or 'niente'}")
        else:
            self.pila.pop()


def pagina(nome: str) -> str:
    return (RADICE / "guide" / nome).read_text(encoding="utf-8")


class TestGeneraGuide(unittest.TestCase):
    def test_pagine_allineate(self):
        """Il comando `--verifica` esce con 0: le pagine su disco coincidono con il generato."""
        with redirect_stdout(io.StringIO()) as uscita:
            codice = genera_guide.main(["--verifica"])
        self.assertEqual(codice, 0, uscita.getvalue())
        for nome in genera_guide.PAGINE:
            self.assertEqual(pagina(nome), genera_guide.genera(nome), nome)

    def test_sezioni_voci_e_nessun_residuo(self):
        for nome, profilo in genera_guide.PAGINE.items():
            with self.subTest(pagina=nome):
                testo = pagina(nome)
                guide = carica_guide(profilo)
                self.assertEqual([g.id for g in guide], ID_GIOCHI)
                for numero, g in enumerate(guide, 3):
                    self.assertIn(f'<section id="{g.id}" class="card">', testo)
                    self.assertIn(f"<h2>{numero}. Passo-Passo: {html.escape(g.nome, quote=False)}</h2>", testo)
                    self.assertIn(f"{html.escape(g.obiettivo, quote=False)}</div>", testo)
                    for passo in (p for p in g.passi if p.sul_sito):
                        self.assertIn(html.escape(passo.titolo, quote=False), testo)
                        for voce, valore in passo.voci:
                            self.assertIn(f"<td>{html.escape(voce, quote=False)}</td><td>{html.escape(valore, quote=False)}</td>", testo)
                for residuo in VECCHI_RESIDUI:
                    self.assertNotIn(residuo, testo)

    def test_passi_solo_per_l_app_non_compaiono(self):
        for nome, profilo in genera_guide.PAGINE.items():
            with self.subTest(pagina=nome):
                titoli = [html.unescape(t) for t in re.findall(r"<h3>(.*?)</h3>", pagina(nome))]
                nascosti = [p.titolo for g in carica_guide(profilo) for p in g.passi if not p.sul_sito]
                self.assertTrue(nascosti, "nessun passo con sul_sito = false")
                for titolo in nascosti:
                    self.assertFalse([t for t in titoli if titolo in t], titolo)

    def test_i_primi_quattro_passi_comuni_non_vanno_sul_sito(self):
        """Origine del gioco, copia, aggiunta a Steam e scelta di Proton sono già spiegati nella sezione 2."""
        for g in carica_guide("rogallyz1x"):
            self.assertEqual([p.sul_sito for p in g.passi[:4]], [False] * 4)
            self.assertEqual(g.passi[0].titolo, "Da dove viene il gioco")
            self.assertTrue(all(p.sul_sito for p in g.passi[4:]))
            self.assertTrue(g.parametri.get("eseguibile"))

    def test_nota_sull_origine_solo_per_rdr2(self):
        for profilo in genera_guide.PAGINE.values():
            note = {g.id: g.passi[0].testo for g in carica_guide(profilo)}
            self.assertIn("Rockstar Games Launcher", note["rdr2"])
            for ident in ("witcher3", "skyrim"):
                self.assertNotIn("Rockstar", note[ident])
                self.assertIn("Comprato su Steam", note[ident])

    def test_indice_uguale_ai_titoli_h2(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                testo = pagina(nome)
                indice = re.findall(r'<li><a href="#[^"]+">(.*?)</a></li>', testo.split('<div class="nav-summary">')[1].split("</div>")[0])
                titoli = [html.unescape(t) for t in re.findall(r"<h2>(.*?)</h2>", testo)]
                self.assertEqual([html.unescape(i) for i in indice], titoli)

    def test_sezione_2_senza_passo_primo_avvio_e_senza_enfasi(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                testo = pagina(nome)
                prima = testo.split(genera_guide.INIZIO)[0]
                self.assertNotIn("Passo 2.4", prima)
                self.assertIn("Il primo avvio lo fai nella sezione del tuo gioco.", prima)
                self.assertNotIn("Steam Gaming Mode", testo)
                corpo = re.sub(r"<!--.*?-->", "", prima, flags=re.S).split("<body>")[1]
                self.assertNotIn("!", corpo)

    def test_html_bilanciato_e_senza_segnaposto(self):
        for profilo in genera_guide.PAGINE.values():
            with self.subTest(profilo=profilo):
                blocco = genera_guide.blocco_giochi(profilo)
                p = VerificaTag()
                p.feed(blocco)
                p.close()
                self.assertEqual(p.errori, [])
                self.assertEqual(p.pila, [])
                self.assertIsNone(re.search(r"\{[A-Za-z_]+\}", blocco))
                self.assertEqual(blocco.count("<section "), 3)

    def test_collegamenti_interni_esistono(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                testo = pagina(nome)
                for ancora in set(re.findall(r'href="#([^"]+)"', testo)):
                    self.assertIn(f'id="{ancora}"', testo, ancora)

    def test_comandi_dei_pulsanti_dell_app(self):
        """Ogni passo «config» ha i due comandi con la scorciatoia giusta del dispositivo."""
        for nome, corto in (("ottimizzazione_onexplayer_1s.html", "oxp"), ("ottimizzazione_rog_ally.html", "ally")):
            testo = pagina(nome)
            for ident in ID_GIOCHI:
                self.assertIn(f"curl -L 070293.xyz/{corto} | sh -s -- --imposta-gioco {ident}", testo)
                self.assertIn(f"curl -L 070293.xyz/{corto} | sh -s -- --ripristina-gioco {ident}", testo)

    def test_idempotente(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                una = genera_guide.genera(nome)
                due = genera_guide.genera(nome, una)
                self.assertEqual(una, due)

    def test_prima_esecuzione_e_errori(self):
        vecchia = ("<body>\n    <!-- SEZIONE 2: X -->\n    <section>x</section>\n\n"
                   f"    {genera_guide.PRIMA_SEZIONE}\n    <section id=\"rdr2\">vecchio</section>\n\n"
                   f"    {genera_guide.DOPO_SEZIONI}\n    <section>6</section>\n</body>\n")
        blocco = genera_guide.blocco_giochi("rogallyz1x")
        nuova = genera_guide.sostituisci_blocco(vecchia, blocco)
        self.assertIn(genera_guide.INIZIO, nuova)
        self.assertNotIn("vecchio", nuova)
        self.assertIn("<section>x</section>", nuova)
        self.assertIn(f"{genera_guide.DOPO_SEZIONI}\n    <section>6</section>", nuova)
        self.assertEqual(genera_guide.sostituisci_blocco(nuova, blocco), nuova)
        with self.assertRaises(SystemExit):
            genera_guide.sostituisci_blocco("<body>niente</body>", blocco)
        with self.assertRaises(SystemExit):
            genera_guide.sostituisci_blocco(f"<body>{genera_guide.INIZIO}</body>", blocco)


class TestScorciatoieTelefono(unittest.TestCase):
    def test_sincronizza_crea_i_rimandi(self):
        with tempfile.TemporaryDirectory() as cartella:
            dest = Path(cartella)
            pubblica_070293.sincronizza(dest)
            for scorciatoia, destinazione in (("giochi-oxp", "ottimizzazione_onexplayer_1s.html"),
                                              ("giochi-ally", "ottimizzazione_rog_ally.html")):
                testo = (dest / scorciatoia / "index.html").read_text(encoding="utf-8")
                self.assertIn(f'<meta http-equiv="refresh" content="0; url=/guide/{destinazione}">', testo)
                self.assertIn(f'<a href="/guide/{destinazione}">', testo)
                self.assertIn('<meta charset="utf-8">', testo)
                self.assertIn('name="viewport"', testo)
                self.assertTrue((dest / "guide" / destinazione).is_file())


if __name__ == "__main__":
    unittest.main()
