# STATO: Bazzite Handheld Setup (v0.6.0)

Aggiornato il 12 novembre 2026 (sera), dopo la revisione degli errori.

## Fatto in questa sessione (pubblicato: commit `85fbec6` su `dilfal/bazzite-handheld-setup`, `dffff34` su `dilfal/070293`)
- **Git riparato**: 82 `desktop.ini` di Google Drive dentro `.git` (anche in `.git/refs`) facevano fallire `git fetch` e `git fsck`. Tolti: ora entrambi puliti.
- **ROG Ally: immagine sbagliata**. `bazzite-ally` non esiste più (la ISO dà 404; in `ublue-os/bazzite` restano solo `bazzite`, `bazzite-deck` e varianti). Corretto in `bazzite-deck` in guide (`index.html`, `installazione_rog_ally.html`), README, profilo Ally, PROSSIMI_PASSI.
- **Decky**: `ujust setup-decky` senza argomento apre un menu a scelta, impossibile dalla finestra. Ora il catalogo usa `setup-decky install` (ricetta e argomenti separati in `catalog.py`).
- **Avviso batteria 80% (OneXPlayer)**: se la notifica falliva (Game Mode) l'avviso veniva comunque segnato come dato e non ripartiva più; ora si segna solo se la notifica parte, e lo script esce sempre con 0.
- **Limite di carica (Ally)**: la regola udev usa `systemctl start --no-block`; il servizio scrive solo se il valore è diverso da 80 (niente cicli di eventi). Provato con systemd vero in Fedora WSL.
- **Installatore**: l'aggiornamento via `curl | sh` conserva `.venv` (prima riscaricava PySide6 ogni volta). Dedicati rigenerati.
- **Finestra**: testi secondari con colore preso dal tema (con tema chiaro il benvenuto era quasi invisibile). `--elenco` allineato.
- **`tools/fumo_gui.py`**: sostituiva `detect.raccogli` ma non `gui.raccogli`, quindi provava il PC reale e non il sistema finto. Corretto; tre profili senza errori (PySide6 6.12 su Windows, offscreen).
- **Documenti**: README e PROSSIMI_PASSI allineati (18 tweak, 70 test, voci completate, prove nuove per TDP e Cura Batteria).
- **Verificato e a posto**: scorciatoie online `/oxp`, `/ally`, `/bhs` identiche ai file locali; archivio GitHub scaricabile; 21 ID Flathub esistenti; `.repo` di Mullvad accettato; `ujust update`, `regenerate-grub`, `setup-boot-windows-steam`, `bios`, `enroll-secure-boot-key` esistono.
- **Test**: 70 verdi su Windows (5 saltati) e in Fedora 44 WSL (nessuno saltato).

## Manca
- Prove sui due dispositivi (elenco in `PROSSIMI_PASSI.md`, sezione 4).

## Non verificabile senza i dispositivi
- `sudo -A` di `setup-decky install` (serve la finestra della password di Bazzite).
- Limiti RAPL: il BIOS del OneXPlayer può imporre un proprio tetto.
- `/mnt/sysimage` e utente già creato nella Live USB attuale di Bazzite.
- `kscreen-doctor output.1.scale.…` (numero dell'uscita) e tastiera Maliit su Plasma 6.

## Note d'uso
- WSL da Git Bash: `MSYS_NO_PATHCONV=1 wsl -d FedoraLinux-44 --cd /mnt/c/… -- comando`; per comandi con `$` o virgolette, scrivere uno script e lanciarlo.

## Prossimo passo
- Prove sul campo con `curl -L 070293.xyz/oxp | sh` e `curl -L 070293.xyz/ally | sh`.
