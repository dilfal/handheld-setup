# STATO: Bazzite Handheld Setup (v0.6.0)

Aggiornato il 12 novembre 2026.

## Fatto
- **Pubblicazione su GitHub (`dilfal/bazzite-handheld-setup`) e sul dominio `070293.xyz` (`dilfal/070293`)**:
  - Scorciatoie da terminale ultra-corte attive in HTTPS:
    - OneXPlayer 1S: `curl -L 070293.xyz/oxp | sh` (o senza pipe: `curl -Lo f 070293.xyz/oxp && sh f`)
    - ASUS ROG Ally: `curl -L 070293.xyz/ally | sh`
    - Generico: `curl -L 070293.xyz/bhs | sh`
  - Guide interattive HTML pubblicate online su `https://070293.xyz/` (e `/guide/`).
- **Installatore intelligente a 3 modalità (`install.sh`, `install-onexplayer.sh`, `install-rog-ally.sh`)**:
  1. **Modalità Console Automatica (`Ctrl+Alt+F3`)**: se lanciato senza sessione grafica (es. schermo nero al primo avvio del OneXPlayer 1S), non si blocca più con errore ma applica subito `INTEL_DEBUG=norbc`, scarica l'app e prepara `.venv`, imposta l'apertura automatica una-tantum della finestra grafica al primo accesso al Desktop KDE (`~/.config/autostart/bhs-first-run.desktop`) e riavvia il sistema dopo 5 secondi.
  2. **Modalità Live USB (`/mnt/sysimage`)**: se lanciato a fine installazione di Bazzite prima del riavvio della chiavetta USB, inietta `INTEL_DEBUG=norbc`, l'app e l'Autostart KDE direttamente sull'SSD, evitando del tutto lo schermo nero al primo avvio.
  3. **Modalità Desktop KDE Plasma 6**: scarica/aggiorna l'app, prepara PySide6 in `.venv`, crea le icone nel menu Start e sul Desktop e avvia la finestra Qt6.
- **Compatibilità POSIX `sh` + `bash`**: rimossi i bashismi in `install.sh` così funziona sia con `| sh` sia con `| bash`.
- **Test unitari**: 61 test passati al 100% (inclusi i test della modalità console automatica e della modalità Live USB in WSL Fedora 44).

## File toccati
- `install.sh`, `install-onexplayer.sh`, `install-rog-ally.sh`, `tools/genera_installatori.py`
- `bhs/__init__.py`, `tests/test_core.py`
- `guide/index.html`, `guide/installazione_onexplayer_1s.html`, `guide/installazione_rog_ally.html`
- `README.md`, `PROSSIMI_PASSI.md`, `STATO.md`
- Repository `C:\Users\df\Dev\GitHub\siti-web\070293` (`dilfal/070293` → `https://070293.xyz`)

## Prossimo passo
- Test sul campo sui due dispositivi fisici usando `curl -L 070293.xyz/oxp | sh` e `curl -L 070293.xyz/ally | sh`.
