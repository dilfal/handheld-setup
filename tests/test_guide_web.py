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


PAROLE_VIETATE_SU_WINDOWS = ["Proton", "Gaming Mode", "Dolphin", "Bazzite Handheld Setup", "Handheld Daemon", "Desktop Mode", "Applica"]
VOID = {"meta", "link", "br", "img", "input", "hr"}


class RaccoltaBlocchi(HTMLParser):
    """Il testo di ogni elemento che ha la classe richiesta (con href e id degli elementi che contiene), più gli id della pagina."""

    def __init__(self, classe: str):
        super().__init__()
        self.classe = classe
        self.pila: list[tuple[str, bool]] = []
        self.blocchi: list[str] = []
        self.id: list[str] = []

    def _dentro(self) -> bool:
        return any(d for _, d in self.pila)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.id.append(a["id"])
        if tag in VOID:
            return
        inizia = self.classe in (a.get("class") or "").split()
        if inizia:
            self.blocchi.append("")
        self.pila.append((tag, inizia or self._dentro()))
        if self._dentro():
            self.blocchi[-1] += " ".join(v or "" for k, v in attrs if k in ("href", "id")) + " "

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.pila and self.pila[-1][0] != tag:
            self.pila.pop()
        if self.pila:
            self.pila.pop()

    def handle_data(self, dati):
        if self._dentro() and self.blocchi:
            self.blocchi[-1] += dati


def blocchi(nome: str, classe: str) -> RaccoltaBlocchi:
    r = RaccoltaBlocchi(classe)
    r.feed(pagina(nome))
    r.close()
    return r


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
                    self.assertIn(f'<section id="{g.id}" class="card solo-bazzite">', testo)
                    self.assertIn(f'<section id="{g.id}-windows" class="card solo-windows">', testo)
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
        """Per ciascun sistema l'indice (la sua variante) elenca id e titolo h2 delle sue sezioni, nello stesso ordine."""
        for nome in genera_guide.PAGINE:
            for sistema in ("bazzite", "windows"):
                with self.subTest(pagina=nome, sistema=sistema):
                    testo = pagina(nome)
                    indice_html = testo.split('<div class="nav-summary">')[1].split("</div>")[0]
                    variante = re.search(rf'<ul class="solo-{sistema}">(.*?)</ul>', indice_html, re.S).group(1)
                    indice = [(i, html.unescape(t)) for i, t in re.findall(r'<li><a href="#([^"]+)">(.*?)</a></li>', variante)]
                    sezioni = [(i, html.unescape(t)) for i, t in re.findall(
                        rf'<section id="([^"]+)" class="card solo-{sistema}">\s*<h2>(.*?)</h2>', testo)]
                    self.assertEqual(indice, sezioni)
                    self.assertEqual(len(sezioni), 6)

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
                self.assertEqual(blocco.count("<section "), 6)
                self.assertEqual(blocco.count('class="card solo-bazzite"'), 3)
                self.assertEqual(blocco.count('class="card solo-windows"'), 3)

    def test_collegamenti_interni_esistono(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                testo = pagina(nome)
                for ancora in set(re.findall(r'href="#([^"]+)"', testo)):
                    self.assertIn(f'id="{ancora}"', testo, ancora)

    def test_id_unici_e_collegamenti_windows(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                ids = blocchi(nome, "solo-windows").id
                self.assertEqual(sorted({i for i in ids if ids.count(i) > 1}), [])
                tutti = blocchi(nome, "card").id
                self.assertEqual(sorted({i for i in tutti if tutti.count(i) > 1}), [])
                for ident in ("intro-windows", "come-avviare-windows", "problemi-windows", *(f"{g}-windows" for g in ID_GIOCHI)):
                    self.assertIn(ident, ids)
                testo = pagina(nome)
                for g in ID_GIOCHI:          # il rimando «sezione 2» della variante Windows punta alla sezione 2 di Windows
                    sezione = testo.split(f'<section id="{g}-windows"')[1].split("</section>")[0]
                    self.assertIn('<a href="#come-avviare-windows">sezione 2</a>', sezione)
                    self.assertNotIn('href="#come-avviare"', sezione)

    def test_nessun_segnaposto_nella_variante_windows(self):
        for nome, profilo in genera_guide.PAGINE.items():
            with self.subTest(pagina=nome):
                testo = "\n".join(blocchi(nome, "solo-windows").blocchi)
                self.assertIsNone(re.search(r"\{[A-Za-z_]+\}", testo))
                for g in carica_guide(profilo, "windows"):
                    for p in g.passi:
                        for t in (p.titolo, p.testo, *(x for voce in p.voci for x in voce)):
                            self.assertIsNone(re.search(r"[{}]", t), t)

    def test_variante_windows_senza_parole_di_bazzite(self):
        """Nei blocchi solo-windows (parti a mano e giochi) non compaiono i nomi del mondo Bazzite, nemmeno «Applica»."""
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                parti = blocchi(nome, "solo-windows").blocchi
                self.assertTrue(any("Winhanced" in b for b in parti))
                for b in parti:
                    for parola in PAROLE_VIETATE_SU_WINDOWS:
                        self.assertNotIn(parola.lower(), b.lower())

    def test_la_variante_windows_ha_i_suoi_contenuti(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                testo = "\n".join(blocchi(nome, "solo-windows").blocchi)
                for frase in ("Gioca in locale", "Winhanced", "C:\\Giochi", "VCRUNTIME140.dll", "RivaTuner Statistics Server",
                              "OneDrive\\Documenti", "Visual C++ 2015-2022", "DirectX End-User Runtime"):
                    self.assertIn(frase, testo)
        self.assertIn("irm 070293.xyz/oxp-win | iex", pagina("ottimizzazione_onexplayer_1s.html"))
        self.assertNotIn("oxp-win", pagina("ottimizzazione_rog_ally.html"))
        # Il limite a 30 di The Witcher 3 su Windows sta nel menu del gioco.
        oxp = pagina("ottimizzazione_onexplayer_1s.html").split('<section id="witcher3-windows"')[1].split("</section>")[0]
        self.assertIn("<td>Fotogrammi al secondo massimi (Maximum FPS)</td><td>30 (il limite a 30 si mette direttamente qui)</td>", oxp)

    def test_selettore_del_sistema(self):
        for nome in genera_guide.PAGINE:
            with self.subTest(pagina=nome):
                testo = pagina(nome)
                self.assertIn('<html lang="it" data-sistema="bazzite">', testo)
                testa = testo.split("</head>")[0]
                for pezzo in ("new URLSearchParams(location.search).get(\"sistema\")", "-windows$", 'localStorage.getItem("guida-sistema")',
                              "navigator.userAgent", '[data-sistema="bazzite"] .solo-windows { display: none !important; }',
                              '[data-sistema="windows"] .solo-bazzite { display: none !important; }', "min-height: 44px"):
                    self.assertIn(pezzo, testa)
                self.assertEqual(testa.count("try {"), testa.count("catch (e)"))
                bottoni = re.findall(r'<button type="button" data-sistema="(bazzite|windows)" aria-pressed="(true|false)">', testo)
                self.assertEqual(bottoni, [("bazzite", "true"), ("windows", "false")])
                self.assertIn(">Windows (Winhanced)</button>", testo)
                self.assertIn('localStorage.setItem("guida-sistema", sistema)', testo)
                # il riquadro sta subito sotto l'intestazione e sopra l'indice
                self.assertLess(testo.index("</header>"), testo.index('class="selettore"'))
                self.assertLess(testo.index('class="selettore"'), testo.index('class="nav-summary"'))

    def test_comandi_dei_pulsanti_dell_app(self):
        """Ogni passo «config» ha i due comandi con la scorciatoia giusta del dispositivo."""
        for nome, corto in (("ottimizzazione_onexplayer_1s.html", "oxp"), ("ottimizzazione_rog_ally.html", "ally")):
            testo = pagina(nome)
            for ident in ID_GIOCHI:
                self.assertIn(f"curl -L 070293.xyz/{corto} | sh -s -- --imposta-gioco {ident}", testo)
                self.assertIn(f"curl -L 070293.xyz/{corto} | sh -s -- --ripristina-gioco {ident}", testo)

    def test_dati_di_default_senza_sistema(self):
        """`carica_guide(profilo)` è la variante Bazzite di sempre: nessuna traccia di Winhanced e «Applica» presente."""
        for profilo in ("onexplayer1s", "rogallyz1x", "generico"):
            with self.subTest(profilo=profilo):
                base = carica_guide(profilo)
                self.assertEqual(base, carica_guide(profilo, "bazzite"))
                testo = repr(base)
                self.assertNotIn("Winhanced", testo)
                self.assertNotIn("Gioca in locale", testo)
                self.assertTrue(all(any(p.azione == "config" for p in g.passi) for g in base))
                win = carica_guide(profilo, "windows")
                self.assertTrue(all(p.azione == "" and p.nota_app == "" for g in win for p in g.passi))
                self.assertLess(len(win[0].passi), len(base[0].passi))
        with self.assertRaises(ValueError):
            carica_guide("generico", "linux")

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


class TestIndiceSottodominio(unittest.TestCase):
    def test_due_ingressi_per_scheda_e_collegamenti_accettati(self):
        from tools import pubblica_guide
        testo = (RADICE / "guide" / "sottodominio" / "index.html").read_text(encoding="utf-8")
        for pagina_ott in ("ottimizzazione_onexplayer_1s.html", "ottimizzazione_rog_ally.html"):
            self.assertIn(f'<a href="{pagina_ott}?sistema=bazzite">Bazzite</a>', testo)
            self.assertIn(f'<a href="{pagina_ott}?sistema=windows">Windows (Winhanced)</a>', testo)
            self.assertNotIn(f'<a href="{pagina_ott}" ', testo)
        aperti = 0                       # nessun <a> dentro un <a>
        for chiusura in re.findall(r"<(/?)a[\s>]", testo):
            aperti += -1 if chiusura else 1
            self.assertIn(aperti, (0, 1))
        self.assertEqual(aperti, 0)
        self.assertEqual(pubblica_guide.controlla(pubblica_guide.raccogli_pagine()), [])

    def test_il_controllo_dei_collegamenti_ignora_query_e_ancora(self):
        from tools import pubblica_guide
        pagine = pubblica_guide.raccogli_pagine()
        with tempfile.TemporaryDirectory() as cartella:
            finta = Path(cartella) / "x.html"
            finta.write_text('<a href="index.html?sistema=windows#a">ok</a><a href="manca.html?sistema=windows">no</a>', encoding="utf-8")
            problemi = pubblica_guide.controlla({**pagine, "x.html": finta})
        self.assertTrue(any("manca.html?sistema=windows" in p for p in problemi), problemi)
        self.assertFalse(any("index.html?sistema=windows#a" in p for p in problemi), problemi)


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
