# Handheld Setup (Bazzite e Windows)

Repository unico per gli handheld, `dilfal/handheld-setup` (prima `bazzite-handheld-setup`, con `onexplayer-1s-drivers` fuso dal 13 novembre 2026). Contiene due strumenti separati:

- **Bazzite (Linux)**: alla radice del repository, descritto in questo file.
- **Windows 11 (OneXPlayer 1S)**: cartella [`windows/`](windows/README.md), utility WPF per driver, programmi di gioco, schermo e touch. Avvio: `irm 070293.xyz/oxp-win | iex`.

## Bazzite

Configurazione guidata, con interfaccia nativa Qt6 (PySide6), da lanciare dopo l'installazione di **Bazzite (KDE Plasma 6) per handheld**.
Due script separati, uno per dispositivo, che condividono lo stesso codice:

| Dispositivo | Scorciatoia | Script | Profilo | Immagine Bazzite raccomandata |
|---|---|---|---|---|
| OneXPlayer 1S (8,4", i7-1195G7) | `070293.xyz/oxp` | `install-onexplayer.sh` | `onexplayer1s` | `bazzite-deck` (KDE Plasma 6) |
| ASUS ROG Ally (Z1 Extreme) | `070293.xyz/ally` | `install-rog-ally.sh` | `rogallyz1x` | `bazzite-deck` (KDE Plasma 6) |
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

Indirizzo completo dal repository GitHub (`dilfal/handheld-setup`):
```bash
# OneXPlayer 1S
curl -fsSL https://raw.githubusercontent.com/dilfal/handheld-setup/main/install-onexplayer.sh | bash
# ROG Ally
curl -fsSL https://raw.githubusercontent.com/dilfal/handheld-setup/main/install-rog-ally.sh | bash
```

Opzioni manuali (dopo `sh -s --` o `bash -s --`): `--dry-run` (solo simulazione), `--diagnosi` (rapporto di sistema), `--elenco` (tweak e stato),
`--applica ID...` (applica solo quei tweak, senza interfaccia). Le opzioni per le guide ai giochi (`--guide`, `--guida`, `--imposta-gioco`, `--ripristina-gioco`) sono descritte nella sezione «Guide ai giochi».

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
- Alcune azioni facoltative chiedono la password di amministratore con `pkexec`: limite di carica (crea un servizio systemd e una regola udev), profili TDP Intel (servizio systemd), blocco della versione (`ostree admin pin 0`) e Mullvad.
- Rileva dispositivo, immagine e app già installate; quelle presenti compaiono spuntate e bloccate. Nulla cambia nella finestra grafica finché non premi «Installa» nel riepilogo.

## Guide ai giochi

L'app contiene una guida passo passo per tre giochi: *Red Dead Redemption 2*, *The Witcher 3* e *Skyrim Special Edition*. Si apre con il pulsante «Guide ai giochi» nella schermata di benvenuto e a fine installazione. Ogni schermata mostra un solo passo, con elementi grandi per il touch, e la guida ricorda il passo a cui eri arrivato. Passi e valori cambiano secondo il profilo: OneXPlayer 1S, ROG Ally o generico.

**Impostazioni automatiche.** A metà guida il pulsante «Applica» scrive le impostazioni grafiche nel file del gioco (per esempio `system.xml` per RDR2). Cambia solo le chiavi elencate nella guida (per The Witcher 3 e Skyrim anche la risoluzione); comandi e salvataggi non vengono toccati. Prima della prima modifica salva una copia accanto al file (`<file>.bhs-originale`) e «Ripristina» la rimette. Nei file XML non si aggiungono chiavi che il gioco non ha scritto: se una voce manca, la guida dice di impostarla a mano dal menu del gioco. Il file viene trovato solo dopo aver avviato il gioco una volta fino al menu.

**Da riga di comando** (anche dagli script di installazione, senza finestra):

```bash
python3 -m bhs --guide                          # apre la finestra direttamente sulle guide
python3 -m bhs --guida rdr2                     # stampa la guida di un gioco (rdr2, witcher3, skyrim)
python3 -m bhs --imposta-gioco rdr2 --dry-run   # mostra cosa cambierebbe, senza scrivere
python3 -m bhs --imposta-gioco rdr2             # scrive le impostazioni nel file del gioco
python3 -m bhs --ripristina-gioco rdr2          # rimette il file com'era
curl -L 070293.xyz/oxp | sh -s -- --imposta-gioco rdr2   # lo stesso, con lo script di installazione
```

`--guida`, `--imposta-gioco` e `--ripristina-gioco` non aprono la finestra e, in console senza sessione grafica, non fanno partire la modalità console automatica; `--guide`, invece, apre la finestra.

**Dove stanno i dati.** I contenuti sono in `data/giochi/*.toml`, un file per gioco; `_comune.toml` contiene i passi uguali per tutti. Le sezioni dei giochi nelle due guide web (`guide/ottimizzazione_*.html`) si rigenerano dagli stessi file con `python3 tools/genera_guide.py` (`--verifica` controlla che non si disallineino).

**Dal telefono.** Le due guide web hanno scorciatoie dedicate: `070293.xyz/giochi-oxp` (OneXPlayer 1S) e `070293.xyz/giochi-ally` (ROG Ally). Esisteranno dopo la prossima pubblicazione del sito.

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
  - **[guide/ottimizzazione_onexplayer_1s.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/ottimizzazione_onexplayer_1s.html)** (*Parte 2 — Ottimizzazione Giochi .exe Locali*): GE-Proton con ProtonUp-Qt, aggiunta degli `.exe` a Steam, scalatura intera a 1280×800 e una guida passo-passo, generata dagli stessi dati dell'app, per *Red Dead Redemption 2*, *The Witcher 3* (DirectX 11) e *Skyrim Special Edition*.
- **ASUS ROG Ally (7" 1080p 120Hz VRR · Ryzen Z1 Extreme · Radeon 780M)**:
  - **[guide/installazione_rog_ally.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/installazione_rog_ally.html)** (*Parte 1 — Installazione Bazzite KDE*): preparazione di Windows (BIOS/MCU, BitLocker, `powercfg /h off` per il Wi-Fi MediaTek), chiavetta USB con **Rufus**, VRAM 4G/6G, *Boot Override*, 120Hz FreeSync VRR, doppio cursore audio e avvio con `curl -L 070293.xyz/ally | sh`.
  - **[guide/ottimizzazione_rog_ally.html](file:///C:/Users/df/Dev/Scripts/bazzite-handheld-setup/guide/ottimizzazione_rog_ally.html)** (*Parte 2 — Ottimizzazione Giochi .exe Locali*): GE-Proton, aggiunta degli `.exe` a Steam, 1080p con VRR (e FSR 2 per RDR2) e una guida passo-passo, generata dagli stessi dati dell'app, per *Red Dead Redemption 2*, *The Witcher 3* (DirectX 11) e *Skyrim Special Edition*.

## Stato (v0.7.0)
Fatto e provato con test (144, di cui 8 saltati su Windows per mancanza di una shell POSIX o dei collegamenti simbolici; in Fedora WSL girano tutti e 144): rilevamento, profili, profilo fisso, installatori (inclusi modalità console automatica, opzioni senza interfaccia e pre-configurazione Live USB `/mnt/sysimage`), tweak KDE Plasma 6, guide ai giochi (dati, scrittura e ripristino dei file di impostazioni, pagine web) ed esecuzione con simulazione (`python -I -m unittest discover -s tests`). Gli installatori dedicati sono verificati con `tools/genera_installatori.py --verifica`, le guide web con `tools/genera_guide.py --verifica`.
Le guide ai giochi non sono ancora state provate con i giochi veri (vedi `PROSSIMI_PASSI.md`, sezione 4).
Pubblicato su GitHub (`dilfal/handheld-setup`) e servito con scorciatoie e guide online su `https://070293.xyz`.
