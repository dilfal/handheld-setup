"""Test della logica (senza interfaccia Qt). Eseguire da `bazzite-handheld-setup`: python -I -m unittest discover -s tests"""

import contextlib
import io
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bhs import __main__ as punto_ingresso  # noqa: E402
from bhs import catalog, cli, detect, giochi, piano, profiles, runner, tweaks  # noqa: E402


def finto_sistema(radice: Path, vendor: str, prodotto: str, os_release: str = 'ID=bazzite\nPRETTY_NAME="Bazzite"\n'):
    dmi = radice / "sys/class/dmi/id"
    dmi.mkdir(parents=True)
    (dmi / "sys_vendor").write_text(vendor)
    (dmi / "product_name").write_text(prodotto)
    (radice / "etc").mkdir()
    (radice / "etc/os-release").write_text(os_release)
    (radice / "proc").mkdir()
    (radice / "proc/cmdline").write_text("quiet video=eDP-1:panel_orientation=left_side_up")


class TestProfili(unittest.TestCase):
    def setUp(self):
        self.p = profiles.carica_profili()

    def test_tre_profili(self):
        self.assertEqual({x.id for x in self.p}, {"onexplayer1s", "rogallyz1x", "generico"})

    def trova(self, fornitore=None, prodotto=None, scheda_fornitore=None, scheda_nome=None):
        return profiles.trova_profilo(self.p, {"fornitore": fornitore, "prodotto": prodotto,
                                               "scheda_fornitore": scheda_fornitore, "scheda_nome": scheda_nome}).id

    def test_rilevamento(self):
        self.assertEqual(self.trova("ASUSTeK COMPUTER INC.", "ROG Ally RC71L_RC71L"), "rogallyz1x")
        self.assertEqual(self.trova("ONE-NETBOOK TECHNOLOGY CO., LTD.", "ONE XPLAYER"), "onexplayer1s")
        self.assertEqual(self.trova("Valve", "Jupiter"), "generico")
        self.assertEqual(self.trova(), "generico")

    def test_onexplayer_da_scheda(self):
        # Il kernel riconosce i OneXPlayer da board_vendor/board_name: basta anche solo la scheda.
        self.assertEqual(self.trova(scheda_fornitore="ONE-NETBOOK", scheda_nome="ONE XPLAYER"), "onexplayer1s")

    def test_altri_onexplayer_non_prendono_il_profilo_1(self):
        # OneXPlayer 2 e X1 sono altri dispositivi (altra CPU): meglio "generico" che il profilo sbagliato.
        self.assertEqual(self.trova("ONE-NETBOOK", "ONEXPLAYER 2 ARP23"), "generico")
        self.assertEqual(self.trova(scheda_fornitore="ONE-NETBOOK", scheda_nome="ONEXPLAYER X1 A"), "generico")

    def test_ally_x_non_e_z1(self):
        # ROG Ally X (RC72LA) è un altro dispositivo: non deve prendere il profilo Z1 Extreme.
        self.assertEqual(self.trova("ASUSTeK COMPUTER INC.", "ROG Ally X RC72LA"), "generico")

    def test_tweak_dei_profili_esistono(self):
        t = tweaks.tutti_i_tweak()
        for p in self.p:
            for tid in p.consigliati + p.avanzati:
                self.assertIn(tid, t, f"{p.id}: tweak sconosciuto {tid}")


class TestCatalogo(unittest.TestCase):
    def test_voci_valide(self):
        voci = catalog.carica_catalogo()
        self.assertGreater(len(voci), 10)
        ids = [v.id for v in voci]
        self.assertEqual(len(ids), len(set(ids)), "id duplicati")
        for v in voci:
            self.assertIn(v.categoria, catalog.CATEGORIE)
            self.assertIn(v.tipo, ("flatpak", "brew", "ujust", "manuale"))

    def test_rilevamento_installata(self):
        a = next(v for v in catalog.carica_catalogo() if v.id == "heroic")
        self.assertTrue(a.installata({"com.heroicgameslauncher.hgl"}))
        self.assertFalse(a.installata(set()))
        self.assertEqual(a.comando()[:3], ["flatpak", "install", "--user"])

    def test_manuale_senza_comando(self):
        a = next(v for v in catalog.carica_catalogo() if v.id == "emudeck")
        self.assertIsNone(a.comando())

    def test_decky_senza_menu_interattivo(self):
        # «ujust setup-decky» senza argomento apre un menu a scelta: dalla finestra (stdin vuoto) non può
        # funzionare. Con «install» la ricetta procede da sola; ricetta e argomento sono due parole distinte.
        a = next(v for v in catalog.carica_catalogo() if v.id == "decky")
        self.assertEqual(a.comando(), ["ujust", "setup-decky", "install"])


class TestRilevamento(unittest.TestCase):
    def test_sistema_finto(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            finto_sistema(r, "ASUSTeK COMPUTER INC.", "ROG Ally RC71L_RC71L")
            s = detect.raccogli(r, esegui=lambda argv: None, esiste=lambda n: False)
            self.assertTrue(s.e_bazzite)
            self.assertEqual(s.dmi["prodotto"], "ROG Ally RC71L_RC71L")
            self.assertIn("panel_orientation", s.orientamento_pannello)
            self.assertEqual(s.soglie_carica, [])
            self.assertIn("sconosciuta", detect.testo_diagnosi(s))

    def test_non_bazzite(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            finto_sistema(r, "x", "y", os_release='ID=ubuntu\nPRETTY_NAME="Ubuntu"\n')
            s = detect.raccogli(r, esegui=lambda argv: None, esiste=lambda n: False)
            self.assertFalse(s.e_bazzite)

    def test_flatpak(self):
        out = "com.discordapp.Discord\norg.mozilla.firefox\n"
        self.assertEqual(detect.flatpak_installati(lambda argv: out),
                         {"com.discordapp.Discord", "org.mozilla.firefox"})


class TestNorbc(unittest.TestCase):
    @unittest.skipUnless(shutil.which("sh"), "serve una shell POSIX")
    def test_script_idempotente(self):
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, "HOME": d}
            for _ in range(2):  # due giri: la riga deve restare una sola
                r = subprocess.run(["sh", "-c", tweaks.SCRIPT_NORBC], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            f = Path(d) / tweaks.FILE_NORBC
            self.assertEqual(f.read_text().splitlines(), ["INTEL_DEBUG=norbc"])
            self.assertEqual(tweaks._norbc(detect.Sistema(), home=Path(d)), "attivo")

    def test_stato_inattivo_senza_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(tweaks._norbc(detect.Sistema(), home=Path(d)), "inattivo")

    def test_profilo_oxp_lo_consiglia(self):
        p = next(x for x in profiles.carica_profili() if x.id == "onexplayer1s")
        self.assertIn("intel_norbc", p.consigliati)
        self.assertIn("scala_display_150", p.consigliati)
        self.assertIn("scala_display_125", p.avanzati)


QUIRK_FINTO = (
    '# OXP 60Hz Devices\n'
    'OXP_LIST="ONE XPLAYER:ONEXPLAYER 1 T08:ONEXPLAYER mini A07"\n'
    'if [[ ":$OXP_LIST:" =~ ":$SYS_ID:"  ]]; then\n'
    '  DRM_MODE=fixed\n'
    '  PANEL_TYPE=external\n'
    '  ORIENTATION=left\n'
    'fi\n'
    'OXP_X1_LIST="ONEXPLAYER X1 i"\n'
    'if [[ ":$OXP_X1_LIST:" =~ ":$SYS_ID:"  ]]; then\n'
    '  PANEL_TYPE=internal\n'
    'fi\n'
    'if [[ ":$SYS_ID:" =~ :ONEXPLAYER\\ G1\\ (A|i): ]]; then\n'
    '  PANEL_TYPE=internal\n'
    'fi\n'
)


class TestLuminosita(unittest.TestCase):
    def quirk(self, prodotto):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / detect.QUIRK_GAMESCOPE
            f.parent.mkdir(parents=True)
            f.write_text(QUIRK_FINTO)
            return detect.quirk_pannello(prodotto, Path(d))

    def test_quirk_del_prodotto(self):
        self.assertEqual(self.quirk("ONE XPLAYER"), "external")
        self.assertEqual(self.quirk("ONEXPLAYER mini A07"), "external")
        self.assertEqual(self.quirk("ONEXPLAYER X1 i"), "internal")
        self.assertIsNone(self.quirk("ROG Ally RC71L_RC71L"))
        self.assertIsNone(self.quirk("XPLAYER"))   # solo voci intere, non pezzi di nome
        self.assertIsNone(self.quirk(None))

    def test_senza_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(detect.quirk_pannello("ONE XPLAYER", Path(d)))
            self.assertEqual(detect.retroilluminazione(Path(d)), [])

    def test_retroilluminazione(self):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "sys/class/backlight/intel_backlight"
            b.mkdir(parents=True)
            (b / "type").write_text("raw\n")
            (b / "brightness").write_text("300\n")
            (b / "max_brightness").write_text("7500\n")
            self.assertEqual(detect.retroilluminazione(Path(d)), ["intel_backlight (raw, 300/7500)"])

    @unittest.skipUnless(shutil.which("sh"), "serve una shell POSIX")
    def test_script_sostituisce_e_non_duplica(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / tweaks.FILE_NORBC
            f.parent.mkdir(parents=True)
            f.write_text("INTEL_DEBUG=norbc\nPANEL_TYPE=external\n")
            self.assertEqual(tweaks._pannello(detect.Sistema(), home=Path(d)), "inattivo")
            env = {**os.environ, "HOME": d}
            for _ in range(2):
                r = subprocess.run(["sh", "-c", tweaks.SCRIPT_PANNELLO], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(f.read_text().splitlines(), ["INTEL_DEBUG=norbc", "PANEL_TYPE=internal"])
            self.assertEqual(tweaks._pannello(detect.Sistema(), home=Path(d)), "attivo")

    @unittest.skipUnless(shutil.which("sh"), "serve una shell POSIX")
    def test_script_senza_file(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(["sh", "-c", tweaks.SCRIPT_PANNELLO], env={**os.environ, "HOME": d},
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((Path(d) / tweaks.FILE_NORBC).read_text().splitlines(), ["PANEL_TYPE=internal"])

    def test_nota_e_profilo(self):
        self.assertIn("confermata", tweaks._nota_pannello(detect.Sistema(quirk_pannello="external")))
        self.assertIn("non confermata", tweaks._nota_pannello(detect.Sistema()))
        p = next(x for x in profiles.carica_profili() if x.id == "onexplayer1s")
        self.assertIn("luminosita_game_mode", p.avanzati)   # mai provata: non tra le consigliate


class TestCli(unittest.TestCase):
    def test_elenco(self):
        t = cli.testo_elenco(detect.Sistema())
        for tid in ("intel_norbc", "scala_display_125", "limite_carica_80"):
            self.assertIn(tid, t)

    def test_elenco_allineato(self):
        # Lo stato comincia alla stessa colonna in ogni riga, anche per l'ID più lungo.
        righe = cli.testo_elenco(detect.Sistema()).splitlines()[1:]
        largo = max(len(i) for i in tweaks.tutti_i_tweak())
        for r in righe:
            self.assertEqual(r[2 + largo], " ", r)
            self.assertNotEqual(r[3 + largo], " ", r)

    def test_sconosciuto(self):
        righe = []
        self.assertEqual(cli.applica(["non_esiste"], True, detect.Sistema(), righe.append), 2)

    def test_simulazione(self):
        righe = []
        self.assertEqual(cli.applica(["intel_norbc"], True, detect.Sistema(), righe.append), 0)
        self.assertTrue(any("simulazione" in r for r in righe))

    def test_non_supportato_salta(self):
        righe = []
        # senza kscreen-doctor il tweak è non supportato: niente da fare, codice 2
        self.assertEqual(cli.applica(["scala_display_125"], True, detect.Sistema(), righe.append), 2)


class TestLimiteCarica(unittest.TestCase):
    BAT = "/sys/class/power_supply/BAT0/charge_control_end_threshold"

    def test_script(self):
        s = tweaks.script_limite_carica([self.BAT])
        self.assertIn(f"echo 80 > {self.BAT}", s)
        self.assertIn("systemctl enable --now bhs-limite-carica.service", s)
        self.assertIn("WantedBy=multi-user.target", s)
        self.assertTrue(s.startswith("set -e\n"))

    def test_comandi_solo_con_percorsi_validi(self):
        t = tweaks.tutti_i_tweak()["limite_carica_80"]
        self.assertEqual(t.comandi_per(detect.Sistema()), [])
        self.assertEqual(t.stato(detect.Sistema()), "non_supportato")
        cmd = t.comandi_per(detect.Sistema(soglie_carica=[self.BAT]))
        self.assertEqual(cmd[0][:3], ["pkexec", "sh", "-c"])

    def test_percorso_sospetto_scartato(self):
        # I percorsi finiscono in uno script eseguito come root: forme strane vanno rifiutate.
        cattivo = "/sys/class/power_supply/BAT0/charge_control_end_threshold; rm -rf /"
        t = tweaks.tutti_i_tweak()["limite_carica_80"]
        self.assertEqual(t.comandi_per(detect.Sistema(soglie_carica=[cattivo])), [])

    def test_stato_attivo(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "charge_control_end_threshold"
            f.write_text("80\n")
            self.assertEqual(detect.leggi_soglia(str(f)), "80")

    def test_persistenza_standby_e_udev(self):
        s = tweaks.script_limite_carica([self.BAT])
        self.assertIn("sleep.target", s)
        self.assertIn("suspend.target", s)
        self.assertIn(tweaks.REGOLA_UDEV_CARICA, s)
        s100 = tweaks.script_sblocca_carica_100([self.BAT])
        self.assertIn(f"echo 100 > {self.BAT}", s100)
        self.assertIn(tweaks.REGOLA_UDEV_CARICA, s100)

    def test_servizio_non_riscrive_e_udev_non_blocca(self):
        # La regola udev rilancia il servizio a ogni evento della batteria: non deve bloccare udev e il
        # servizio non deve riscrivere un valore già giusto (una scrittura può generare un altro evento).
        s = tweaks.script_limite_carica([self.BAT])
        self.assertIn("systemctl start --no-block bhs-limite-carica.service", s)
        self.assertIn(f"ExecStart=-/bin/sh -c '[ \"$$(cat {self.BAT} 2>/dev/null)\" = 80 ] || echo 80 > {self.BAT}'", s)

    @unittest.skipUnless(shutil.which("sh") and os.name == "posix", "serve ambiente POSIX per lo script")
    def test_avviso_riprova_se_la_notifica_fallisce(self):
        # In Game Mode nessuno mostra le notifiche: l'avviso non va segnato come dato, così riparte al giro dopo.
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            home, bat, cestino, run = base / "home", base / "ps" / "BAT0", base / "bin", base / "run"
            for c in (home, bat, cestino, run):
                c.mkdir(parents=True)
            finto = cestino / "notify-send"
            finto.write_text('#!/bin/sh\necho x >> "$BHS_CONTA"\nexit "$BHS_RC"\n', encoding="utf-8")
            finto.chmod(0o755)
            conta = base / "conta"
            env = {**os.environ, "HOME": str(home), "XDG_RUNTIME_DIR": str(run), "BHS_BATTERIE": str(base / "ps"),
                   "BHS_CONTA": str(conta), "PATH": f"{cestino}{os.pathsep}{os.environ['PATH']}"}
            r = subprocess.run(["sh", "-c", tweaks.SCRIPT_CURA_BATTERIA_UTENTE], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            controllo = home / tweaks.SCRIPT_CHECK_CARICA
            segno = run / "bhs-cura-batteria-avvisato"

            def giro(stato, carica, rc):
                (bat / "status").write_text(stato + "\n")
                (bat / "capacity").write_text(f"{carica}\n")
                esito = subprocess.run(["sh", str(controllo)], env={**env, "BHS_RC": str(rc)}, capture_output=True)
                self.assertEqual(esito.returncode, 0)   # il servizio non deve mai risultare fallito
                return len(conta.read_text().splitlines()) if conta.exists() else 0

            self.assertEqual(giro("Charging", 70, 0), 0)
            self.assertEqual(giro("Charging", 80, 1), 1)      # notifica fallita…
            self.assertFalse(segno.exists())                  # …quindi non segnata
            self.assertEqual(giro("Charging", 81, 0), 2)      # riprova e riesce
            self.assertTrue(segno.exists())
            self.assertEqual(giro("Charging", 90, 0), 2)      # non ripete l'avviso
            self.assertEqual(giro("Discharging", 77, 0), 2)
            self.assertFalse(segno.exists())                  # pronto per la prossima carica
            self.assertEqual(giro("Charging", 80, 0), 3)

    @unittest.skipUnless(shutil.which("sh"), "serve una shell POSIX")
    def test_modalita_utente_senza_soglia_hardware(self):
        # Sul OneXPlayer 1S l'EC non espone charge_control_end_threshold, ma BAT0 esiste:
        # la Cura Batteria attiva il timer utente con avviso all'80% senza pkexec.
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            sist = detect.Sistema(batterie=["/sys/class/power_supply/BAT0"])
            t80 = tweaks.tutti_i_tweak()["limite_carica_80"]
            t100 = tweaks.tutti_i_tweak()["carica_100"]
            cmd = t80.comandi_per(sist)
            self.assertEqual(cmd[0][:2], ["sh", "-c"])
            self.assertEqual(tweaks._soglia_carica(sist, home=home), "inattivo")
            env = {**os.environ, "HOME": d}
            r = subprocess.run(["sh", "-c", tweaks.SCRIPT_CURA_BATTERIA_UTENTE], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((home / tweaks.TIMER_UTENTE_CARICA).is_file())
            self.assertTrue((home / tweaks.SCRIPT_CHECK_CARICA).is_file())
            self.assertEqual(tweaks._soglia_carica(sist, home=home), "attivo")
            self.assertEqual(tweaks._stato_carica_100(sist, home=home), "inattivo")
            r2 = subprocess.run(["sh", "-c", tweaks.SCRIPT_RIMUOVI_CURA_UTENTE], env=env, capture_output=True, text=True)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertEqual(tweaks._soglia_carica(sist, home=home), "inattivo")
            self.assertEqual(tweaks._stato_carica_100(sist, home=home), "attivo")


class TestTdpRapl(unittest.TestCase):
    RAPL = "/sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw"

    def test_script_tdp(self):
        s = tweaks.script_tdp_rapl(20, 25)
        self.assertIn("echo 20000000 > /sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw", s)
        self.assertIn("echo 25000000 > /sys/class/powercap/intel-rapl:0/constraint_1_power_limit_uw", s)
        self.assertIn("systemctl enable --now bhs-tdp-rapl.service", s)
        self.assertIn("sleep.target", s)

    def test_comandi_e_validazione_percorso(self):
        t20 = tweaks.tutti_i_tweak()["tdp_20w"]
        self.assertEqual(t20.stato(detect.Sistema()), "non_supportato")
        self.assertEqual(t20.comandi_per(detect.Sistema()), [])
        cattivo = "/sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw; rm -rf /"
        self.assertEqual(t20.comandi_per(detect.Sistema(rapl_pl1=cattivo)), [])
        cmd = t20.comandi_per(detect.Sistema(rapl_pl1=self.RAPL))
        self.assertEqual(cmd[0][:3], ["pkexec", "sh", "-c"])


class TestProfiloFisso(unittest.TestCase):
    ALLY = {"fornitore": "ASUSTeK COMPUTER INC.", "prodotto": "ROG Ally RC71L_RC71L"}
    OXP = {"fornitore": "ONE-NETBOOK TECHNOLOGY CO., LTD.", "prodotto": "ONE XPLAYER"}

    def setUp(self):
        self.p = profiles.carica_profili()

    def test_per_id(self):
        self.assertEqual(profiles.profilo_per_id(self.p, "rogallyz1x").id, "rogallyz1x")
        self.assertIsNone(profiles.profilo_per_id(self.p, "boh"))

    def test_nessun_avviso_sul_dispositivo_giusto(self):
        self.assertIsNone(profiles.avviso_incoerenza(profiles.profilo_per_id(self.p, "rogallyz1x"), self.ALLY))
        self.assertIsNone(profiles.avviso_incoerenza(profiles.profilo_per_id(self.p, "onexplayer1s"), self.OXP))

    def test_avviso_sul_dispositivo_sbagliato(self):
        # Lo script del OneXPlayer lanciato su una ROG Ally deve avvisare, non applicare in silenzio.
        a = profiles.avviso_incoerenza(profiles.profilo_per_id(self.p, "onexplayer1s"), self.ALLY)
        self.assertIn("OneXPlayer 1S", a)
        self.assertIn("ROG Ally", a)
        self.assertIsNotNone(profiles.avviso_incoerenza(profiles.profilo_per_id(self.p, "rogallyz1x"), {}))

    def test_generico_senza_avviso(self):
        self.assertIsNone(profiles.avviso_incoerenza(profiles.profilo_per_id(self.p, "generico"), self.OXP))

    def test_profilo_sconosciuto_da_riga_di_comando(self):
        self.assertEqual(punto_ingresso.main(["--profilo", "boh"]), 2)


class TestInstallatoriDedicati(unittest.TestCase):
    RADICE = Path(__file__).resolve().parent.parent

    def test_sincronizzati_con_install_sh(self):
        r = subprocess.run([sys.executable, "-I", str(self.RADICE / "tools" / "genera_installatori.py"), "--verifica"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_profilo_giusto_in_ogni_script(self):
        for nome, ident in (("install-onexplayer.sh", "onexplayer1s"), ("install-rog-ally.sh", "rogallyz1x")):
            testo = (self.RADICE / nome).read_text(encoding="utf-8")
            self.assertIn(f'PROFILO_FISSO="{ident}"', testo)
            self.assertIn(nome, testo)
            self.assertNotIn("GENERICO", testo)
        generico = (self.RADICE / "install.sh").read_text(encoding="utf-8")
        self.assertIn('PROFILO_FISSO=""', generico)

    def test_ogni_profilo_dedicato_esiste(self):
        ids = {p.id for p in profiles.carica_profili()}
        for ident in ("onexplayer1s", "rogallyz1x"):
            self.assertIn(ident, ids)

    @unittest.skipUnless(shutil.which("sh"), "serve una shell POSIX")
    def test_sintassi_sh(self):
        for nome in ("install.sh", "install-onexplayer.sh", "install-rog-ally.sh"):
            r = subprocess.run(["sh", "-n", str(self.RADICE / nome)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{nome}: {r.stderr}")

    @unittest.skipUnless(shutil.which("sh") and os.name == "posix", "serve ambiente POSIX per lo script")
    def test_console_auto_onexplayer(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "WAYLAND_DISPLAY": "",
                "DISPLAY": "",
                "BHS_FORCE": "1",
                "BHS_NO_REBOOT": "1",
                "BHS_SKIP_VENV": "1",
            }
            r = subprocess.run(["sh", str(self.RADICE / "install-onexplayer.sh")],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            norbc = home / ".config/environment.d/10-gamescope-session.conf"
            self.assertTrue(norbc.is_file(), "file 10-gamescope-session.conf non creato")
            self.assertIn("INTEL_DEBUG=norbc", norbc.read_text(encoding="utf-8").splitlines())
            autostart = home / ".config/autostart/bhs-first-run.desktop"
            self.assertTrue(autostart.is_file(), "autostart bhs-first-run.desktop non creato")
            self.assertIn("install-onexplayer.sh", autostart.read_text(encoding="utf-8"))
            menu = home / ".local/share/applications/bazzite-handheld-setup-onexplayer1s.desktop"
            self.assertTrue(menu.is_file(), "voce di menu non creata")

    @unittest.skipUnless(shutil.which("sh") and os.name == "posix", "serve ambiente POSIX per lo script")
    def test_console_auto_generico_rileva_oxp_da_dmi(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "home"
            dmi = Path(d) / "dmi"
            home.mkdir()
            dmi.mkdir()
            (dmi / "product_name").write_text("ONE XPLAYER\n", encoding="utf-8")
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "WAYLAND_DISPLAY": "",
                "DISPLAY": "",
                "BHS_FORCE": "1",
                "BHS_NO_REBOOT": "1",
                "BHS_SKIP_VENV": "1",
                "BHS_DMI_DIR": str(dmi),
            }
            r = subprocess.run(["sh", str(self.RADICE / "install.sh")],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            norbc = home / ".config/environment.d/10-gamescope-session.conf"
            self.assertTrue(norbc.is_file())
            self.assertIn("INTEL_DEBUG=norbc", norbc.read_text(encoding="utf-8").splitlines())

    def _avvia_in_console_senza_interfaccia(self, script, *argomenti, prima=None, dopo=None):
        """Lancia lo script come da console (nessuna sessione grafica) su un OneXPlayer finto, con le opzioni date.

        Lavora su una copia dell'app in una cartella temporanea e mette in testa al PATH un finto `systemctl` che
        scrive un file se riceve `reboot`: se partisse il riavvio automatico, il file comparirebbe (e il computer
        non si riavvia). `prima(app)` e `dopo(home, app)`, se date, girano prima e dopo lo script, a cartelle ancora
        presenti.
        Restituisce (esito, norbc scritto, autostart creato, .venv creato, riavvio partito).
        """
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            app = base / "app"
            shutil.copytree(self.RADICE, app, ignore=shutil.ignore_patterns(
                "__pycache__", ".git", ".venv", "shots", "OneDrive_*", "guide", "assets"))
            home = base / "home"
            dmi = base / "dmi"
            finto = base / "bin"
            for cartella in (home, dmi, finto):
                cartella.mkdir()
            (dmi / "product_name").write_text("ONE XPLAYER\n", encoding="utf-8")
            riavvio = base / "riavvio.txt"
            systemctl = finto / "systemctl"
            # Il rilevamento di sistema interroga systemctl per altri motivi: conta solo `systemctl reboot`.
            systemctl.write_text(f'#!/bin/sh\n[ "$1" = reboot ] && echo reboot > "{riavvio}"\nexit 0\n',
                                 encoding="utf-8")
            systemctl.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{finto}{os.pathsep}{os.environ['PATH']}",
                "HOME": str(home),
                "XDG_DATA_HOME": str(home / ".local/share"),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "WAYLAND_DISPLAY": "",
                "DISPLAY": "",
                "BHS_FORCE": "1",
                "BHS_DMI_DIR": str(dmi),
            }
            env.pop("BHS_NO_REBOOT", None)
            env.pop("BHS_SKIP_VENV", None)
            if prima:
                prima(app)
            r = subprocess.run(["sh", str(app / script), *argomenti], env=env, capture_output=True, text=True,
                               timeout=60)
            if dopo:
                dopo(home, app)
            return (
                r,
                (home / ".config/environment.d/10-gamescope-session.conf").exists(),
                (home / ".config/autostart/bhs-first-run.desktop").exists(),
                (app / ".venv").exists(),
                riavvio.exists(),
            )

    def _controlla_nessuna_modalita_automatica(self, esito):
        r, norbc, autostart, venv, riavvio = esito
        self.assertNotIn("configurazione automatica da console", r.stdout + r.stderr)
        self.assertNotIn("Riavvio automatico", r.stdout + r.stderr)
        self.assertFalse(norbc, "INTEL_DEBUG=norbc scritto senza che fosse richiesto")
        self.assertFalse(autostart, "creato l'autostart della modalità console automatica")
        self.assertFalse(venv, "creato l'ambiente Qt (PySide6) per un'opzione senza interfaccia")
        self.assertFalse(riavvio, "partito il riavvio")

    @unittest.skipUnless(shutil.which("sh") and shutil.which("python3") and os.name == "posix",
                         "servono ambiente POSIX e python3")
    def test_guida_in_console_non_avvia_la_modalita_automatica(self):
        for script in ("install-onexplayer.sh", "install.sh"):
            with self.subTest(script=script):
                esito = self._avvia_in_console_senza_interfaccia(script, "--guida", "rdr2")
                self._controlla_nessuna_modalita_automatica(esito)
                r = esito[0]
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("== Red Dead Redemption 2 ==", r.stdout)

    @unittest.skipUnless(shutil.which("sh") and shutil.which("python3") and os.name == "posix",
                         "servono ambiente POSIX e python3")
    def test_imposta_e_ripristina_gioco_in_console_non_avviano_la_modalita_automatica(self):
        # In una Home vuota il gioco non ha file di impostazioni: esito 1 con il messaggio dell'app, che prova
        # che le opzioni sono arrivate a `python3 -m bhs` così come scritte (e non a una modalità automatica).
        for script in ("install-onexplayer.sh", "install.sh"):
            for opzioni in (("--imposta-gioco", "rdr2", "--dry-run"), ("--imposta-gioco=rdr2",),
                            ("--ripristina-gioco", "rdr2")):
                with self.subTest(script=script, opzioni=opzioni):
                    esito = self._avvia_in_console_senza_interfaccia(script, *opzioni)
                    self._controlla_nessuna_modalita_automatica(esito)
                    r = esito[0]
                    self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                    self.assertIn("Non trovo i file di impostazioni di Red Dead Redemption 2", r.stderr)

    @unittest.skipUnless(shutil.which("sh") and shutil.which("curl") and os.name == "posix",
                         "servono ambiente POSIX e curl")
    def test_aggiornamento_via_pipe_conserva_il_venv(self):
        # Come «curl … | sh»: lo script arriva da stdin, scarica l'archivio e sostituisce l'installazione.
        # L'ambiente Qt (.venv con PySide6) non sta nell'archivio e non va riscaricato a ogni aggiornamento.
        import tarfile
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            archivio = base / "src.tar.gz"
            with tarfile.open(archivio, "w:gz") as tar:
                for nome in ("bhs", "data", "install.sh", "install-onexplayer.sh", "install-rog-ally.sh"):
                    tar.add(self.RADICE / nome, arcname=f"bazzite-handheld-setup-main/{nome}",
                            filter=lambda i: None if "__pycache__" in i.name else i)
            home = base / "home"
            dest = home / ".local/share/bazzite-handheld-setup"
            (dest / ".venv").mkdir(parents=True)
            (dest / ".venv" / "segno").write_text("x")
            (dest / "vecchio.txt").write_text("x")
            env = {k: v for k, v in os.environ.items() if not k.startswith("XDG_")}
            env.update(HOME=str(home), DISPLAY=":9", BHS_FORCE="1", BHS_SKIP_VENV="1",
                       BHS_URL=archivio.as_uri())
            with (self.RADICE / "install.sh").open("rb") as script:
                r = subprocess.run(["sh", "-s", "--", "--elenco"], stdin=script, env=env, cwd=d,
                                   capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("intel_norbc", r.stdout)
            self.assertTrue((dest / "bhs/__main__.py").is_file())
            self.assertFalse((dest / "vecchio.txt").exists(), "la versione precedente non è stata sostituita")
            self.assertTrue((dest / ".venv/segno").is_file(), "l'ambiente Qt è andato perso con l'aggiornamento")
            self.assertEqual(list(dest.parent.glob("bazzite-handheld-setup.*")), [])

    @staticmethod
    def _testo_finto_python(con_pyside: bool = True) -> str:
        # Risponde come un python3 con (o senza) PySide6 al controllo `-c "import PySide6"` dell'installatore.
        return ('#!/bin/sh\nif [ "$1" = "-c" ] && [ "$2" = "import PySide6" ]; then exit '
                f'{0 if con_pyside else 1}; fi\nexit 0\n')

    @classmethod
    def _finto_venv(cls, cartella: Path, con_pyside: bool = True) -> Path:
        python = cartella / ".venv/bin/python3"
        python.parent.mkdir(parents=True)
        python.write_text(cls._testo_finto_python(con_pyside), encoding="utf-8")
        python.chmod(0o755)
        return python

    @staticmethod
    def _riga_exec(home: Path) -> str:
        voci = list((home / ".local/share/applications").glob("*.desktop"))
        assert len(voci) == 1, voci
        return next(r for r in voci[0].read_text(encoding="utf-8").splitlines() if r.startswith("Exec="))

    @unittest.skipUnless(shutil.which("sh") and shutil.which("python3") and os.name == "posix",
                         "servono ambiente POSIX e python3")
    def test_opzioni_senza_interfaccia_non_rompono_l_icona_di_chi_ha_gia_il_venv(self):
        for script in ("install-onexplayer.sh", "install.sh"):
            for opzioni in (("--guida", "rdr2"), ("--elenco",), ("--ripristina-gioco", "rdr2")):
                with self.subTest(script=script, opzioni=opzioni):
                    visto = {}

                    def dopo(home, app):
                        visto["exec"] = self._riga_exec(home)
                        visto["venv"] = str(app / ".venv/bin/python3")
                        visto["contenuto"] = (app / ".venv/bin/python3").read_text(encoding="utf-8")
                        visto["elenco"] = sorted(p.name for p in (app / ".venv").rglob("*"))
                    self._avvia_in_console_senza_interfaccia(
                        script, *opzioni, prima=self._finto_venv_in_app, dopo=dopo)
                    self.assertIn(f" {visto['venv']} -m bhs", visto["exec"])
                    self.assertEqual(visto["contenuto"], self._testo_finto_python())     # il venv non è stato toccato
                    self.assertEqual(visto["elenco"], ["bin", "python3"])

    def _finto_venv_in_app(self, app: Path) -> None:
        self._finto_venv(app)

    @unittest.skipUnless(shutil.which("sh") and shutil.which("python3") and os.name == "posix",
                         "servono ambiente POSIX e python3")
    def test_opzioni_senza_interfaccia_con_venv_senza_pyside6_usano_python3(self):
        visto = {}
        self._avvia_in_console_senza_interfaccia(
            "install.sh", "--guida", "rdr2", prima=lambda app: self._finto_venv(app, con_pyside=False),
            dopo=lambda home, app: visto.update(exec=self._riga_exec(home)))
        self.assertIn(" python3 -m bhs", visto["exec"])
        self.assertNotIn(".venv", visto["exec"])

    @unittest.skipUnless(shutil.which("sh") and shutil.which("python3") and os.name == "posix",
                         "servono ambiente POSIX e python3")
    def test_opzioni_senza_interfaccia_senza_venv_usano_python3(self):
        visto = {}
        self._avvia_in_console_senza_interfaccia(
            "install.sh", "--guida", "rdr2", dopo=lambda home, app: visto.update(exec=self._riga_exec(home)))
        self.assertIn(" python3 -m bhs", visto["exec"])
        self.assertNotIn(".venv", visto["exec"])

    @unittest.skipUnless(shutil.which("sh") and shutil.which("curl") and os.name == "posix",
                         "servono ambiente POSIX e curl")
    def test_aggiornamento_via_pipe_senza_interfaccia_tiene_il_python_del_venv(self):
        import tarfile
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            archivio = base / "src.tar.gz"
            with tarfile.open(archivio, "w:gz") as tar:
                for nome in ("bhs", "data", "install.sh", "install-onexplayer.sh", "install-rog-ally.sh"):
                    tar.add(self.RADICE / nome, arcname=f"bazzite-handheld-setup-main/{nome}",
                            filter=lambda i: None if "__pycache__" in i.name else i)
            home = base / "home"
            dest = home / ".local/share/bazzite-handheld-setup"
            self._finto_venv(dest)                  # sta nella versione vecchia e viene spostato in quella nuova
            env = {k: v for k, v in os.environ.items() if not k.startswith("XDG_")}
            env.update(HOME=str(home), DISPLAY=":9", BHS_FORCE="1", BHS_URL=archivio.as_uri())
            env.pop("BHS_SKIP_VENV", None)
            with (self.RADICE / "install.sh").open("rb") as script:
                r = subprocess.run(["sh", "-s", "--", "--elenco"], stdin=script, env=env, cwd=d,
                                   capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((dest / ".venv/bin/python3").is_file())
            self.assertIn(f" {dest}/.venv/bin/python3 -m bhs", self._riga_exec(home))

    @unittest.skipUnless(shutil.which("sh") and os.name == "posix", "serve ambiente POSIX per lo script")
    def test_live_usb_sysimage_onexplayer(self):
        with tempfile.TemporaryDirectory() as d:
            sysimg = Path(d) / "sysimage"
            (sysimg / "etc").mkdir(parents=True)
            (sysimg / "etc/os-release").write_text('ID=bazzite\nPRETTY_NAME="Bazzite"\n', encoding="utf-8")
            utente_home = sysimg / "var/home/davide"
            utente_home.mkdir(parents=True)
            env = {
                **os.environ,
                "BHS_SYSIMAGE": str(sysimg),
            }
            r = subprocess.run(["sh", str(self.RADICE / "install-onexplayer.sh")],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            norbc = utente_home / ".config/environment.d/10-gamescope-session.conf"
            self.assertTrue(norbc.is_file())
            self.assertIn("INTEL_DEBUG=norbc", norbc.read_text(encoding="utf-8").splitlines())
            app_main = utente_home / ".local/share/bazzite-handheld-setup/bhs/__main__.py"
            self.assertTrue(app_main.is_file())
            autostart = utente_home / ".config/autostart/bhs-first-run.desktop"
            self.assertTrue(autostart.is_file())
            self.assertIn("install-onexplayer.sh", autostart.read_text(encoding="utf-8"))


class TestAria2(unittest.TestCase):
    def test_nessun_commento_a_fine_riga(self):
        # In aria2 un "#" dopo il valore ne fa parte e rompe l'opzione: i commenti stanno su righe a parte.
        for fascia in tweaks.FASCE_ARIA2:
            for riga in tweaks.testo_aria2(fascia).splitlines():
                if riga.strip() and not riga.startswith("#"):
                    self.assertRegex(riga, r"^[a-z-]+=[^#\s]+$", f"{fascia}: {riga!r}")

    def test_valori_della_tabella(self):
        t = tweaks.testo_aria2("fttc")
        for atteso in ("max-connection-per-server=8", "split=8", "min-split-size=5M", "max-concurrent-downloads=3",
                       "disk-cache=32M", "max-tries=10", "retry-wait=5", "continue=true"):
            self.assertIn(atteso, t.splitlines())
        self.assertIn("max-connection-per-server=4", tweaks.testo_aria2("adsl").splitlines())
        self.assertIn("max-connection-per-server=16", tweaks.testo_aria2("ftth").splitlines())
        self.assertIn("retry-wait=10", tweaks.testo_aria2("adsl").splitlines())

    @unittest.skipUnless(shutil.which("sh"), "serve una shell POSIX")
    def test_script_scrive_e_salva_copia(self):
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, "HOME": d}
            for giro in range(2):
                r = subprocess.run(["sh", "-c", tweaks.script_aria2("fttc")], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            conf = (Path(d) / tweaks.FILE_ARIA2)
            testo = conf.read_text()
            self.assertEqual(testo.splitlines()[0], "# aria2.conf - FTTC/VDSL (30-200 Mbit)")
            self.assertNotIn("$DL", testo)
            self.assertNotIn("$ALLOC", testo)
            self.assertRegex(testo, r"(?m)^dir=.+/Downloads$")
            self.assertRegex(testo, r"(?m)^file-allocation=(falloc|none)$")
            copie = list(conf.parent.glob("aria2.conf.bak-*"))
            self.assertEqual(len(copie), 1, "al secondo giro deve esistere una copia del file precedente")
            self.assertEqual(tweaks._stato_aria2("fttc")(detect.Sistema(), home=Path(d)), "attivo")
            self.assertEqual(tweaks._stato_aria2("adsl")(detect.Sistema(), home=Path(d)), "inattivo")

    def test_voce_catalogo_brew(self):
        a = next(v for v in catalog.carica_catalogo() if v.id == "aria2")
        self.assertEqual(a.tipo, "brew")
        self.assertFalse(a.installata(set(), trova=lambda c: None, bin_brew=Path("/non/esiste")))
        self.assertTrue(a.installata(set(), trova=lambda c: "/x/aria2c" if c == "aria2c" else None))
        self.assertEqual(a.comando(detect.Sistema(brew="brew")), ["brew", "install", "aria2"])
        self.assertEqual(a.comando(detect.Sistema(brew=detect.BREW_BIN))[0], detect.BREW_BIN)
        self.assertIsNone(a.comando(detect.Sistema(brew=None)))   # senza Homebrew: istruzioni a mano


class TestMullvad(unittest.TestCase):
    OK = "\n".join(["[mullvad-stable]", "name=Mullvad VPN", "baseurl=https://repository.mullvad.net/rpm/stable/$basearch",
                    "type=rpm", "enabled=1", "gpgcheck=1",
                    "gpgkey=https://repository.mullvad.net/rpm/mullvad-keyring.asc"]) + "\n"
    BASE = dict(strumenti={"rpm-ostree": True, "pkexec": True, "curl": True, "mullvad": False})

    def sist(self, **extra):
        dati = {**self.BASE, **extra}
        dati["strumenti"] = {**self.BASE["strumenti"], **extra.get("strumenti", {})}
        return detect.Sistema(**dati)

    def test_fasi(self):
        f = tweaks._fase_mullvad
        self.assertEqual(f(self.sist()), "da_installare")
        self.assertEqual(f(self.sist(layer={"mullvad-vpn"})), "in_attesa")
        self.assertEqual(f(self.sist(strumenti={"mullvad": True})), "da_attivare")
        self.assertEqual(f(self.sist(strumenti={"mullvad": True}, mullvad_servizio=True)), "attivo")
        self.assertEqual(f(self.sist(strumenti={"rpm-ostree": False})), "non_supportato")
        self.assertEqual(f(self.sist(strumenti={"curl": False})), "non_supportato")

    def test_comandi_per_fase(self):
        t = tweaks.tutti_i_tweak()["mullvad_vpn"]
        fase1 = t.comandi_per(self.sist())
        self.assertEqual(len(fase1), 2)
        self.assertEqual(fase1[1][:3], ["pkexec", "sh", "-c"])          # un solo passaggio di password per root
        self.assertTrue(fase1[1][-1].endswith("mullvad.repo"))           # il file scaricato arriva come $1
        self.assertIn("rpm-ostree install mullvad-vpn", fase1[1][3])
        self.assertIn("ostree admin pin 0", fase1[1][3])                 # prima si blocca la versione
        self.assertLess(fase1[1][3].index("ostree admin pin 0"), fase1[1][3].index("rpm-ostree install"))
        self.assertEqual(t.comandi_per(self.sist(layer={"mullvad-vpn"})), [])          # in attesa: niente da fare
        self.assertEqual(t.comandi_per(self.sist(strumenti={"mullvad": True})),
                         [["pkexec", "systemctl", "enable", "--now", "mullvad-daemon.service"]])
        self.assertEqual(t.comandi_per(self.sist(strumenti={"mullvad": True}, mullvad_servizio=True)), [])
        self.assertEqual(t.stato(self.sist(layer={"mullvad-vpn"})), "in_attesa")

    def valida(self, contenuto: str) -> int:
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "repo").write_text(contenuto, encoding="utf-8", newline="\n")
            r = subprocess.run(["sh", "-c", "t=repo\n" + tweaks.VALIDA_REPO_MULLVAD + "echo VALIDO"],
                               cwd=d, capture_output=True, text=True)
            return 0 if "VALIDO" in r.stdout else r.returncode or 1

    @unittest.skipUnless(shutil.which("sh") and shutil.which("grep"), "servono sh e grep")
    def test_validazione_del_file_repo(self):
        self.assertEqual(self.valida(self.OK), 0)                                        # il file ufficiale passa
        self.assertNotEqual(self.valida(""), 0)                                          # vuoto
        self.assertNotEqual(self.valida(self.OK.replace("repository.mullvad.net/rpm/stable", "evil.example/rpm")), 0)
        self.assertNotEqual(self.valida(self.OK.replace("gpgcheck=1", "gpgcheck=0")), 0)
        self.assertNotEqual(self.valida(self.OK + "exclude=kernel*\n"), 0)               # riga in più
        self.assertNotEqual(self.valida(self.OK + "baseurl=http://repository.mullvad.net/x\n"), 0)   # http, non https
        self.assertNotEqual(self.valida(self.OK.replace("gpgcheck=1\n", "")), 0)         # senza controllo firma
        self.assertNotEqual(self.valida(self.OK.replace("https://repository.mullvad.net/rpm/mullvad-keyring.asc",
                                                        "https://repository.mullvad.net.evil.example/k")), 0)

    def test_script_root_sintassi(self):
        if not shutil.which("sh"):
            self.skipTest("serve una shell POSIX")
        for script in (tweaks.SCRIPT_INSTALLA_MULLVAD, tweaks.SCRIPT_SCARICA_REPO_MULLVAD):
            r = subprocess.run(["sh", "-n", "-c", script], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_rilevamento_pacchetti_aggiunti(self):
        out = ("State: idle\nDeployments:\n● ostree-image-signed:docker://ghcr.io/ublue-os/bazzite-deck-gnome:stable\n"
               "                   Digest: sha256:abc\n          LayeredPackages: mullvad-vpn foo\n"
               "                           bar\n                   Version: 44\n")
        self.assertEqual(detect.pacchetti_aggiunti(lambda argv: out), {"mullvad-vpn", "foo", "bar"})
        self.assertEqual(detect.pacchetti_aggiunti(lambda argv: None), set())
        self.assertTrue(detect.servizio_attivo("x.service", lambda argv: "enabled\n"))
        self.assertFalse(detect.servizio_attivo("x.service", lambda argv: "disabled\n"))
        self.assertFalse(detect.servizio_attivo("x.service", lambda argv: None))


class TestPiano(unittest.TestCase):
    def setUp(self):
        self.cat = catalog.carica_catalogo()
        self.tw = tweaks.tutti_i_tweak()

    def test_flathub_solo_con_flatpak(self):
        s = detect.Sistema(brew="brew")
        con = piano.costruisci_piano(self.cat, self.tw, {"heroic"}, set(), s)
        self.assertEqual(con[0].argv[:4], ["flatpak", "remote-add", "--user", "--if-not-exists"])
        self.assertEqual(con[1].argv[:3], ["flatpak", "install", "--user"])
        senza = piano.costruisci_piano(self.cat, self.tw, {"aria2"}, set(), s)
        self.assertEqual([a.argv[0] for a in senza], ["brew"])

    def test_ordine_dei_tweak(self):
        # Ordine di definizione, non casuale: il blocco della versione prima, l'aggiornamento (lungo) per ultimo.
        scelti = {"aggiorna_sistema", "intel_norbc", "blocca_versione", "aria2_conf"}
        titoli = [a.titolo for a in piano.costruisci_piano(self.cat, self.tw, set(), scelti, detect.Sistema())]
        attesi = [self.tw[i].titolo for i in ("intel_norbc", "blocca_versione", "aria2_conf", "aggiorna_sistema")]
        self.assertEqual(titoli, attesi)

    def test_manuali_senza_comando(self):
        a = piano.costruisci_piano(self.cat, self.tw, {"emudeck", "aria2"}, set(), detect.Sistema(brew=None))
        self.assertEqual([x.argv for x in a], [None, None])
        self.assertIn("brew.sh", next(x for x in a if "aria2" in x.titolo).nota)
        self.assertIn("emudeck.com", next(x for x in a if "EmuDeck" in x.titolo).nota)

    def test_riassunto_comando(self):
        self.assertEqual(runner.riassunto_comando(None), "")
        self.assertEqual(runner.riassunto_comando(["pkexec", "sh", "-c", "a\nb", "sh", "/x/y"]),
                         "pkexec sh -c ‹script› sh /x/y")

    def test_profili_elencano_le_nuove_voci(self):
        for pr in profiles.carica_profili():
            self.assertIn("aria2_conf", pr.avanzati)
            self.assertIn("mullvad_vpn", pr.avanzati)


class TestTweakKDE(unittest.TestCase):
    def test_schema_colori_file(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            cfg = home / ".config" / "kdeglobals"
            cfg.parent.mkdir(parents=True)
            cfg.write_text("[General]\nColorScheme=BreezeDark\n")
            self.assertEqual(tweaks._schema_colori_kde(detect.Sistema(), home=home), "attivo")
            cfg.write_text("[General]\nColorScheme=BreezeLight\n")
            self.assertEqual(tweaks._schema_colori_kde(detect.Sistema(), home=home), "inattivo")

    def test_tastiera_kde_file(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            cfg = home / ".config" / "kwinrc"
            cfg.parent.mkdir(parents=True)
            cfg.write_text("[Wayland]\nInputMethod=/usr/share/applications/com.github.maliit.keyboard.desktop\n")
            self.assertEqual(tweaks._tastiera_kde(detect.Sistema(), home=home), "attivo")
            cfg.write_text("[Wayland]\nInputMethod=\n")
            self.assertEqual(tweaks._tastiera_kde(detect.Sistema(), home=home), "inattivo")

    def test_scala_display_file(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            cfg = home / ".config" / "kdeglobals"
            cfg.parent.mkdir(parents=True)
            cfg.write_text("[KScreen]\nScaleFactor=1.5\n")
            f150 = tweaks._scala_display(1.5, home=home)
            f125 = tweaks._scala_display(1.25, home=home)
            self.assertEqual(f150(detect.Sistema()), "attivo")
            self.assertEqual(f125(detect.Sistema()), "inattivo")


class TestRunner(unittest.TestCase):
    def test_descrivi_comando(self):
        self.assertEqual(runner.descrivi_comando(["ls", "a b"]), ["  $ ls 'a b'"])
        r = runner.descrivi_comando(["pkexec", "sh", "-c", "set -e\necho ciao\n"])
        self.assertEqual(r[0], "  $ pkexec sh -c <<script>>")
        self.assertEqual(r[1:], ["      set -e", "      echo ciao"])

    def test_dry_run_non_esegue(self):
        righe = []
        ris = runner.esegui_azioni([runner.Azione("x", ["comando-che-non-esiste"]),
                                    runner.Azione("y", None, nota="a mano")], True, righe.append)
        self.assertEqual([r.esito for r in ris], ["simulata", "saltata"])

    def test_esecuzione_reale_e_errore(self):
        righe = []
        py = sys.executable
        ris = runner.esegui_azioni([runner.Azione("ok", [py, "-c", "print('ciao')"]),
                                    runner.Azione("ko", [py, "-c", "raise SystemExit(3)"]),
                                    runner.Azione("manca", ["comando-che-non-esiste-xyz"])],
                                   False, righe.append)
        self.assertEqual([r.esito for r in ris], ["ok", "errore", "errore"])
        self.assertTrue(any("ciao" in r for r in righe))


PROFILI_GIOCHI = ("onexplayer1s", "rogallyz1x", "generico")


def _guida(profilo: str, ident: str) -> giochi.Guida:
    g = giochi.guida_per_id(giochi.carica_guide(profilo), ident)
    assert g is not None, ident
    return g


class TestGuideDati(unittest.TestCase):
    def test_ordine_e_contenuto_per_ogni_profilo(self):
        for profilo in PROFILI_GIOCHI:
            with self.subTest(profilo=profilo):
                guide = giochi.carica_guide(profilo)
                self.assertEqual([g.id for g in guide], ["rdr2", "witcher3", "skyrim"])
                for g in guide:
                    self.assertTrue(g.obiettivo.strip(), g.id)
                    self.assertTrue(any(p.azione == "config" for p in g.passi), g.id)
                    self.assertIsNotNone(g.config, g.id)

    def test_nessun_segnaposto_rimasto(self):
        # Un segnaposto sconosciuto resta visibile come «{nome}»: qui si controlla che non ne sia rimasto nessuno.
        for profilo in PROFILI_GIOCHI:
            for g in giochi.carica_guide(profilo):
                testi = [g.obiettivo]
                for p in g.passi:
                    testi += [p.titolo, p.testo, p.copia, p.nota_app]
                    testi += [t for voce in p.voci for t in voce]
                for t in testi:
                    with self.subTest(profilo=profilo, gioco=g.id, testo=t[:40]):
                        self.assertNotIn("{", t)
                        self.assertNotIn("}", t)

    def test_dove_valido(self):
        for profilo in PROFILI_GIOCHI:
            for g in giochi.carica_guide(profilo):
                for p in g.passi:
                    self.assertTrue(p.dove == "" or p.dove in giochi.DOVE, f"{profilo}/{g.id}: {p.titolo} -> {p.dove}")

    def test_profilo_sconosciuto_usa_generico(self):
        ignoto = giochi.carica_guide("boh")
        generico = giochi.carica_guide("generico")
        self.assertEqual([g.id for g in ignoto], [g.id for g in generico])
        for a, b in zip(ignoto, generico):
            self.assertEqual(a.obiettivo, b.obiettivo)
            self.assertEqual([p.titolo for p in a.passi], [p.titolo for p in b.passi])
            self.assertEqual(a.config.valori, b.config.valori)

    def test_forma_delle_chiavi_di_configurazione(self):
        for profilo in PROFILI_GIOCHI:
            for g in giochi.carica_guide(profilo):
                for chiave in g.config.valori:
                    with self.subTest(profilo=profilo, gioco=g.id, chiave=chiave):
                        self.assertRegex(chiave, r"^[^/]+/[^/]+$")
                        sezione, chiave_pura = chiave.split("/")
                        self.assertTrue(sezione.strip() and chiave_pura.strip())

    def test_valori_xml_senza_caratteri_speciali(self):
        # Il valore viene scritto così com'è dentro il file: un «&», «<», «>» o «"» lo romperebbe.
        for profilo in PROFILI_GIOCHI:
            for g in giochi.carica_guide(profilo):
                if g.config.tipo != "xml":
                    continue
                for chiave, valore in g.config.valori.items():
                    with self.subTest(profilo=profilo, gioco=g.id, chiave=chiave):
                        self.assertFalse(set(valore) & set('&<>"'), valore)

    def test_guida_per_id(self):
        guide = giochi.carica_guide("generico")
        self.assertEqual(giochi.guida_per_id(guide, "skyrim").id, "skyrim")
        self.assertIsNone(giochi.guida_per_id(guide, "boh"))


class TestGuidePerProfilo(unittest.TestCase):
    @staticmethod
    def titoli(profilo, ident):
        return [p.titolo for p in _guida(profilo, ident).passi]

    def test_passo_risoluzione_solo_dove_serve(self):
        # L'Ally ha lo schermo 1080p e non ha bisogno di abbassare la risoluzione di gioco.
        for ident in ("rdr2", "witcher3", "skyrim"):
            def con(profilo):
                return any(t.startswith("Imposta la risoluzione di gioco") for t in self.titoli(profilo, ident))
            self.assertTrue(con("onexplayer1s"), ident)
            self.assertTrue(con("generico"), ident)
            self.assertFalse(con("rogallyz1x"), ident)

    def test_rdr2_qualita_alberi(self):
        self.assertEqual(_guida("rogallyz1x", "rdr2").config.valori["advancedGraphics/treeQuality"], "kSettingLevel_High")
        self.assertEqual(_guida("onexplayer1s", "rdr2").config.valori["advancedGraphics/treeQuality"], "kSettingLevel_Low")

    def test_generico_eredita_la_qualita_del_onexplayer(self):
        for ident in ("rdr2", "witcher3", "skyrim"):
            oxp, gen = _guida("onexplayer1s", ident).config.valori, _guida("generico", ident).config.valori
            for chiave, valore in gen.items():
                self.assertEqual(oxp[chiave], valore, f"{ident}: {chiave}")
            self.assertTrue(gen, ident)

    def test_generico_non_eredita_le_chiavi_dello_schermo(self):
        # Una risoluzione scritta per lo schermo di un altro dispositivo romperebbe il gioco: niente ripiego.
        skyrim = {p: _guida(p, "skyrim").config.valori for p in PROFILI_GIOCHI}
        self.assertEqual(skyrim["onexplayer1s"]["Display/iSize W"], "1280")
        self.assertEqual(skyrim["rogallyz1x"]["Display/iSize W"], "1920")
        self.assertNotIn("Display/iSize W", skyrim["generico"])
        self.assertNotIn("Display/iSize H", skyrim["generico"])
        witcher = {p: _guida(p, "witcher3").config.valori for p in PROFILI_GIOCHI}
        self.assertIn("Viewport/Resolution", witcher["onexplayer1s"])
        self.assertIn("Viewport/Resolution", witcher["rogallyz1x"])
        self.assertNotIn("Viewport/Resolution", witcher["generico"])


class TestValoriRdr2(unittest.TestCase):
    AMMESSO = r"kSettingLevel_(?:Low|Medium|High|Ultra)|kSettingAPI_Vulkan|true|false|\d+(?:\.\d+)?"

    def test_valori_e_sezioni(self):
        for profilo in PROFILI_GIOCHI:
            for chiave, valore in _guida(profilo, "rdr2").config.valori.items():
                with self.subTest(profilo=profilo, chiave=chiave):
                    self.assertRegex(valore, f"^(?:{self.AMMESSO})$")
                    self.assertIn(chiave.split("/")[0], ("graphics", "advancedGraphics"))


class TestModificaIni(unittest.TestCase):
    def test_cambia_conservando_resto_e_crlf(self):
        testo = "[Display]\r\niSize H=1600\r\niShadowMapResolution=4096\r\n\r\n[Grass]\r\nfGrassStartFadeDistance=7000\r\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/iShadowMapResolution": "1024"})
        self.assertEqual(nuovo, testo.replace("=4096", "=1024"))
        self.assertEqual([(e.stato, e.prima, e.dopo) for e in esiti], [("cambiata", "4096", "1024")])
        self.assertNotIn("\n", nuovo.replace("\r\n", ""))

    def test_chiave_con_spazio(self):
        nuovo, esiti = giochi.modifica_ini("[Display]\niSize W=2560\niSize H=1600\n", {"Display/iSize W": "1280"})
        self.assertEqual(nuovo, "[Display]\niSize W=1280\niSize H=1600\n")
        self.assertEqual(esiti[0].stato, "cambiata")

    def test_senza_distinzione_di_maiuscole(self):
        nuovo, esiti = giochi.modifica_ini("[display]\nISHADOWMAPRESOLUTION=4096\n", {"Display/iShadowMapResolution": "1024"})
        self.assertEqual(nuovo, "[display]\nISHADOWMAPRESOLUTION=1024\n")
        self.assertEqual(esiti[0].stato, "cambiata")

    def test_uguale_non_cambia_il_testo(self):
        testo = "[Display]\r\nbUseTAA=1\r\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/bUseTAA": "1"})
        self.assertEqual(nuovo, testo)
        self.assertEqual([e.stato for e in esiti], ["uguale"])

    def test_aggiunge_la_chiave_in_coda_alla_sezione(self):
        testo = "[Display]\nbUseTAA=0\n\n[Grass]\nfGrassStartFadeDistance=7000\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/iVSyncPresentInterval": "1"})
        self.assertEqual(nuovo, "[Display]\nbUseTAA=0\niVSyncPresentInterval=1\n\n[Grass]\nfGrassStartFadeDistance=7000\n")
        self.assertEqual([e.stato for e in esiti], ["aggiunta"])

    def test_aggiunge_la_chiave_nell_ultima_sezione(self):
        nuovo, _ = giochi.modifica_ini("[Display]\nbUseTAA=0\n", {"Display/iVSyncPresentInterval": "1"})
        self.assertEqual(nuovo, "[Display]\nbUseTAA=0\niVSyncPresentInterval=1\n")

    def test_crea_la_sezione_mancante_in_fondo(self):
        nuovo, esiti = giochi.modifica_ini("[Display]\nbUseTAA=0\n", {"Grass/fGrassStartFadeDistance": "3500"})
        self.assertEqual(nuovo, "[Display]\nbUseTAA=0\n[Grass]\nfGrassStartFadeDistance=3500\n")
        self.assertEqual(esiti[0].stato, "aggiunta")

    def test_senza_aggiungere_la_chiave_resta_assente(self):
        testo = "[Display]\nbUseTAA=0\n"
        for valori in ({"Display/iVSyncPresentInterval": "1"}, {"Grass/fGrassStartFadeDistance": "3500"}):
            nuovo, esiti = giochi.modifica_ini(testo, valori, aggiungi=False)
            self.assertEqual(nuovo, testo)
            self.assertEqual([e.stato for e in esiti], ["assente"])

    def test_riga_commentata_non_e_la_chiave(self):
        testo = "[Display]\n;bUseTAA=0\n#bUseTAA=0\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/bUseTAA": "1"}, aggiungi=False)
        self.assertEqual(nuovo, testo)
        self.assertEqual(esiti[0].stato, "assente")
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/bUseTAA": "1"})
        self.assertEqual(nuovo, "[Display]\n;bUseTAA=0\n#bUseTAA=0\nbUseTAA=1\n")
        self.assertEqual(esiti[0].stato, "aggiunta")

    def test_chiave_omonima_in_un_altra_sezione(self):
        testo = "[Altro]\nbUseTAA=0\n[Display]\nbUseTAA=0\n"
        nuovo, _ = giochi.modifica_ini(testo, {"Display/bUseTAA": "1"})
        self.assertEqual(nuovo, "[Altro]\nbUseTAA=0\n[Display]\nbUseTAA=1\n")
        nuovo, esiti = giochi.modifica_ini("[Altro]\nbUseTAA=0\n", {"Display/bUseTAA": "1"}, aggiungi=False)
        self.assertEqual(nuovo, "[Altro]\nbUseTAA=0\n")
        self.assertEqual(esiti[0].stato, "assente")

    def test_a_capo_misti_ogni_riga_tiene_il_suo(self):
        testo = "[Display]\r\niShadowMapResolution=4096\nfShadowDistance=8000\r\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/iShadowMapResolution": "1024",
                                                   "Display/fShadowDistance": "4000"})
        self.assertEqual(nuovo, "[Display]\r\niShadowMapResolution=1024\nfShadowDistance=4000\r\n")
        self.assertEqual([e.stato for e in esiti], ["cambiata", "cambiata"])

    def test_righe_nuove_usano_il_fine_riga_prevalente(self):
        testo = "[Display]\r\na=1\r\nb=2\nc=3\r\n[Grass]\r\nd=4\r\n"
        nuovo, _ = giochi.modifica_ini(testo, {"Display/x": "9", "Altro/y": "8"})
        self.assertEqual(nuovo, "[Display]\r\na=1\r\nb=2\nc=3\r\nx=9\r\n[Grass]\r\nd=4\r\n[Altro]\r\ny=8\r\n")

    def test_senza_a_capo_finale_resta_tale(self):
        nuovo, _ = giochi.modifica_ini("[Display]\nbUseTAA=0", {"Display/bUseTAA": "1"})
        self.assertEqual(nuovo, "[Display]\nbUseTAA=1")
        nuovo, _ = giochi.modifica_ini("[Display]\nbUseTAA=1", {"Display/bUseTAA": "1"})
        self.assertEqual(nuovo, "[Display]\nbUseTAA=1")

    def test_aggiunta_in_coda_a_un_file_senza_a_capo_finale(self):
        nuovo, _ = giochi.modifica_ini("[Display]\nbUseTAA=0", {"Display/iVSync": "1"})
        self.assertEqual(nuovo, "[Display]\nbUseTAA=0\niVSync=1\n")
        nuovo, _ = giochi.modifica_ini("[Display]\r\nbUseTAA=0", {"Grass/f": "1"})
        self.assertEqual(nuovo, "[Display]\r\nbUseTAA=0\r\n[Grass]\r\nf=1\r\n")

    def test_intestazione_con_commento(self):
        testo = "[General]\nx=1\n[Display] ; nota\niSize W=2560\n[Grass]   # altra\nf=1\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"Display/iSize W": "1280", "Grass/f": "2"}, aggiungi=False)
        self.assertEqual(nuovo, "[General]\nx=1\n[Display] ; nota\niSize W=1280\n[Grass]   # altra\nf=2\n")
        self.assertEqual([e.stato for e in esiti], ["cambiata", "cambiata"])
        # La sezione con commento chiude quella prima: la chiave di [General] non si confonde con [Display].
        nuovo, esiti = giochi.modifica_ini(testo, {"General/iSize W": "1"}, aggiungi=False)
        self.assertEqual(esiti[0].stato, "assente")

    def test_chiave_senza_sezione_e_un_errore_e_il_testo_non_cambia(self):
        for percorso in ("chiave", "/chiave", " /chiave"):
            with self.subTest(percorso=percorso):
                with self.assertRaisesRegex(ValueError, "^chiave senza sezione: "):
                    giochi.modifica_ini("[Display]\na=1\n", {"Display/a": "2", percorso: "1"})

    def test_aggiungere_una_sezione_non_toglie_le_righe_finali(self):
        # Righe «vuote» per str.strip() (spazi, 0xA0, 0x85 in latin-1) fanno parte del file: non si cancellano.
        for coda in ("\n\n", "   \n", "\xa0\n", "\x85\n", "  "):
            with self.subTest(coda=coda):
                testo = "[A]\nx=1\n" + coda
                nuovo, _ = giochi.modifica_ini(testo, {"B/y": "2"})
                self.assertEqual(nuovo, testo + ("" if coda.endswith("\n") else "\n") + "[B]\ny=2\n")

    def test_commento_in_linea_si_conserva(self):
        nuovo, esiti = giochi.modifica_ini("[A]\ny=0 ; nota\nz = 5\t;  due  spazi\n", {"A/y": "1", "A/z": "6"})
        self.assertEqual(nuovo, "[A]\ny=1 ; nota\nz = 6\t;  due  spazi\n")
        self.assertEqual([(e.prima, e.dopo) for e in esiti], [("0", "1"), ("5", "6")])
        testo = "[A]\ny=1   ; nota\r\n"
        nuovo, esiti = giochi.modifica_ini(testo, {"A/y": "1"})
        self.assertEqual(nuovo, testo)
        self.assertEqual([e.stato for e in esiti], ["uguale"])

    def test_punto_e_virgola_senza_spazio_prima_fa_parte_del_valore(self):
        nuovo, esiti = giochi.modifica_ini("[A]\ny=a;b\n", {"A/y": "c"})
        self.assertEqual(nuovo, "[A]\ny=c\n")
        self.assertEqual(esiti[0].prima, "a;b")

    def test_caratteri_che_non_sono_a_capo_non_dividono_le_righe(self):
        # In una codifica a un byte per carattere 0x85 diventa U+0085, che str.splitlines() tratterebbe da a capo.
        testo = "[Display]\nnota=a\x85b\nbUseTAA=0\n"
        nuovo, _ = giochi.modifica_ini(testo, {"Display/nota": "x"})
        self.assertEqual(nuovo, "[Display]\nnota=x\nbUseTAA=0\n")


class TestModificaXml(unittest.TestCase):
    XML = ('<?xml version="1.0" encoding="UTF-8"?>\n<settings>\n'
           '  <graphics>\n    <textureQuality>kSettingLevel_High</textureQuality>\n    <msaa value="2" />\n  </graphics>\n'
           '  <advancedGraphics>\n    <textureQuality>kSettingLevel_Low</textureQuality>\n'
           '    <locked value="true"/>\n  </advancedGraphics>\n</settings>\n')

    def test_cambia_testo_e_attributo(self):
        nuovo, esiti = giochi.modifica_xml(self.XML, {"graphics/textureQuality": "kSettingLevel_Ultra", "graphics/msaa": "0"})
        self.assertEqual([e.stato for e in esiti], ["cambiata", "cambiata"])
        self.assertEqual(nuovo, self.XML.replace("kSettingLevel_High", "kSettingLevel_Ultra").replace('"2"', '"0"'))

    def test_chiave_omonima_in_un_altra_sezione_non_si_tocca(self):
        nuovo, _ = giochi.modifica_xml(self.XML, {"advancedGraphics/textureQuality": "kSettingLevel_Medium"})
        self.assertEqual(nuovo, self.XML.replace("kSettingLevel_Low", "kSettingLevel_Medium"))
        self.assertIn("kSettingLevel_High", nuovo)

    def test_attributo_con_barra_attaccata(self):
        nuovo, esiti = giochi.modifica_xml(self.XML, {"advancedGraphics/locked": "false"})
        self.assertIn('<locked value="false"/>', nuovo)
        self.assertEqual(esiti[0].stato, "cambiata")

    def test_uguale(self):
        nuovo, esiti = giochi.modifica_xml(self.XML, {"graphics/msaa": "2"})
        self.assertEqual(nuovo, self.XML)
        self.assertEqual(esiti[0].stato, "uguale")

    def test_mancante_non_aggiunge_nulla(self):
        nuovo, esiti = giochi.modifica_xml(self.XML, {"graphics/ssao": "kSettingLevel_Low", "audio/volume": "1"})
        self.assertEqual(nuovo, self.XML)
        self.assertEqual([e.stato for e in esiti], ["assente", "assente"])


class TestApplicaERipristina(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def cfg(self, **valori):
        return giochi.ConfigGioco(tipo="ini", cartelle=[], file=["impostazioni.ini"], valori=valori)

    def file(self, contenuto: bytes) -> Path:
        f = self.dir / "impostazioni.ini"
        f.write_bytes(contenuto)
        return f

    def test_copia_alla_prima_modifica_e_mai_sovrascritta(self):
        originale = b"[Display]\r\niSize W=2560\r\n"
        f = self.file(originale)
        copia = f.with_name("impostazioni.ini" + giochi.SUFFISSO_COPIA)
        self.assertFalse(copia.exists())
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertTrue(r.scritto)
        self.assertEqual(copia.read_bytes(), originale)
        self.assertEqual(f.read_bytes(), b"[Display]\r\niSize W=1280\r\n")
        giochi.applica_config(self.cfg(**{"Display/iSize W": "999"}), [f])
        self.assertEqual(f.read_bytes(), b"[Display]\r\niSize W=999\r\n")
        self.assertEqual(copia.read_bytes(), originale)       # la copia resta lo stato di partenza

    def test_nessuna_modifica_nessuna_copia(self):
        f = self.file(b"[Display]\niSize W=1280\n")
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertFalse(r.scritto)
        self.assertEqual(r.conta("uguale"), 1)
        self.assertFalse(f.with_name(f.name + giochi.SUFFISSO_COPIA).exists())

    def test_simulazione_non_scrive_niente(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f], simulazione=True)[0]
        self.assertFalse(r.scritto)
        self.assertEqual(r.esiti[0].stato, "cambiata")        # il rapporto dice che cosa cambierebbe
        self.assertEqual(f.read_bytes(), originale)
        self.assertFalse(f.with_name(f.name + giochi.SUFFISSO_COPIA).exists())
        self.assertIn("simulazione", giochi.testo_rapporti([r], simulazione=True))

    def test_ripristina_byte_per_byte(self):
        originale = b"[Display]\r\niSize W=2560\r\n; \xc3\xa8 commento\r\n"
        f = self.file(originale)
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        self.assertNotEqual(f.read_bytes(), originale)
        r = giochi.ripristina_config([f])[0]
        self.assertTrue(r.scritto)
        self.assertIsNone(r.errore)
        self.assertEqual(f.read_bytes(), originale)
        self.assertFalse(f.with_name(f.name + giochi.SUFFISSO_COPIA).exists())
        # Tolta la copia, una nuova modifica ne crea un'altra.
        giochi.applica_config(self.cfg(**{"Display/iSize W": "800"}), [f])
        self.assertEqual(f.with_name(f.name + giochi.SUFFISSO_COPIA).read_bytes(), originale)

    def test_ripristina_senza_copia_non_e_un_errore(self):
        f = self.file(b"[Display]\n")
        r = giochi.ripristina_config([f])[0]
        self.assertIsNone(r.errore)
        self.assertTrue(r.senza_copia)
        self.assertFalse(r.scritto)
        self.assertEqual(f.read_bytes(), b"[Display]\n")
        testo = giochi.testo_rapporti([r])
        self.assertNotIn("✗", testo)
        self.assertIn("Nessuna copia salvata: non c'era niente da ripristinare", testo)

    def test_ripristina_in_parte_senza_copia(self):
        a, b = self.dir / "a.ini", self.dir / "b.ini"
        a.write_bytes(b"[Display]\niSize W=2560\n")
        b.write_bytes(b"[Display]\niSize W=1280\n")
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [a, b])
        ra, rb = giochi.ripristina_config([a, b])
        self.assertTrue(ra.scritto and not ra.senza_copia and ra.errore is None)
        self.assertTrue(rb.senza_copia and rb.errore is None)
        self.assertEqual(a.read_bytes(), b"[Display]\niSize W=2560\n")
        testo = giochi.testo_rapporti([ra, rb])
        self.assertIn("ripristinato", testo)
        self.assertNotIn("Nessuna copia salvata", testo)       # il riepilogo c'è solo se nessun file aveva la copia

    def test_ripristina_in_simulazione_non_tocca_niente(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
        modificato = f.read_bytes()
        r = giochi.ripristina_config([f], simulazione=True)[0]
        self.assertFalse(r.scritto)
        self.assertIsNone(r.errore)
        self.assertEqual(f.read_bytes(), modificato)
        self.assertEqual(copia.read_bytes(), originale)
        self.assertIn("simulazione", giochi.testo_rapporti([r], simulazione=True))
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), sorted([f.name, copia.name]))

    def test_copia_interrotta_non_lascia_una_copia_col_nome_definitivo(self):
        originale = b"[Display]\r\niSize W=2560\r\n"
        f = self.file(originale)
        copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
        with mock.patch.object(giochi.os, "fsync", side_effect=OSError("disco pieno")):
            r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertIn("disco pieno", r.errore)
        self.assertFalse(r.scritto)
        self.assertFalse(copia.exists())
        self.assertEqual(f.read_bytes(), originale)
        self.assertEqual([p.name for p in self.dir.iterdir()], [f.name])      # nessun temporaneo rimasto

    def test_scrittura_del_file_interrotta_lascia_file_e_copia_interi(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
        # Il primo fsync è quello della copia, il secondo quello del file del gioco.
        with mock.patch.object(giochi.os, "fsync", side_effect=[None, OSError("disco pieno")]):
            r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertIn("disco pieno", r.errore)
        self.assertFalse(r.scritto)
        self.assertEqual(f.read_bytes(), originale)
        self.assertEqual(copia.read_bytes(), originale)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), sorted([f.name, copia.name]))

    def test_ripristino_interrotto_non_cancella_la_copia(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
        modificato = f.read_bytes()
        with mock.patch.object(giochi.os, "replace", side_effect=OSError("bloccato")):
            r = giochi.ripristina_config([f])[0]
        self.assertIn("bloccato", r.errore)
        self.assertEqual(f.read_bytes(), modificato)
        self.assertEqual(copia.read_bytes(), originale)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), sorted([f.name, copia.name]))

    def test_scrivi_atomico_sostituisce_e_non_lascia_temporanei(self):
        f = self.file(b"vecchio")
        giochi._scrivi_atomico(f, b"nuovo")
        self.assertEqual(f.read_bytes(), b"nuovo")
        self.assertEqual([p.name for p in self.dir.iterdir()], [f.name])

    @unittest.skipUnless(hasattr(os, "symlink"), "servono i collegamenti simbolici")
    def test_scrivi_atomico_scrive_il_file_vero_non_il_collegamento(self):
        vero = self.dir / "vero"
        vero.mkdir()
        f = vero / "impostazioni.ini"
        f.write_bytes(b"vecchio")
        collegamento = self.dir / "collegamento.ini"
        try:
            collegamento.symlink_to(f)
        except (OSError, NotImplementedError):
            self.skipTest("collegamenti simbolici non permessi")
        giochi._scrivi_atomico(collegamento, b"nuovo")
        self.assertTrue(collegamento.is_symlink())
        self.assertEqual(f.read_bytes(), b"nuovo")
        self.assertEqual(sorted(p.name for p in vero.iterdir()), ["impostazioni.ini"])

    def test_utf16_big_endian_con_bom_resta_big_endian(self):
        f = self.file(b"\xfe\xff" + "[Display]\r\niSize W=2560\r\n".encode("utf-16-be"))
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        self.assertEqual(f.read_bytes(), b"\xfe\xff" + "[Display]\r\niSize W=1280\r\n".encode("utf-16-be"))

    def test_utf16_little_endian_con_bom_resta_little_endian(self):
        f = self.file(b"\xff\xfe" + "[Display]\r\niSize W=2560\r\n".encode("utf-16-le"))
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        self.assertEqual(f.read_bytes(), b"\xff\xfe" + "[Display]\r\niSize W=1280\r\n".encode("utf-16-le"))

    def test_byte_non_utf8_tornano_identici_fuori_dalla_chiave(self):
        # 0x81 e 0x8D non esistono in cp1252: con un ripiego «replace» diventerebbero «?» o U+FFFD.
        originale = b"; \x81\x8d \xe0 \x85\n[Display]\niSize W=2560\nnota=\x81\x8d\n"
        f = self.file(originale)
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertIsNone(r.errore)
        self.assertEqual(f.read_bytes(), originale.replace(b"=2560", b"=1280"))
        giochi.ripristina_config([f])
        self.assertEqual(f.read_bytes(), originale)

    def test_byte_nulli_senza_bom_sono_rifiutati(self):
        originale = b"[Display]\x00\niSize W=2560\n"
        f = self.file(originale)
        copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertEqual(r.errore, "codifica non riconosciuta: file non modificato")
        self.assertFalse(r.scritto)
        self.assertEqual(f.read_bytes(), originale)
        self.assertFalse(copia.exists())
        self.assertEqual([p.name for p in self.dir.iterdir()], [f.name])

    def test_errori_di_codifica_vanno_nel_rapporto(self):
        # UTF-16 con BOM ma di lunghezza dispari: non si decodifica.
        originale = b"\xff\xfe[\x00D"
        f = self.file(originale)
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertTrue(r.errore)
        self.assertFalse(r.scritto)
        self.assertEqual(f.read_bytes(), originale)
        self.assertFalse(f.with_name(f.name + giochi.SUFFISSO_COPIA).exists())

    def _sola_lettura(self, f: Path) -> None:
        os.chmod(f, stat.S_IREAD)
        self.addCleanup(os.chmod, f, stat.S_IWRITE | stat.S_IREAD)
        if os.access(f, os.W_OK):
            self.skipTest("qui il bit di sola lettura non vale (utente root)")

    def test_file_di_sola_lettura_non_si_modifica(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        self._sola_lettura(f)
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])[0]
        self.assertEqual(r.errore, "file di sola lettura: non modificato")
        self.assertFalse(r.scritto)
        self.assertEqual(f.read_bytes(), originale)
        self.assertEqual([p.name for p in self.dir.iterdir()], [f.name])      # né copia né temporanei
        self.assertIn("file di sola lettura", giochi.testo_rapporti([r]))

    def test_ripristino_di_un_file_di_sola_lettura(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
        modificato = f.read_bytes()
        self._sola_lettura(f)
        r = giochi.ripristina_config([f])[0]
        self.assertEqual(r.errore, "file di sola lettura: non modificato")
        self.assertEqual(f.read_bytes(), modificato)
        self.assertEqual(copia.read_bytes(), originale)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), sorted([f.name, copia.name]))

    def test_scrittura_fallita_su_file_di_sola_lettura_non_lascia_temporanei(self):
        f = self.file(b"vecchio")
        self._sola_lettura(f)       # il temporaneo eredita il bit con copymode: va reso scrivibile prima di toglierlo
        with mock.patch.object(giochi.os, "replace", side_effect=OSError("bloccato")):
            with self.assertRaises(OSError):
                giochi._scrivi_atomico(f, b"nuovo")
        self.assertEqual([p.name for p in self.dir.iterdir()], [f.name])
        self.assertEqual(f.read_bytes(), b"vecchio")

    def test_chiave_senza_sezione_va_nel_rapporto(self):
        originale = b"[Display]\niSize W=2560\n"
        f = self.file(originale)
        r = giochi.applica_config(self.cfg(**{"Display/iSize W": "1280", "senzasezione": "1"}), [f])[0]
        self.assertIn("chiave senza sezione", r.errore)
        self.assertEqual(f.read_bytes(), originale)
        self.assertEqual([p.name for p in self.dir.iterdir()], [f.name])

    def test_file_ammesso(self):
        cfg = giochi.ConfigGioco(tipo="ini", cartelle=[], file=["SkyrimPrefs.ini", "Altro.ini"], valori={})
        self.assertTrue(giochi.file_ammesso(cfg, Path("/x/y/SkyrimPrefs.ini")))
        self.assertTrue(giochi.file_ammesso(cfg, "/x/y/skyrimprefs.INI"))
        self.assertTrue(giochi.file_ammesso(cfg, Path("altro.ini")))
        self.assertFalse(giochi.file_ammesso(cfg, Path("/x/y/Skyrim.ini")))
        self.assertFalse(giochi.file_ammesso(cfg, Path("/x/SkyrimPrefs.ini/passwd")))
        self.assertFalse(giochi.file_ammesso(cfg, Path("/x/y/SkyrimPrefs.ini.bak")))

    def test_witcher3_un_file_modificato_e_uno_no(self):
        cfg = _guida("onexplayer1s", "witcher3").config
        nome = cfg.file[0]
        (self.dir / "uno").mkdir()
        (self.dir / "due").mkdir()
        da_cambiare, a_posto = self.dir / "uno" / nome, self.dir / "due" / nome
        da_cambiare.write_bytes(TestConfigurazioneReale.WITCHER.encode())
        a_posto.write_bytes(TestConfigurazioneReale.WITCHER.encode())
        giochi.applica_config(cfg, [a_posto])                         # già alle impostazioni consigliate...
        a_posto.with_name(nome + giochi.SUFFISSO_COPIA).unlink()      # ...e senza copia, come un file mai toccato da noi
        a_posto_prima = a_posto.read_bytes()
        originale = da_cambiare.read_bytes()
        applicati = giochi.applica_config(cfg, [da_cambiare, a_posto])
        self.assertEqual([r.scritto for r in applicati], [True, False])
        self.assertTrue(all(r.errore is None for r in applicati))
        ripristinati = giochi.ripristina_config([da_cambiare, a_posto])
        self.assertTrue(all(r.errore is None for r in ripristinati), [r.errore for r in ripristinati])
        self.assertEqual([r.scritto for r in ripristinati], [True, False])
        self.assertEqual(da_cambiare.read_bytes(), originale)
        self.assertEqual(a_posto.read_bytes(), a_posto_prima)

    def test_utf16_con_bom_resta_utf16(self):
        f = self.file("[Display]\r\niSize W=2560\r\n".encode("utf-16"))
        self.assertTrue(f.read_bytes().startswith((b"\xff\xfe", b"\xfe\xff")))
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        dati = f.read_bytes()
        self.assertTrue(dati.startswith((b"\xff\xfe", b"\xfe\xff")))
        self.assertEqual(dati.decode("utf-16"), "[Display]\r\niSize W=1280\r\n")

    def test_cp1252_resta_cp1252(self):
        # Una «à» in cp1252 non è UTF-8 valido: se il file venisse riscritto in UTF-8 il gioco leggerebbe un carattere sbagliato.
        f = self.file("; Qualità\n[Display]\niSize W=2560\n".encode("cp1252"))
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        dati = f.read_bytes()
        self.assertIn(b"Qualit\xe0", dati)
        self.assertEqual(dati.decode("cp1252"), "; Qualità\n[Display]\niSize W=1280\n")

    def test_utf8_con_bom_resta_con_bom(self):
        f = self.file(b"\xef\xbb\xbf[Display]\niSize W=2560\n")
        giochi.applica_config(self.cfg(**{"Display/iSize W": "1280"}), [f])
        self.assertEqual(f.read_bytes(), b"\xef\xbb\xbf[Display]\niSize W=1280\n")

    def test_xml_nel_file(self):
        cfg = giochi.ConfigGioco(tipo="xml", cartelle=[], file=["system.xml"], valori={"graphics/msaa": "0"})
        f = self.dir / "system.xml"
        f.write_bytes(b'<s>\n<graphics>\n<msaa value="2" />\n</graphics>\n</s>\n')
        giochi.applica_config(cfg, [f])
        self.assertEqual(f.read_bytes(), b'<s>\n<graphics>\n<msaa value="0" />\n</graphics>\n</s>\n')


class TestTrovaFile(unittest.TestCase):
    PREFISSO = "steamapps/compatdata/{}/pfx/drive_c/users/steamuser"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.steam = self.home / ".local/share/Steam"
        (self.steam / "steamapps").mkdir(parents=True)
        self.cfg = _guida("onexplayer1s", "skyrim").config

    def metti(self, radice: Path, appid: str, testo: str = "[Display]\n", cartella="Documents/My Games/Skyrim Special Edition"):
        f = radice / self.PREFISSO.format(appid) / cartella / "SkyrimPrefs.ini"
        f.parent.mkdir(parents=True)
        f.write_text(testo)
        return f

    def test_vuota_se_non_c_e_niente(self):
        self.assertEqual(giochi.trova_file(self.cfg, self.home), [])
        self.assertEqual(giochi.trova_file(self.cfg, self.home / "non-esiste"), [])

    def test_trova_nel_prefisso_proton(self):
        f = self.metti(self.steam, "489830")
        self.assertEqual(giochi.trova_file(self.cfg, self.home), [f])

    def test_trova_anche_la_cartella_gog_e_my_documents(self):
        a = self.metti(self.steam, "1", cartella="Documents/My Games/Skyrim Special Edition GOG")
        b = self.metti(self.steam, "2", cartella="My Documents/My Games/Skyrim Special Edition")
        self.assertEqual({p.resolve() for p in giochi.trova_file(self.cfg, self.home)}, {a.resolve(), b.resolve()})

    def test_seconda_libreria_dal_vdf(self):
        seconda = Path(self._tmp.name) / "sd"
        (seconda / "steamapps").mkdir(parents=True)
        f1 = self.metti(self.steam, "1")
        f2 = self.metti(seconda, "2")
        vdf = f'"libraryfolders"\n{{\n\t"0"\n\t{{\n\t\t"path"\t\t"{seconda.as_posix()}"\n\t}}\n}}\n'
        (self.steam / "steamapps/libraryfolders.vdf").write_text(vdf)
        self.assertEqual({p.resolve() for p in giochi.trova_file(self.cfg, self.home)}, {f1.resolve(), f2.resolve()})

    def test_piu_recente_per_primo(self):
        vecchio = self.metti(self.steam, "1")
        nuovo = self.metti(self.steam, "2")
        os.utime(vecchio, (1_600_000_000, 1_600_000_000))
        os.utime(nuovo, (1_700_000_000, 1_700_000_000))
        self.assertEqual([p.resolve() for p in giochi.trova_file(self.cfg, self.home)], [nuovo.resolve(), vecchio.resolve()])
        os.utime(vecchio, (1_800_000_000, 1_800_000_000))
        self.assertEqual([p.resolve() for p in giochi.trova_file(self.cfg, self.home)], [vecchio.resolve(), nuovo.resolve()])

    def test_nessun_doppione(self):
        # La libreria principale è elencata anche nel suo stesso libraryfolders.vdf, come fa Steam.
        f = self.metti(self.steam, "1")
        vdf = f'"libraryfolders"\n{{\n"0"\n{{\n"path"  "{self.steam.as_posix()}"\n}}\n}}\n'
        (self.steam / "steamapps/libraryfolders.vdf").write_text(vdf)
        self.assertEqual(giochi.trova_file(self.cfg, self.home), [f])
        self.assertEqual(len(giochi.radici_steam(self.home)), 1)

    def test_alias_della_stessa_cartella(self):
        f = self.metti(self.steam, "1")
        try:
            (self.home / ".steam").mkdir()
            (self.home / ".steam/steam").symlink_to(self.steam, target_is_directory=True)
        except OSError:
            self.skipTest("collegamenti simbolici non permessi su questo sistema")
        self.assertEqual(giochi.trova_file(self.cfg, self.home), [f])


class TestConfigurazioneReale(unittest.TestCase):
    """Le configurazioni vere di ogni gioco, applicate a un file d'esempio realistico."""

    def applica(self, profilo, ident, contenuto: bytes, nome: str):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / nome
            f.write_bytes(contenuto)
            r = giochi.applica_config(_guida(profilo, ident).config, [f])[0]
            self.assertIsNone(r.errore)
            return f.read_bytes().decode("utf-8"), r      # byte, non read_text: così gli a capo CRLF restano visibili

    SKYRIM = ("[General]\r\nsLanguage=ITALIAN\r\n[Display]\r\niSize H=1600\r\niSize W=2560\r\nbFull Screen=0\r\n"
              "iShadowMapResolution=4096\r\nfShadowDistance=8000.0000\r\nbUseTAA=0\r\n[Grass]\r\nfGrassStartFadeDistance=7000.0000\r\n")
    RDR2 = ('<?xml version="1.0" encoding="UTF-8"?>\n<rage__fwuiSystemSettingsCollection>\n  <graphics>\n'
            '    <textureQuality>kSettingLevel_High</textureQuality>\n    <msaa value="2" />\n  </graphics>\n  <advancedGraphics>\n'
            '    <API>kSettingAPI_DX12</API>\n    <locked value="true" />\n    <treeQuality>kSettingLevel_Ultra</treeQuality>\n'
            '  </advancedGraphics>\n</rage__fwuiSystemSettingsCollection>\n')
    WITCHER = '[Viewport]\nVSync=true\nResolution="2560x1600"\n[PostProcess]\nAllowMotionBlur=true\n[Rendering]\nHairWorksLevel=2\n'

    def test_skyrim_onexplayer(self):
        testo, r = self.applica("onexplayer1s", "skyrim", self.SKYRIM.encode(), "SkyrimPrefs.ini")
        for riga in ("iSize W=1280", "iSize H=800", "iShadowMapResolution=1024", "bFull Screen=1", "bUseTAA=1",
                     "fGrassStartFadeDistance=3500.0000"):
            self.assertIn(riga, testo)
        self.assertIn("sLanguage=ITALIAN", testo)                 # il resto non si tocca
        self.assertNotIn("\n", testo.replace("\r\n", ""))         # a capo CRLF intatti
        self.assertTrue(r.scritto)

    def test_skyrim_ally(self):
        testo, _ = self.applica("rogallyz1x", "skyrim", self.SKYRIM.encode(), "SkyrimPrefs.ini")
        for riga in ("iSize W=1920", "iSize H=1080", "iShadowMapResolution=2048", "bVolumetricLightingEnable=1"):
            self.assertIn(riga, testo)

    def test_skyrim_generico_lascia_la_risoluzione(self):
        testo, _ = self.applica("generico", "skyrim", self.SKYRIM.encode(), "SkyrimPrefs.ini")
        self.assertIn("iSize W=2560", testo)
        self.assertIn("iSize H=1600", testo)
        self.assertIn("iShadowMapResolution=1024", testo)

    def test_rdr2_ally(self):
        testo, r = self.applica("rogallyz1x", "rdr2", self.RDR2.encode(), "system.xml")
        self.assertIn("<API>kSettingAPI_Vulkan</API>", testo)
        self.assertIn('<locked value="false" />', testo)
        self.assertIn("<treeQuality>kSettingLevel_High</treeQuality>", testo)
        self.assertIn('<msaa value="0" />', testo)
        self.assertGreater(r.conta("assente"), 0)                 # le voci che il file non ha non vengono inventate
        self.assertEqual(testo.count("<"), self.RDR2.count("<"))

    def test_rdr2_onexplayer(self):
        testo, _ = self.applica("onexplayer1s", "rdr2", self.RDR2.encode(), "system.xml")
        self.assertIn("<treeQuality>kSettingLevel_Low</treeQuality>", testo)
        self.assertIn("<textureQuality>kSettingLevel_Ultra</textureQuality>", testo)

    def test_witcher_onexplayer(self):
        testo, r = self.applica("onexplayer1s", "witcher3", self.WITCHER.encode(), "user.settings")
        self.assertIn("HairWorksLevel=0", testo)
        self.assertIn('Resolution="1280x800"', testo)
        self.assertIn("AllowMotionBlur=false", testo)
        self.assertIn("VSync=false", testo)
        self.assertEqual(r.conta("assente"), 0)

    def test_witcher_non_aggiunge_chiavi(self):
        # Il gioco scarta i file che non hanno la sua struttura: una chiave mancante si segnala, non si inventa.
        testo, r = self.applica("generico", "witcher3", b"[Rendering]\nHairWorksLevel=2\n", "user.settings")
        self.assertEqual(testo, "[Rendering]\nHairWorksLevel=0\n")
        self.assertEqual(r.conta("assente"), 2)


class TestTestoGuide(unittest.TestCase):
    def test_html_elenchi_grassetto_codice(self):
        h = giochi.testo_html("Prima **riga** con `codice`.\n\n1. uno\n2. due\n\n- a\n- b\n\nFine")
        self.assertIn("<ol>", h)
        self.assertIn("<li>uno</li>", h)
        self.assertIn("<ul>", h)
        self.assertIn("<li>b</li>", h)
        self.assertIn("<b>riga</b>", h)
        self.assertIn("<code>codice</code>", h)
        self.assertEqual(h.count("<ol>"), h.count("</ol>"))
        self.assertEqual(h.count("<ul>"), h.count("</ul>"))
        self.assertTrue(h.endswith("<p>Fine</p>"))

    def test_html_elenco_senza_riga_vuota_in_mezzo(self):
        h = giochi.testo_html("1. uno\n- puntato")
        self.assertLess(h.index("</ol>"), h.index("<ul>"))

    def test_html_escape(self):
        h = giochi.testo_html("a < b & c > d")
        self.assertIn("a &lt; b &amp; c &gt; d", h)
        self.assertIn("&lt;script&gt;", giochi.testo_html("- <script>"))

    def test_testo_semplice(self):
        self.assertEqual(giochi.testo_semplice("**Dolphin** e `~/Giochi`"), "Dolphin e ~/Giochi")

    def test_testo_guida(self):
        g = _guida("onexplayer1s", "skyrim")
        t = giochi.testo_guida(g)
        self.assertIn(g.nome, t)
        self.assertIn(f"Passo 1 di {len(g.passi)}", t)
        self.assertIn(f"Passo {len(g.passi)} di {len(g.passi)}", t)
        self.assertIn("--imposta-gioco skyrim", t)
        self.assertIn("--ripristina-gioco skyrim", t)
        self.assertNotIn("**", t)
        self.assertNotIn("`", t)


class TestProgressiGuide(unittest.TestCase):
    def test_salva_e_rileggi(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "sotto/guide.json"
            giochi.salva_progresso("rdr2", 4, f)
            giochi.salva_progresso("skyrim", 2, f)
            giochi.salva_progresso("rdr2", 5, f)
            self.assertEqual(giochi.leggi_progressi(f), {"rdr2": 5, "skyrim": 2})

    def test_file_assente_o_rotto(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "guide.json"
            self.assertEqual(giochi.leggi_progressi(f), {})
            f.write_text("{non è json", encoding="utf-8")
            self.assertEqual(giochi.leggi_progressi(f), {})
            f.write_text("[1, 2]", encoding="utf-8")
            self.assertEqual(giochi.leggi_progressi(f), {})
            f.write_text('{"rdr2": "tre", "skyrim": 2}', encoding="utf-8")
            self.assertEqual(giochi.leggi_progressi(f), {"skyrim": 2})
            f.write_text("{non è json", encoding="utf-8")
            giochi.salva_progresso("witcher3", 1, f)          # un file rotto non impedisce di salvare di nuovo
            self.assertEqual(giochi.leggi_progressi(f), {"witcher3": 1})

    def test_cartella_non_scrivibile_non_solleva(self):
        with tempfile.TemporaryDirectory() as d:
            ostacolo = Path(d) / "file"
            ostacolo.write_text("x")
            giochi.salva_progresso("rdr2", 1, ostacolo / "guide.json")      # la «cartella» è un file


class TestGuideDaConsole(unittest.TestCase):
    def esegui(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codice = punto_ingresso.main(list(argv))
        return codice, out.getvalue(), err.getvalue()

    def test_guida(self):
        codice, out, _ = self.esegui("--guida", "rdr2", "--profilo", "onexplayer1s")
        self.assertEqual(codice, 0)
        self.assertIn("Red Dead Redemption 2", out)
        self.assertIn("Passo 1 di", out)

    def test_guida_sconosciuta(self):
        codice, out, err = self.esegui("--guida", "boh", "--profilo", "generico")
        self.assertEqual(codice, 2)
        self.assertEqual(out, "")
        self.assertIn("rdr2", err)

    def test_profilo_sconosciuto(self):
        self.assertEqual(self.esegui("--guida", "rdr2", "--profilo", "boh")[0], 2)

    def test_imposta_senza_file_trovati(self):
        with mock.patch.object(punto_ingresso, "trova_file", lambda cfg, *a: []):
            codice, _, err = self.esegui("--imposta-gioco", "skyrim", "--profilo", "onexplayer1s")
            self.assertEqual(codice, 1)
            self.assertIn("SkyrimPrefs.ini", err)
            self.assertEqual(self.esegui("--ripristina-gioco", "skyrim", "--profilo", "onexplayer1s")[0], 1)

    def test_imposta_e_ripristina(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "SkyrimPrefs.ini"
            originale = b"[Display]\r\niShadowMapResolution=4096\r\n"
            f.write_bytes(originale)
            with mock.patch.object(punto_ingresso, "trova_file", lambda cfg, *a: [f]):
                codice, out, _ = self.esegui("--imposta-gioco", "skyrim", "--profilo", "onexplayer1s", "--dry-run")
                self.assertEqual(codice, 0)
                self.assertIn("1024", out)
                self.assertEqual(f.read_bytes(), originale)           # con --dry-run il file non cambia
                codice, out, _ = self.esegui("--imposta-gioco", "skyrim", "--profilo", "onexplayer1s")
                self.assertEqual(codice, 0)
                self.assertIn(b"iShadowMapResolution=1024", f.read_bytes())
                self.assertIn("salvato", out)
                codice, out, _ = self.esegui("--ripristina-gioco", "skyrim", "--profilo", "onexplayer1s")
                self.assertEqual(codice, 0)
                self.assertEqual(f.read_bytes(), originale)

    def test_ripristina_senza_copia_non_e_un_errore(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "SkyrimPrefs.ini"
            f.write_bytes(b"[Display]\n")
            with mock.patch.object(punto_ingresso, "trova_file", lambda cfg, *a: [f]):
                codice, out, err = self.esegui("--ripristina-gioco", "skyrim", "--profilo", "generico")
            self.assertEqual(codice, 0)
            self.assertIn("Nessuna copia salvata: non c'era niente da ripristinare", out)
            self.assertEqual(err, "")
            self.assertEqual(f.read_bytes(), b"[Display]\n")

    def test_ripristina_con_dry_run_non_ripristina(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "SkyrimPrefs.ini"
            originale = b"[Display]\r\niShadowMapResolution=4096\r\n"
            f.write_bytes(originale)
            copia = f.with_name(f.name + giochi.SUFFISSO_COPIA)
            with mock.patch.object(punto_ingresso, "trova_file", lambda cfg, *a: [f]):
                self.esegui("--imposta-gioco", "skyrim", "--profilo", "onexplayer1s")
                modificato = f.read_bytes()
                self.assertNotEqual(modificato, originale)
                codice, out, _ = self.esegui("--ripristina-gioco", "skyrim", "--profilo", "onexplayer1s", "--dry-run")
                self.assertEqual(codice, 0)
                self.assertIn("simulazione", out)
                self.assertEqual(f.read_bytes(), modificato)
                self.assertEqual(copia.read_bytes(), originale)
                codice, _, _ = self.esegui("--ripristina-gioco", "skyrim", "--profilo", "onexplayer1s")
                self.assertEqual(codice, 0)
                self.assertEqual(f.read_bytes(), originale)
                self.assertFalse(copia.exists())

    def test_errore_di_scrittura_da_uscita_1(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "SkyrimPrefs.ini"
            f.write_bytes(b"[Display]\niShadowMapResolution=4096\n")
            with mock.patch.object(punto_ingresso, "trova_file", lambda cfg, *a: [f]), \
                    mock.patch.object(giochi.os, "replace", side_effect=OSError("sola lettura")):
                codice, out, _ = self.esegui("--imposta-gioco", "skyrim", "--profilo", "onexplayer1s")
            self.assertEqual(codice, 1)
            self.assertIn("sola lettura", out)


if __name__ == "__main__":
    unittest.main()
