# STATO: Bazzite Handheld Setup (v0.6.0)

Aggiornato il 12 novembre 2026.

## Fatto
- **Pubblicazione su GitHub (`dilfal/bazzite-handheld-setup`) e sul dominio `070293.xyz` (`dilfal/070293`)**:
  - Scorciatoie da terminale ultra-corte attive in HTTPS:
    - OneXPlayer 1S: `curl -L 070293.xyz/oxp | sh` (o senza pipe: `curl -Lo f 070293.xyz/oxp && sh f`)
    - ASUS ROG Ally: `curl -L 070293.xyz/ally | sh`
    - Generico: `curl -L 070293.xyz/bhs | sh`
  - Guide interattive HTML pubblicate online su `https://070293.xyz/` (e `/guide/`).
- **Modalità «Cura Batteria (80%)» (`limite_carica_80`) + Sblocco al 100% (`carica_100`)**:
  - **Con soglia hardware EC (ROG Ally)**: imposta `80%`, crea `bhs-limite-carica.service` agganciato sia al boot (`multi-user.target`) sia al risveglio dallo standby (`sleep.target` / `After=suspend.target...`) e scrive la regola udev `/etc/udev/rules.d/99-bhs-cura-batteria.rules` al collegamento del cavo USB-C (risolve il bug Bazzite #3855).
  - **Senza soglia hardware EC (OneXPlayer 1S Intel)**: attiva un timer utente (`bhs-cura-batteria.timer` + script `~/.local/bin/bhs-cura-batteria-check`) che avvisa automaticamente con una notifica appena la batteria in carica raggiunge l'80%.
  - **`carica_100` (nelle Avanzate)**: disattiva la Cura Batteria e riporta la carica al 100% (utile prima di un viaggio).
- **Controllo TDP (Intel RAPL per OneXPlayer 1S) e Ventole**:
  - Rilevamento in `detect.py` (`--diagnosi`) di Intel RAPL (`constraint_0_power_limit_uw`) e sensori ventole `hwmon`.
  - Nuovi tweak TDP persistenti a riavvio e standby per processori Intel: `tdp_20w` (consigliato su OneXPlayer 1S: 20W PL1 / 25W PL2, ~10°C in meno e ventole quiete), `tdp_15w` (15W/20W silenzioso/batteria) e `tdp_28w` (28W/35W Turbo).
  - Documentato nelle guide e nel profilo OneXPlayer 1S anche il tasto fisico **MUTE** sul retro (tenuto premuto 2 secondi) per attivare la Modalità Silenziosa (Night Mode) hardware delle ventole.
- **Installatore intelligente a 3 modalità** (Console `Ctrl+Alt+F3` con fix automatico + Autostart KDE, Live USB `/mnt/sysimage`, Desktop KDE).
- **Test unitari**: 65 test passati al 100% in Fedora 44 WSL.

## File toccati
- `bhs/detect.py`, `bhs/tweaks.py`, `data/profiles/*.toml`, `tests/test_core.py`
- `guide/installazione_onexplayer_1s.html`, `guide/installazione_rog_ally.html`, `STATO.md`
- Sincronizzato `C:\Users\df\Dev\GitHub\siti-web\070293` (`070293.xyz`)

## Prossimo passo
- Test sul campo sui due dispositivi fisici usando `curl -L 070293.xyz/oxp | sh` e `curl -L 070293.xyz/ally | sh`.
