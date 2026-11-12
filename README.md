# Bazzite Handheld Setup

Configurazione guidata, con interfaccia nativa Qt6 (PySide6), da lanciare dopo l'installazione di **Bazzite (KDE Plasma 6) per handheld**.
Due script separati, uno per dispositivo, che condividono lo stesso codice:

| Dispositivo | Scorciatoia | Script | Profilo | Immagine Bazzite raccomandata |
|---|---|---|---|---|
| OneXPlayer 1S (8,4", i7-1195G7) | `070293.xyz/oxp` | `install-onexplayer.sh` | `onexplayer1s` | `bazzite-deck` (KDE Plasma 6) |
| ASUS ROG Ally (Z1 Extreme) | `070293.xyz/ally` | `install-rog-ally.sh` | `rogallyz1x` | `bazzite-ally` (KDE Plasma 6) |
| Altro handheld | `070293.xyz/bhs` | `install.sh` | `generico` | `bazzite-deck` (KDE Plasma 6) |

## Avvio Rapido (Desktop, Console `Ctrl+Alt+F3` o Live USB)

```bash
# OneXPlayer 1S (funziona sul Desktop KDE, in console Ctrl+Alt+F3 con schermo nero e dalla Live USB)
curl -L 070293.xyz/oxp | sh

# ASUS ROG Ally (Z1 Extreme)
curl -L 070293.xyz/ally | sh
```

*Variante senza barra verticale `|` (comoda da digitare a mano in console `Ctrl+Alt+F3` su qualsiasi tastiera):*
```bash
curl -Lo f 070293.xyz/oxp
sh f
```

Indirizzo completo dal repository GitHub (`dilfal/bazzite-handheld-setup`):
```bash
# OneXPlayer 1S
curl -fsSL https://raw.githubusercontent.com/dilfal/bazzite-handheld-setup/main/install-onexplayer.sh | bash
# ROG Ally
curl -fsSL https://raw.githubusercontent.com/dilfal/bazzite-handheld-setup/main/install-rog-ally.sh | bash
```

Opzioni manuali (dopo `sh -s --` o `bash -s --`): `--dry-run` (solo simulazione), `--diagnosi` (rapporto di sistema), `--elenco` (tweak e stato),
`--applica ID...` (applica solo quei tweak, senza interfaccia).

Da una copia già scaricata: `bash install-onexplayer.sh` oppure `python3 -m bhs --profilo onexplayer1s`.
Se lo script dedicato gira su un dispositivo diverso, la finestra lo segnala con un avviso (ma non si blocca).

## Come funziona (3 modalità intelligenti)
- **Sul Desktop KDE Plasma 6:** scarica l'app in `~/.local/share/bazzite-handheld-setup`, prepara l'ambiente virtuale isolato `.venv` con PySide6, crea l'icona nel menu Start e sul Desktop e apre subito la finestra grafica Qt6.
- **In Console testuale (`Ctrl+Alt+F3`, es. schermo nero al primo avvio del OneXPlayer 1S):** non serve ricordare `--applica intel_norbc`! Lo script riconosce automaticamente di essere in console senza sessione grafica:
  1. Applica subito la correzione dello schermo nero (`INTEL_DEBUG=norbc` in `~/.config/environment.d/10-gamescope-session.conf`).
  2. Scarica e pre-installa l'app e il `.venv` con PySide6.
  3. Imposta un **Autostart una-tantum** (`~/.config/autostart/bhs-first-run.desktop`) che aprirà da solo la finestra grafica Qt6 non appena l'utente passerà al Desktop KDE Plasma.
  4. Riavvia automaticamente l'handheld dopo 5 secondi (`systemctl reboot`).
- **Dalla Live USB di Bazzite a fine installazione (`/mnt/sysimage`):** se lanciato prima del primo riavvio della chiavetta USB, pre-configura direttamente l'SSD appena installato (`INTEL_DEBUG=norbc` + app + Autostart KDE), evitando del tutto che si verifichi lo schermo nero al primo avvio.
- Gli script dedicati sono **generati** da `install.sh` con `python3 tools/genera_installatori.py`: dopo ogni modifica a `install.sh` va rilanciato (`--verifica` controlla che non si disallineino).
- Non usa `sudo` sul sistema installato. Di norma non installa pacchetti di sistema: solo Flatpak, Homebrew, `ujust`, `steamosctl` e impostazioni KDE (`plasma-apply-colorscheme`, `kscreen-doctor`, `kwriteconfig6`). L'unica eccezione è Mullvad (`rpm-ostree`), facoltativa e in «Avanzate».
- Alcune azioni facoltative chiedono la password di amministratore con `pkexec`: limite di carica (crea un servizio systemd), blocco della versione (`ostree admin pin 0`) e Mullvad.
- Rileva dispositivo, immagine e app già installate; quelle presenti compaiono spuntate e bloccate. Nulla cambia nella finestra grafica finché non premi «Installa» nel riepilogo.

## Strumenti aggiuntivi (tutti facoltativi, nelle «Avanzate» o tra le app)
- **aria2** (app, via Homebrew) e **`aria2_conf`**: scrive `~/.config/aria2/aria2.conf` con i valori della guida Retro Think
  (`aria2c_guida`): FTTC/VDSL di default, `aria2_conf_adsl` e `aria2_conf_ftth` solo da `--applica`. Salva una copia di un file esistente.
- **`mullvad_vpn`**: repository ufficiale + `rpm-ostree install`, **in due tempi** (installa, riavvia, rilancia lo script per attivare il servizio).
  Blocca da sé la versione attuale e controlla il file `.repo` riga per riga prima di darlo a root.

## Guide Passo-Passo Online (`070293.xyz`) e Offline (`guide/`)

Le quattro guide HTML interattive (con pulsanti per copiare i comandi in un clic) sono disponibili sia online su **`https://070293.xyz`** sia offline nella cartella `guide/`:

- **[guide/index.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/index.html)** (`https://070293.xyz/`): Hub iniziale di navigazione per entrambi gli handheld
- **OneXPlayer 1S (8.4" 2560×1600 · Intel i7-1195G7 · Iris Xe)**:
  - **[guide/installazione_onexplayer_1s.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/installazione_onexplayer_1s.html)** (*Parte 1 — Installazione Bazzite KDE*): preparazione di Windows (BitLocker, Avvio Rapido, partizioni), creazione della chiavetta USB con **Rufus**, BIOS/Boot Menu, MOK Secure Boot, sblocco automatico dello schermo nero (`curl -L 070293.xyz/oxp | sh`) e configurazione guidata.
  - **[guide/ottimizzazione_onexplayer_1s.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/ottimizzazione_onexplayer_1s.html)** (*Parte 2 — Ottimizzazione Giochi .exe Locali*): GE-Proton con ProtonUp-Qt, aggiunta degli `.exe` a Steam, Scaling per Interi 2:1 (1280×800 nitido) e script automatici per *Red Dead Redemption 2*, *The Witcher 3 Remastered* (DX11) e *Skyrim Special Edition*.
- **ASUS ROG Ally (7" 1080p 120Hz VRR · Ryzen Z1 Extreme · Radeon 780M)**:
  - **[guide/installazione_rog_ally.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/installazione_rog_ally.html)** (*Parte 1 — Installazione Bazzite KDE*): preparazione di Windows (BIOS/MCU, BitLocker, `powercfg /h off` per il Wi-Fi MediaTek), chiavetta USB con **Rufus**, VRAM 4G/6G, *Boot Override*, 120Hz FreeSync VRR, doppio cursore audio e avvio con `curl -L 070293.xyz/ally | sh`.
  - **[guide/ottimizzazione_rog_ally.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/ottimizzazione_rog_ally.html)** (*Parte 2 — Ottimizzazione Giochi .exe Locali*): GE-Proton, aggiunta degli `.exe` a Steam, display 120Hz VRR + risoluzione 900p (1600×900) e script automatici per *Red Dead Redemption 2*, *The Witcher 3 Remastered* e *Skyrim Special Edition* (fisica Havok 120Hz).

## Stato (v0.6.0)
Fatto e provato con test (61): rilevamento, profili, profilo fisso, installatori (inclusi modalità console automatica e pre-configurazione Live USB `/mnt/sysimage`), tweak KDE Plasma 6 ed esecuzione con simulazione (`python -I -m unittest discover -s tests`). Gli installatori dedicati sono verificati con `tools/genera_installatori.py --verifica`.
Pubblicato su GitHub (`dilfal/bazzite-handheld-setup`) e servito con scorciatoie e guide online su `https://070293.xyz`.
