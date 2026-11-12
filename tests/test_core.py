"""Test della logica (senza GTK). Eseguire da `bazzite-handheld-setup`: python -I -m unittest discover -s tests"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bhs import __main__ as punto_ingresso  # noqa: E402
from bhs import catalog, cli, detect, piano, profiles, runner, tweaks  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
