"""Guide ai giochi nella finestra Qt6: elenco dei giochi e un passo per schermata, pensato per il touch.

La guida ricorda a che passo si era arrivati: molti passi si fanno fuori da questa finestra (in Gaming Mode
o dentro il gioco), quindi alla riapertura si riparte da lì.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import giochi
from .giochi import DOVE, Guida, Passo, testo_html


def _svuota(layout) -> None:
    while layout.count():
        voce = layout.takeAt(0)
        if voce.widget():
            # Prima si stacca dal genitore: con il solo deleteLater() il vecchio widget resta disegnato fino al giro
            # successivo del ciclo degli eventi e si sovrappone al nuovo contenuto.
            vecchio = voce.widget()
            vecchio.hide()
            vecchio.setParent(None)
            vecchio.deleteLater()
        elif voce.layout():
            _svuota(voce.layout())


class VistaGuide(QWidget):
    """Elenco delle guide e passo corrente. `chiudi` riporta alla procedura guidata."""

    def __init__(self, profilo_id: str, nome_profilo: str, simulazione: bool, chiudi: Callable[[], None],
                 file_progressi: Path = giochi.FILE_PROGRESSI):
        super().__init__()
        from .gui import colore_tenue      # qui e non in testa al file: gui.py importa questo modulo
        self._tenue = colore_tenue()
        self.simulazione = simulazione
        self._chiudi = chiudi
        self._file_progressi = file_progressi
        self.guida: Optional[Guida] = None
        self.indice = 0
        self._file_a_mano: dict[str, list[Path]] = {}

        fuori = QVBoxLayout(self)
        fuori.setContentsMargins(0, 0, 0, 0)
        self.pile = QStackedWidget()
        fuori.addWidget(self.pile)

        self.pag_elenco = QWidget()
        self.lay_elenco = QVBoxLayout(self.pag_elenco)
        self.lay_elenco.setContentsMargins(0, 0, 0, 0)
        self.pile.addWidget(self.pag_elenco)
        self.pile.addWidget(self._costruisci_passo())
        self.imposta_profilo(profilo_id, nome_profilo)

    # ── Elenco ────────────────────────────────────────────────────────
    def imposta_profilo(self, profilo_id: str, nome_profilo: str) -> None:
        self.profilo_id, self.nome_profilo = profilo_id, nome_profilo
        self.guide = giochi.carica_guide(profilo_id)
        self.mostra_elenco()

    def mostra_elenco(self) -> None:
        _svuota(self.lay_elenco)
        self.guida = None
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        dentro = QWidget()
        scroll.setWidget(dentro)
        lay = QVBoxLayout(dentro)
        lay.setSpacing(12)

        titolo = QLabel("Guide ai giochi")
        titolo.setStyleSheet("font-size: 24px; font-weight: bold;")
        lay.addWidget(titolo)
        sotto = QLabel(f"Un passo per volta, con le impostazioni scelte per: {self.nome_profilo}. "
                       "Puoi chiudere quando vuoi: la guida riparte dal passo a cui eri arrivato.")
        sotto.setWordWrap(True)
        sotto.setStyleSheet(f"color: {self._tenue}; font-size: 14px; margin-bottom: 6px;")
        lay.addWidget(sotto)

        progressi = giochi.leggi_progressi(self._file_progressi)
        for g in self.guide:
            fatto = min(progressi.get(g.id, 0), len(g.passi) - 1)
            scheda = QFrame()
            scheda.setProperty("class", "card")
            riga = QHBoxLayout(scheda)
            riga.setContentsMargins(16, 14, 16, 14)
            riga.setSpacing(12)
            testi = QVBoxLayout()
            nome = QLabel(g.nome)
            nome.setStyleSheet("font-size: 18px; font-weight: bold;")
            nome.setWordWrap(True)
            testi.addWidget(nome)
            obiettivo = QLabel(g.obiettivo)
            obiettivo.setWordWrap(True)
            obiettivo.setStyleSheet(f"color: {self._tenue}; font-size: 13px;")
            testi.addWidget(obiettivo)
            riga.addLayout(testi, 1)
            apri = QPushButton(f"Riprendi dal passo {fatto + 1}" if fatto else "Inizia")
            apri.setProperty("class", "pill suggested")
            apri.clicked.connect(lambda _=False, guida=g, da=fatto: self.apri(guida, da))
            riga.addWidget(apri, 0, Qt.AlignmentFlag.AlignVCenter)
            lay.addWidget(scheda)
        lay.addStretch(1)
        self.lay_elenco.addWidget(scroll, 1)

        barra = QHBoxLayout()
        torna = QPushButton("Torna alla configurazione")
        torna.setProperty("class", "pill")
        torna.clicked.connect(self._chiudi)
        barra.addWidget(torna)
        barra.addStretch(1)
        self.lay_elenco.addLayout(barra)
        self.pile.setCurrentIndex(0)

    # ── Passo ─────────────────────────────────────────────────────────
    def _costruisci_passo(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        testa = QHBoxLayout()
        self.lbl_gioco = QLabel()
        self.lbl_gioco.setStyleSheet(f"color: {self._tenue}; font-size: 14px; font-weight: bold;")
        testa.addWidget(self.lbl_gioco, 1)
        self.lbl_dove = QLabel()
        self.lbl_dove.setProperty("class", "chip")
        testa.addWidget(self.lbl_dove, 0, Qt.AlignmentFlag.AlignRight)
        lay.addLayout(testa)

        self.avanzamento = QProgressBar()
        self.avanzamento.setTextVisible(False)
        self.avanzamento.setFixedHeight(8)
        lay.addWidget(self.avanzamento)

        self.lbl_titolo = QLabel()
        self.lbl_titolo.setWordWrap(True)
        self.lbl_titolo.setStyleSheet("font-size: 21px; font-weight: bold;")
        lay.addWidget(self.lbl_titolo)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.corpo = QWidget()
        self.lay_corpo = QVBoxLayout(self.corpo)
        self.lay_corpo.setSpacing(12)
        self.scroll.setWidget(self.corpo)
        lay.addWidget(self.scroll, 1)

        barra = QHBoxLayout()
        self.btn_prima = QPushButton("Indietro")
        self.btn_prima.setProperty("class", "pill")
        self.btn_prima.clicked.connect(lambda: self.vai(-1))
        barra.addWidget(self.btn_prima)
        self.btn_elenco = QPushButton("Tutte le guide")
        self.btn_elenco.setProperty("class", "pill")
        self.btn_elenco.clicked.connect(self.mostra_elenco)
        barra.addWidget(self.btn_elenco)
        barra.addStretch(1)
        self.btn_dopo = QPushButton("Avanti")
        self.btn_dopo.setProperty("class", "pill suggested")
        self.btn_dopo.clicked.connect(lambda: self.vai(+1))
        barra.addWidget(self.btn_dopo)
        lay.addLayout(barra)
        return w

    def apri(self, guida: Guida, da: int = 0) -> None:
        self.guida = guida
        self.indice = max(0, min(da, len(guida.passi) - 1))
        self._mostra_passo()
        self.pile.setCurrentIndex(1)

    def vai(self, passo: int) -> None:
        if self.guida is None:
            return
        nuovo = self.indice + passo
        if nuovo >= len(self.guida.passi):          # «Fine» sull'ultimo passo: si ricomincia da capo la prossima volta
            giochi.salva_progresso(self.guida.id, 0, self._file_progressi)
            self.mostra_elenco()
            return
        self.indice = max(0, nuovo)
        giochi.salva_progresso(self.guida.id, self.indice, self._file_progressi)
        self._mostra_passo()

    def _mostra_passo(self) -> None:
        assert self.guida is not None
        g, p, n = self.guida, self.guida.passi[self.indice], len(self.guida.passi)
        self.lbl_gioco.setText(f"{g.nome} · passo {self.indice + 1} di {n}")
        self.lbl_dove.setText(DOVE.get(p.dove, ""))
        self.lbl_dove.setVisible(p.dove in DOVE)
        self.avanzamento.setRange(0, n)
        self.avanzamento.setValue(self.indice + 1)
        self.lbl_titolo.setText(p.titolo)
        self.btn_prima.setVisible(self.indice > 0)
        self.btn_dopo.setText("Fine" if self.indice == n - 1 else "Avanti")

        _svuota(self.lay_corpo)
        if p.testo:
            self.lay_corpo.addWidget(self._etichetta(testo_html(p.testo)))
        if p.nota_app:
            nota = self._etichetta(testo_html(p.nota_app))
            nota.setStyleSheet(f"color: {self._tenue}; font-size: 14px;")
            self.lay_corpo.addWidget(nota)
        if p.copia:
            self.lay_corpo.addWidget(self._riquadro_copia(p.copia))
        if p.azione == "config":
            self.lay_corpo.addWidget(self._riquadro_config(g))
        if p.voci:
            self.lay_corpo.addWidget(self._tabella(p))
        self.lay_corpo.addStretch(1)
        self.scroll.verticalScrollBar().setValue(0)

    @staticmethod
    def _etichetta(html: str) -> QLabel:
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 15px;")
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return lbl

    def _tabella(self, p: Passo) -> QFrame:
        riquadro = QFrame()
        riquadro.setProperty("class", "card")
        griglia = QGridLayout(riquadro)
        griglia.setContentsMargins(14, 10, 14, 10)
        griglia.setHorizontalSpacing(16)
        griglia.setVerticalSpacing(8)
        griglia.setColumnStretch(0, 3)
        griglia.setColumnStretch(1, 2)
        for r, (voce, valore) in enumerate(p.voci):
            a = QLabel(voce)
            a.setWordWrap(True)
            a.setStyleSheet(f"color: {self._tenue}; font-size: 14px;")
            b = QLabel(valore)
            b.setWordWrap(True)
            b.setStyleSheet("font-size: 15px; font-weight: bold;")
            griglia.addWidget(a, r, 0)
            griglia.addWidget(b, r, 1)
        return riquadro

    def _riquadro_copia(self, testo: str) -> QFrame:
        riquadro = QFrame()
        riquadro.setProperty("class", "card")
        riga = QHBoxLayout(riquadro)
        riga.setContentsMargins(14, 10, 14, 10)
        lbl = QLabel(testo)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-family: monospace; font-size: 14px;")
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        riga.addWidget(lbl, 1)
        btn = QPushButton("Copia")
        btn.setStyleSheet("min-height: 40px; padding: 0 16px;")

        def copia():
            QGuiApplication.clipboard().setText(testo)
            btn.setText("Copiato")
        btn.clicked.connect(copia)
        riga.addWidget(btn)
        return riquadro

    # ── Impostazioni automatiche ──────────────────────────────────────
    def _riquadro_config(self, g: Guida) -> QFrame:
        riquadro = QFrame()
        riquadro.setProperty("class", "card")
        lay = QVBoxLayout(riquadro)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        self.txt_esito = QPlainTextEdit()
        self.txt_esito.setReadOnly(True)
        self.txt_esito.setProperty("class", "log")
        self.txt_esito.setMinimumHeight(150)
        if g.config is None:
            avviso = QLabel("Per questo dispositivo non ci sono impostazioni automatiche: usa la tabella dei passi seguenti.")
            avviso.setWordWrap(True)
            lay.addWidget(avviso)
            return riquadro

        bottoni = QHBoxLayout()
        self.btn_applica = QPushButton("Applica (simulazione)" if self.simulazione else "Applica")
        self.btn_applica.setProperty("class", "pill suggested")
        self.btn_applica.clicked.connect(lambda: self._esegui_config("applica"))
        bottoni.addWidget(self.btn_applica)
        self.btn_ripristina = QPushButton("Ripristina")
        self.btn_ripristina.setProperty("class", "pill")
        self.btn_ripristina.clicked.connect(lambda: self._esegui_config("ripristina"))
        bottoni.addWidget(self.btn_ripristina)
        bottoni.addStretch(1)
        lay.addLayout(bottoni)

        self.btn_scegli = QPushButton("Scegli il file a mano…")
        self.btn_scegli.setStyleSheet("min-height: 40px; padding: 0 16px;")
        self.btn_scegli.clicked.connect(self._scegli_file)
        self.btn_scegli.setVisible(False)
        lay.addWidget(self.btn_scegli, 0, Qt.AlignmentFlag.AlignLeft)

        file = self._file_config(g)
        self.txt_esito.setPlainText(
            "File trovati:\n" + "\n".join(f"  {f}" for f in file) if file else self._testo_non_trovato(g))
        self.btn_scegli.setVisible(not file)
        lay.addWidget(self.txt_esito)
        return riquadro

    def _file_config(self, g: Guida) -> list[Path]:
        assert g.config is not None
        return self._file_a_mano.get(g.id) or giochi.trova_file(g.config)

    @staticmethod
    def _testo_non_trovato(g: Guida) -> str:
        assert g.config is not None
        return (f"Non trovo ancora {' o '.join(g.config.file)}.\n"
                "Il gioco crea questo file la prima volta che arriva al menu principale: "
                "se l'hai già avviato da Steam con Proton, riprova. "
                "Se usi un altro launcher (Heroic, Lutris), indica il file a mano.")

    def _esegui_config(self, cosa: str) -> None:
        g = self.guida
        if g is None or g.config is None:
            return
        file = self._file_config(g)
        if not file:
            self.txt_esito.setPlainText(self._testo_non_trovato(g))
            self.btn_scegli.setVisible(True)
            return
        if cosa == "ripristina":
            rapporti = giochi.ripristina_config(file, self.simulazione)
        else:
            rapporti = giochi.applica_config(g.config, file, self.simulazione)
        self.txt_esito.setPlainText(giochi.testo_rapporti(rapporti, self.simulazione))

    def _scegli_file(self) -> None:
        g = self.guida
        if g is None or g.config is None:
            return
        nomi = " ".join(g.config.file)
        partenza = Path.home() / ".local/share/Steam/steamapps/compatdata"
        scelto, _ = QFileDialog.getOpenFileName(self, f"Scegli {nomi}",
                                                str(partenza if partenza.is_dir() else Path.home()),
                                                f"Impostazioni del gioco ({nomi});;Tutti i file (*)")
        if not scelto:
            return
        if not giochi.file_ammesso(g.config, scelto):
            self.txt_esito.setPlainText(f"«{Path(scelto).name}» non è un file di impostazioni di {g.nome}: "
                                        f"scegli {' o '.join(g.config.file)}. Non ho cambiato niente.")
            return
        self._file_a_mano[g.id] = [Path(scelto)]
        self.txt_esito.setPlainText(f"File scelto:\n  {scelto}\nOra premi Applica.")
