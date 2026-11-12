"""Test di fumo della GUI con PySide6: apre la finestra, naviga in simulazione, salva uno screenshot per pagina.

Uso: python3 tools/fumo_gui.py <ally|oxp|generico> <larghezza> <altezza> <cartella_output> [auto|ID_PROFILO]
Usa un sistema finto e la simulazione: non modifica nulla.
"""
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bhs import detect, gui

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


def foto(win, nome):
    try:
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
                QTimer.singleShot(200, self.app.quit)
                return
            self.win._vai(+1)
            QTimer.singleShot(300, self.passo)
        except Exception:
            errori.append("passo")
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
