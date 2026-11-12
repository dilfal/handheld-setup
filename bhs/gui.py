"""Interfaccia Qt6 (PySide6): procedura guidata a pagine per touch e gamepad."""

from __future__ import annotations

import subprocess
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .catalog import CATEGORIE, App, carica_catalogo
from .detect import Sistema, raccogli, testo_diagnosi
from .piano import costruisci_piano
from .profiles import Profilo, avviso_incoerenza, carica_profili, profilo_per_id, trova_profilo
from .runner import Azione, esegui_azioni, riassunto_comando
from .tweaks import Tweak, tutti_i_tweak

QSS = """
QWidget {
    font-size: 14px;
}
QPushButton.pill {
    min-height: 48px;
    padding: 0 24px;
    border-radius: 24px;
    font-weight: bold;
    font-size: 15px;
}
QPushButton.suggested {
    background-color: #3584e4;
    color: white;
    border: none;
}
QPushButton.suggested:hover {
    background-color: #1c71d8;
}
QPushButton.suggested:disabled {
    background-color: #555555;
    color: #888888;
}
QPushButton.destructive {
    background-color: #e01b24;
    color: white;
    border: none;
}
QPushButton.destructive:hover {
    background-color: #c01c28;
}
QFrame.card {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
}
QFrame.touch-row {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    min-height: 56px;
    padding: 8px 12px;
}
QFrame.touch-row:hover {
    background-color: rgba(255, 255, 255, 0.08);
}
QCheckBox::indicator {
    width: 26px;
    height: 26px;
}
QProgressBar {
    min-height: 20px;
    border-radius: 10px;
    text-align: center;
}
QPlainTextEdit.log {
    font-family: monospace;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px;
}
"""

PAGINE = ["benvenuto", "dispositivo", "app", "tweak", "riepilogo", "esecuzione"]


class TouchRiga(QFrame):
    """Riga touch con titolo, sottotitolo e controllo opzionale (es. checkbox o pulsante)."""

    def __init__(self, titolo: str, sottotitolo: str = "", widget_dx: Optional[QWidget] = None):
        super().__init__()
        self.setProperty("class", "touch-row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        testo_layout = QVBoxLayout()
        testo_layout.setSpacing(4)
        lbl_titolo = QLabel(titolo)
        lbl_titolo.setStyleSheet("font-weight: bold; font-size: 15px;")
        lbl_titolo.setWordWrap(True)
        testo_layout.addWidget(lbl_titolo)

        self.lbl_sub = None
        if sottotitolo:
            self.lbl_sub = QLabel(sottotitolo)
            self.lbl_sub.setStyleSheet("color: #aaaaaa; font-size: 13px;")
            self.lbl_sub.setWordWrap(True)
            testo_layout.addWidget(self.lbl_sub)

        layout.addLayout(testo_layout, 1)

        self.widget_dx = widget_dx
        if widget_dx is not None:
            layout.addWidget(widget_dx, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if self.widget_dx and isinstance(self.widget_dx, QCheckBox) and self.widget_dx.isEnabled():
            self.widget_dx.setChecked(not self.widget_dx.isChecked())
        super().mousePressEvent(event)


class EsecutoreWorker(QObject):
    finito = Signal(str, int, bool)
    avanzamento = Signal(int, int, str)
    log = Signal(str)

    def __init__(self, azioni: list[Azione], dry_run: bool, serve_riavvio: bool):
        super().__init__()
        self.azioni = azioni
        self.dry_run = dry_run
        self.serve_riavvio = serve_riavvio

    def run(self):
        ris = esegui_azioni(
            self.azioni,
            self.dry_run,
            log=lambda r: self.log.emit(r),
            avanzamento=lambda i, n, t: self.avanzamento.emit(i, n, t),
        )
        errori = sum(1 for r in ris if r.esito == "errore")
        msg = f"Finito con {errori} errori" if errori else "Finito"
        self.finito.emit(msg, errori, self.serve_riavvio)


class Procedura(QMainWindow):
    def __init__(self, dry_run: bool, profilo_id: str | None = None):
        super().__init__()
        self.setWindowTitle("Bazzite Handheld Setup (KDE Plasma)")
        self.resize(720, 960)
        self.dry_run = dry_run

        self.sistema: Sistema = raccogli()
        self.profili: list[Profilo] = carica_profili()
        self.catalogo: list[App] = carica_catalogo()
        self.tweaks: dict[str, Tweak] = tutti_i_tweak()
        fisso = profilo_per_id(self.profili, profilo_id) if profilo_id else None
        self.profilo_fisso = fisso is not None
        self.profilo: Profilo = fisso or trova_profilo(self.profili, self.sistema.dmi)
        self.avviso_profilo = avviso_incoerenza(self.profilo, self.sistema.dmi) if self.profilo_fisso else None

        self.sel_app: set[str] = set()
        self.sel_tweak: set[str] = set()
        self.in_esecuzione = False
        self._azioni_pronte: list[Azione] = []

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Intestazione superiore
        header_box = QHBoxLayout()
        titolo_app = QLabel("Bazzite Handheld Setup")
        titolo_app.setStyleSheet("font-size: 18px; font-weight: bold;")
        sottotitoli = ([self.profilo.nome] if self.profilo_fisso else []) + \
                      (["SIMULAZIONE"] if self.dry_run else [])
        if sottotitoli:
            sub = QLabel(f"({ ' · '.join(sottotitoli) })")
            sub.setStyleSheet("color: #3584e4; font-size: 14px; font-weight: bold;")
            header_box.addWidget(titolo_app)
            header_box.addWidget(sub)
        else:
            header_box.addWidget(titolo_app)
        header_box.addStretch(1)
        root_layout.addLayout(header_box)

        # Stack delle pagine
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)

        # Costruzione pagine
        self.stack.addWidget(self._p_benvenuto())
        self.stack.addWidget(self._p_dispositivo())
        self.stack.addWidget(self._p_app())
        self.pag_tweak = QWidget()
        self.stack.addWidget(self.pag_tweak)
        self.pag_riepilogo = QWidget()
        self.stack.addWidget(self.pag_riepilogo)
        self.stack.addWidget(self._p_esecuzione())
        self._ricostruisci_tweak()

        # Barra inferiore di navigazione
        nav_box = QHBoxLayout()
        self.btn_indietro = QPushButton("Indietro")
        self.btn_indietro.setProperty("class", "pill")
        self.btn_indietro.clicked.connect(lambda: self._vai(-1))
        nav_box.addWidget(self.btn_indietro)

        nav_box.addStretch(1)

        self.btn_avanti = QPushButton("Inizia")
        self.btn_avanti.setProperty("class", "pill suggested")
        self.btn_avanti.clicked.connect(lambda: self._vai(+1))
        nav_box.addWidget(self.btn_avanti)
        root_layout.addLayout(nav_box)

        self._aggiorna_bottoni()

    # ── Pagine ────────────────────────────────────────────────────────
    def _p_benvenuto(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(16)
        lay.addStretch(1)

        icon_lbl = QLabel("🎮")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 72px;")
        lay.addWidget(icon_lbl)

        titolo = QLabel("Benvenuto")
        titolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titolo.setStyleSheet("font-size: 26px; font-weight: bold;")
        lay.addWidget(titolo)

        disp = self.profilo.nome if self.profilo_fisso else "il tuo handheld"
        testo = (
            f"Ti aiuto a configurare Bazzite (KDE Plasma 6) su {disp}: app, emulatori, "
            "strumenti e impostazioni per il comfort d'uso su schermo touch.\n\n"
            "Nessuna modifica verrà apportata finché non confermerai nel riepilogo."
        )
        if not self.sistema.e_bazzite:
            testo += "\n\n⚠ Questo sistema non sembra Bazzite: alcune funzioni potrebbero non essere disponibili."
        if self.avviso_profilo:
            testo += f"\n\n⚠ {self.avviso_profilo}"

        lbl_desc = QLabel(testo)
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet("font-size: 15px; line-height: 1.4; color: #dddddd;")
        lay.addWidget(lbl_desc)

        lay.addStretch(2)
        return w

    def _p_dispositivo(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setSpacing(16)

        # Dispositivo rilevato
        gb_disp = QGroupBox("Dispositivo rilevato")
        lay_disp = QVBoxLayout(gb_disp)
        d = self.sistema.dmi
        lay_disp.addWidget(TouchRiga("Modello", f"{d.get('fornitore') or 'sconosciuto'} · {d.get('prodotto') or 'sconosciuto'}"))
        lay_disp.addWidget(TouchRiga("Sistema", self.sistema.os.get("PRETTY_NAME", "sconosciuto")))
        lay_disp.addWidget(TouchRiga("Immagine", self.sistema.immagine or "sconosciuta"))
        lay.addWidget(gb_disp)

        # Scelta profilo
        gb_prof = QGroupBox("Profilo")
        lay_prof = QVBoxLayout(gb_prof)
        if self.profilo_fisso:
            lay_prof.addWidget(TouchRiga(self.profilo.nome, self.avviso_profilo or "Il dispositivo corrisponde."))
        else:
            self.combo = QComboBox()
            self.combo.setStyleSheet("min-height: 44px; padding: 0 12px; font-size: 15px;")
            for p in self.profili:
                self.combo.addItem(p.nome)
            self.combo.setCurrentIndex(self.profili.index(self.profilo))
            self.combo.currentIndexChanged.connect(self._profilo_cambiato)
            lay_prof.addWidget(QLabel("Scegli il profilo se il rilevamento automatico non è corretto:"))
            lay_prof.addWidget(self.combo)
        lay.addWidget(gb_prof)

        # Note del profilo
        self.gb_note = QGroupBox("Cose da sapere per questo dispositivo")
        self.lay_note = QVBoxLayout(self.gb_note)
        lay.addWidget(self.gb_note)
        self._mostra_note()

        # Diagnosi
        gb_diag = QGroupBox("Diagnosi")
        lay_diag = QVBoxLayout(gb_diag)
        btn_copia = QPushButton("Copia")
        btn_copia.setStyleSheet("min-height: 40px; padding: 0 16px;")
        btn_copia.clicked.connect(self._copia_diagnosi)
        lay_diag.addWidget(TouchRiga("Copia rapporto di diagnosi", "Utile per segnalare problemi o verificare l'hardware.", btn_copia))
        lay.addWidget(gb_diag)

        lay.addStretch(1)
        return scroll

    def _copia_diagnosi(self):
        cb = QGuiApplication.clipboard()
        cb.setText(testo_diagnosi(self.sistema))
        QMessageBox.information(self, "Diagnosi", "Rapporto di diagnosi copiato negli appunti!")

    def _mostra_note(self):
        while self.lay_note.count():
            item = self.lay_note.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.gb_note.setTitle(f"Note per: {self.profilo.nome}")
        desc = QLabel(self.profilo.descrizione)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-style: italic; margin-bottom: 6px;")
        self.lay_note.addWidget(desc)
        for n in self.profilo.note:
            self.lay_note.addWidget(TouchRiga(n))

    def _profilo_cambiato(self, idx: int):
        self.profilo = self.profili[idx]
        self._mostra_note()
        self._ricostruisci_tweak()

    def _p_app(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setSpacing(16)

        presenti = sum(1 for a in self.catalogo if a.installata(self.sistema.flatpak))
        for cod, titolo in CATEGORIE.items():
            gb = QGroupBox(titolo)
            lay_gb = QVBoxLayout(gb)
            if cod == "launcher":
                lbl_info = QLabel(f"Già installate nel sistema: {presenti}. Le altre sono selezionabili sotto.")
                lbl_info.setStyleSheet("color: #aaaaaa; font-size: 13px; margin-bottom: 4px;")
                lay_gb.addWidget(lbl_info)

            for app in (a for a in self.catalogo if a.categoria == cod):
                sub = app.descrizione
                chk = QCheckBox()
                riga = TouchRiga(app.nome, sub, chk)
                if app.tipo == "manuale":
                    sub += " (da installare a mano: mostra link)"
                if not app.verificato:
                    sub += " · da verificare"

                if app.installata(self.sistema.flatpak):
                    chk.setChecked(True)
                    chk.setEnabled(False)
                    sub += " · già installata"
                elif app.tipo == "brew" and not self.sistema.brew:
                    chk.setEnabled(False)
                    sub += " · richiede Homebrew (non trovato)"
                else:
                    chk.toggled.connect(lambda val, aid=app.id: (self.sel_app.add(aid) if val else self.sel_app.discard(aid)))

                if riga.lbl_sub:
                    riga.lbl_sub.setText(sub)
                lay_gb.addWidget(riga)
            lay.addWidget(gb)

        lay.addStretch(1)
        return scroll

    def _ricostruisci_tweak(self):
        self.sel_tweak.clear()
        lay_prec = self.pag_tweak.layout()
        if lay_prec:
            while lay_prec.count():
                item = lay_prec.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            lay_prec = QVBoxLayout(self.pag_tweak)
            lay_prec.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setSpacing(16)

        gb_cons = QGroupBox("Impostazioni consigliate")
        lay_cons = QVBoxLayout(gb_cons)

        gb_adv = QGroupBox("Avanzate (solo se sai cosa fai)")
        lay_adv = QVBoxLayout(gb_adv)

        n_adv = 0
        for tid in dict.fromkeys(self.profilo.consigliati + self.profilo.avanzati):
            t = self.tweaks.get(tid)
            if t is None:
                continue
            riga, e_consigliato = self._crea_riga_tweak(t, tid in self.profilo.consigliati)
            if t.avanzato or tid in self.profilo.avanzati:
                lay_adv.addWidget(riga)
                n_adv += 1
            else:
                lay_cons.addWidget(riga)

        lay.addWidget(gb_cons)
        if n_adv:
            lay.addWidget(gb_adv)
        lay.addStretch(1)

        lay_prec.addWidget(scroll)

    def _crea_riga_tweak(self, t: Tweak, consigliato: bool) -> tuple[TouchRiga, bool]:
        stato = t.stato(self.sistema)
        sub = t.descrizione
        chk = QCheckBox()
        riga = TouchRiga(t.titolo, sub, chk)

        if stato == "attivo":
            chk.setChecked(True)
            chk.setEnabled(False)
            sub += " · già attivo"
        elif stato == "non_supportato":
            chk.setEnabled(False)
            sub += " · non supportato su questo dispositivo"
        elif stato == "in_attesa":
            chk.setEnabled(False)
            sub += " · in attesa del riavvio"
        elif not t.comandi_per(self.sistema):
            chk.setEnabled(False)
            sub += " · in arrivo"
        else:
            if consigliato and not t.avanzato:
                chk.setChecked(True)
                self.sel_tweak.add(t.id)
            chk.toggled.connect(lambda val, tid=t.id: (self.sel_tweak.add(tid) if val else self.sel_tweak.discard(tid)))

        nota = t.nota_stato(self.sistema) if t.nota_stato else ""
        if nota:
            sub += f" · {nota}"
        if t.avviso:
            sub += f"\n⚠ {t.avviso}"

        if riga.lbl_sub:
            riga.lbl_sub.setText(sub)
        return riga, consigliato

    def _p_esecuzione(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)

        self.lbl_stato = QLabel("Pronto")
        self.lbl_stato.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(self.lbl_stato)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        lay.addWidget(self.barra)

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setProperty("class", "log")
        lay.addWidget(self.txt_log, 1)

        self.btn_riavvia = QPushButton("Riavvia ora")
        self.btn_riavvia.setProperty("class", "pill destructive")
        self.btn_riavvia.setVisible(False)
        self.btn_riavvia.clicked.connect(self._chiedi_riavvio)
        lay.addWidget(self.btn_riavvia, 0, Qt.AlignmentFlag.AlignCenter)

        return w

    # ── Riepilogo ─────────────────────────────────────────────────────
    def _mostra_riepilogo(self):
        lay_prec = self.pag_riepilogo.layout()
        if lay_prec:
            while lay_prec.count():
                item = lay_prec.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            lay_prec = QVBoxLayout(self.pag_riepilogo)
            lay_prec.setContentsMargins(0, 0, 0, 0)

        azioni = costruisci_piano(self.catalogo, self.tweaks, self.sel_app, self.sel_tweak, self.sistema)
        self._azioni_pronte = azioni

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        desc = "Premi «Installa» per applicare le seguenti azioni:" if azioni else "Non hai selezionato alcuna azione."
        gb = QGroupBox("Riepilogo azioni da eseguire")
        lay_gb = QVBoxLayout(gb)
        lbl_info = QLabel(desc)
        lbl_info.setStyleSheet("color: #dddddd; font-size: 14px; margin-bottom: 8px;")
        lay_gb.addWidget(lbl_info)

        for a in azioni:
            cmd_info = a.nota or riassunto_comando(a.argv)
            lay_gb.addWidget(TouchRiga(a.titolo, cmd_info))

        lay.addWidget(gb)
        lay.addStretch(1)
        lay_prec.addWidget(scroll)

    # ── Navigazione ───────────────────────────────────────────────────
    def _indice(self) -> int:
        return self.stack.currentIndex()

    def _vai(self, passo: int):
        i = self._indice()
        nome = PAGINE[i]
        if nome == "esecuzione":
            self.close()
            return
        if nome == "riepilogo" and passo > 0:
            self._avvia()
            return

        j = max(0, min(len(PAGINE) - 1, i + passo))
        if PAGINE[j] == "riepilogo":
            self._mostra_riepilogo()

        self.stack.setCurrentIndex(j)
        self._aggiorna_bottoni()

    def _aggiorna_bottoni(self):
        nome = PAGINE[self._indice()]
        self.btn_indietro.setVisible(nome not in ("benvenuto", "esecuzione"))
        labels = {"benvenuto": "Inizia", "riepilogo": "Installa", "esecuzione": "Chiudi"}
        self.btn_avanti.setText(labels.get(nome, "Avanti"))
        self.btn_avanti.setEnabled(not self.in_esecuzione)

    # ── Esecuzione ────────────────────────────────────────────────────
    def _avvia(self):
        self.in_esecuzione = True
        self.stack.setCurrentIndex(PAGINE.index("esecuzione"))
        self._aggiorna_bottoni()
        serve_riavvio = any(self.tweaks[t].richiede_riavvio for t in self.sel_tweak if t in self.tweaks)

        self.thread = QThread()
        self.worker = EsecutoreWorker(self._azioni_pronte, self.dry_run, serve_riavvio)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._aggiungi_log)
        self.worker.avanzamento.connect(self._aggiorna_avanzamento)
        self.worker.finito.connect(self._fine_esecuzione)
        self.worker.finito.connect(self.thread.quit)
        self.thread.start()

    def _aggiungi_log(self, riga: str):
        self.txt_log.appendPlainText(riga)

    def _aggiorna_avanzamento(self, i: int, n: int, titolo: str):
        val = int((i / n * 100)) if n else 100
        self.barra.setValue(val)
        self.lbl_stato.setText(titolo)

    def _fine_esecuzione(self, messaggio: str, errori: int = 0, serve_riavvio: bool = False):
        self.in_esecuzione = False
        if serve_riavvio and not errori:
            messaggio += ": per applicare le modifiche serve un riavvio"
            self.btn_riavvia.setVisible(True)
        self.lbl_stato.setText(messaggio)
        self.barra.setValue(100)
        self._aggiorna_bottoni()

    def _chiedi_riavvio(self):
        r = QMessageBox.question(
            self,
            "Riavviare adesso?",
            "Salva quello che stai facendo prima di riavviare.\n\n"
            "Se hai installato Mullvad VPN, dopo il riavvio rilancia questo script "
            "per completare l'abilitazione del servizio.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            if self.dry_run:
                self.lbl_stato.setText("Simulazione: non riavvio")
            else:
                subprocess.Popen(["systemctl", "reboot"])


def avvia(dry_run: bool, profilo_id: str | None = None) -> int:
    import sys
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(QSS)
    finestra = Procedura(dry_run, profilo_id)
    finestra.show()
    return app.exec()
