"""Test di fumo della GUI con PySide6: apre la finestra, naviga in simulazione, salva uno screenshot per pagina.

Uso: python3 tools/fumo_gui.py <ally|oxp|generico> <larghezza> <altezza> <cartella_output> [auto|ID_PROFILO]
Usa un sistema finto e la simulazione: non modifica nulla.
"""
import os
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bhs import detect, giochi, gui

quale = sys.argv[1] if len(sys.argv) > 1 else "ally"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 720
H = int(sys.argv[3]) if len(sys.argv) > 3 else 960
OUT = sys.argv[4] if len(sys.argv) > 4 else "shots"
FISSO = sys.argv[5] if len(sys.argv) > 5 else None

if FISSO == "auto":
    FISSO = {"ally": "rogallyz1x", "oxp": "onexplayer1s"}.get(quale)
ETICHETTA = f"{quale}_fisso-{FISSO}" if FISSO else quale
os.makedirs(OUT, exist_ok=True)

BAT = "/sys/class/power_supply/BAT0/charge_control_end_threshold"
DMI = {
    "ally": {"fornitore": "ASUSTeK COMPUTER INC.", "prodotto": "ROG Ally RC71L_RC71L",
             "scheda_fornitore": "ASUSTeK COMPUTER INC.", "scheda_nome": "RC71L"},
    "oxp": {"fornitore": "ONE-NETBOOK TECHNOLOGY CO., LTD.", "prodotto": "ONE XPLAYER",
            "scheda_fornitore": "ONE-NETBOOK", "scheda_nome": "ONE XPLAYER"},
    "generico": {"fornitore": "Valve", "prodotto": "Jupiter"},
}[quale]


def sistema_finto(*a, **k):
    return detect.Sistema(
        os={"ID": "bazzite", "PRETTY_NAME": "Bazzite 44 (KDE Plasma - finto per la prova)"},
        dmi=DMI, kernel="6.18-prova", immagine="ghcr.io/ublue-os/bazzite-deck:stable",
        gpu=["AMD Radeon Graphics (finto)"],
        strumenti={"plasma-apply-colorscheme": True, "kscreen-doctor": True, "kwriteconfig6": True,
                   "flatpak": True, "pkexec": True, "rpm-ostree": True, "curl": True,
                   "ujust": True, "steamosctl": True, "mullvad": False},
        brew="brew" if quale == "ally" else None,
        flatpak={"com.discordapp.Discord", "org.mozilla.firefox"},
        soglie_carica=[BAT] if quale == "ally" else [],
        batterie=["/sys/class/power_supply/BAT0"],
        rapl_pl1="/sys/class/powercap/intel-rapl:0/constraint_0_power_limit_uw" if quale == "oxp" else None,
    )


# gui.py importa `raccogli` per nome: va sostituito anche lì, altrimenti la finestra rileva il PC su cui gira la prova.
detect.raccogli = sistema_finto
gui.raccogli = sistema_finto
errori = []

# Una cartella di Steam finta con i file di impostazioni dei tre giochi, per provare le guide senza toccare il PC.
FINTA = Path(tempfile.mkdtemp(prefix="bhs-fumo-"))
_UTENTE = FINTA / ".local/share/Steam/steamapps/compatdata/1234/pfx/drive_c/users/steamuser/Documents"
_FILE_FINTI = {
    "Rockstar Games/Red Dead Redemption 2/Settings/system.xml":
        "<rage__fwuiSystemSettingsCollection>\n"
        "  <graphics>\n"
        "    <textureQuality>kSettingLevel_High</textureQuality>\n"
        "    <shadowQuality>kSettingLevel_Ultra</shadowQuality>\n"
        "    <msaa value=\"2\" />\n"
        "  </graphics>\n"
        "  <advancedGraphics>\n"
        "    <API>kSettingAPI_DX12</API>\n"
        "    <locked value=\"true\" />\n"
        "  </advancedGraphics>\n"
        "</rage__fwuiSystemSettingsCollection>\n",
    "The Witcher 3/user.settings":
        "[Viewport]\n"
        "VSync=true\n"
        "Resolution=\"2560x1600\"\n"
        "[PostProcess]\n"
        "AllowMotionBlur=true\n"
        "[Rendering]\n"
        "HairWorksLevel=2\n",
    "My Games/Skyrim Special Edition/SkyrimPrefs.ini":
        "[Display]\r\n"
        "iSize H=1600\r\n"
        "iSize W=2560\r\n"
        "iShadowMapResolution=4096\r\n"
        "bUseTAA=0\r\n"
        "[Grass]\r\n"
        "fGrassStartFadeDistance=7000.0000\r\n",
}
for _nome, _testo in _FILE_FINTI.items():
    (_UTENTE / _nome).parent.mkdir(parents=True, exist_ok=True)
    (_UTENTE / _nome).write_bytes(_testo.encode("utf-8"))
_trova_vero = giochi.trova_file
giochi.trova_file = lambda cfg, home=FINTA: _trova_vero(cfg, FINTA)


def foto(win, nome):
    try:
        for _ in range(4):                # lascia finire layout e distruzione dei widget tolti, come farebbe l'uso reale
            QApplication.processEvents()
        pix = win.grab()
        file_out = os.path.join(OUT, f"{ETICHETTA}_{nome}.png")
        pix.save(file_out)
        print(f"foto {nome} {win.width()}x{win.height()} -> {file_out}")
    except Exception:
        errori.append(f"foto {nome}")
        traceback.print_exc()


class TestFumoRunner:
    def __init__(self, app: QApplication):
        self.app = app
        self.win = gui.Procedura(dry_run=True, profilo_id=FISSO)
        self.win.resize(W, H)
        self.win.show()
        self.passi = ["benvenuto", "dispositivo", "app", "tweak", "riepilogo", "esecuzione"]
        self.i = 0
        QTimer.singleShot(500, self.passo)

    def passo(self):
        try:
            nome = self.passi[self.i]
            if nome == "app":
                self.win.sel_app.update({"heroic", "aria2"})
                self.win.sel_tweak.update({"aria2_conf", "mullvad_vpn", "blocca_versione"})
            foto(self.win, f"{self.i}_{nome}")
            self.i += 1
            if self.i >= len(self.passi):
                print("Tweak scelti:", sorted(self.win.sel_tweak))
                QTimer.singleShot(800, self.guide)
                return
            self.win._vai(+1)
            QTimer.singleShot(300, self.passo)
        except Exception:
            errori.append("passo")
            traceback.print_exc()
            self.app.quit()

    def guide(self):
        """Elenco delle guide, poi per ogni gioco il passo con «Applica» (in simulazione) e l'ultimo passo."""
        try:
            win, vista = self.win, self.win.vista_guide
            vista._file_progressi = FINTA / "guide.json"
            win._apri_guide()
            if win.stack.currentIndex() != win.i_guide:
                raise RuntimeError("le guide non si aprono (esecuzione ancora in corso?)")
            foto(win, "6_guide_elenco")
            for g in vista.guide:
                i_config = next(i for i, p in enumerate(g.passi) if p.azione == "config")
                vista.apri(g, i_config)
                vista.btn_applica.click()
                esito = vista.txt_esito.toPlainText()
                if "→" not in esito or "simulazione" not in esito:
                    raise RuntimeError(f"{g.id}: «Applica» in simulazione non ha prodotto il rapporto atteso:\n{esito}")
                foto(win, f"7_guida_{g.id}_applica")
                vista.vai(+1)
                foto(win, f"8_guida_{g.id}_tabella")
                for _ in range(len(g.passi)):      # fino a «Fine», che riporta all'elenco
                    if vista.pile.currentIndex() == 0:
                        break
                    vista.vai(+1)
                if vista.pile.currentIndex() != 0:
                    raise RuntimeError(f"{g.id}: «Fine» non riporta all'elenco")
            vista.apri(vista.guide[0], 0)
            foto(win, "9_guida_primo_passo")
            vista._chiudi()
            if win.stack.currentIndex() == win.i_guide or not win.btn_avanti.isVisible():
                raise RuntimeError("la chiusura delle guide non riporta alla procedura")
        except Exception:
            errori.append("guide")
            traceback.print_exc()
        self.app.quit()


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(gui.QSS)
    runner = TestFumoRunner(app)
    app.exec()
    print("ERRORI:", errori if errori else "nessuno")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
