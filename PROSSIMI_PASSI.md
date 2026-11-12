# Bazzite Handheld Setup: appunti per quando avrai gli handheld

Aggiornato il 12 novembre 2026. Versione dell'app: 0.6.0 (KDE Plasma 6 + Pubblicazione su `dilfal/bazzite-handheld-setup` e `070293.xyz`).

## 1. Cosa abbiamo deciso

| Tema | Scelta |
|---|---|
| Ambiente Desktop | **KDE Plasma 6** su entrambi i dispositivi (`bazzite-deck` per OneXPlayer 1S, `bazzite-ally` per ROG Ally) |
| Interfaccia | Python + Qt 6 / PySide6 (nativa per KDE Plasma 6), procedura guidata a pagine, elementi spaziosi per il touch |
| Dispositivi | Due profili dedicati: **OneXPlayer 1S** (8,4", i7-1195G7, 16 GB, SSD 1 TB) e **ASUS ROG Ally Z1 Extreme**, più un profilo generico |
| Funzioni | App e giochi, emulazione e Decky, tweak di sistema e batteria, comfort visivo (Breeze Dark, fractional scaling Wayland, tastiera Maliit) |
| Avvio | **Due script separati**, uno per dispositivo (`install-onexplayer.sh`, `install-rog-ally.sh`), da incollare nel terminale (`curl … \| bash`) da un repository GitHub pubblico; più `install.sh` generico. Condividono lo stesso codice |
| Lingua | Solo italiano |
| App già installate | Mostrate spuntate e bloccate; l'elenco propone quelle che mancano |
| `rpm-ostree` | Solo in una sezione «Avanzate» (per ora non usato tranne per Mullvad facoltativo) |
| Prove | Scrivo il codice io, lo provi tu sull'handheld |
| Sicurezza | Niente `sudo` nascosto, nulla cambia prima del riepilogo, `--dry-run` per simulare |

## 2. Struttura (in `C:\Users\df\Dev\Scripts\bazzite-handheld-setup`)

```
install.sh              installatore generico (sorgente degli altri due)
install-onexplayer.sh   dedicato al OneXPlayer 1S (GENERATO: non modificarlo a mano)
install-rog-ally.sh     dedicato alla ROG Ally (GENERATO)
tools/genera_installatori.py  rigenera i due dedicati da install.sh (--verifica per controllare)
bhs/detect.py           rilevamento sistema, dispositivo, strumenti KDE, flatpak
bhs/profiles.py         profili da data/profiles/*.toml
bhs/catalog.py          catalogo app da data/catalog.toml (22 voci, 4 categorie)
bhs/tweaks.py           13 tweak (KDE Plasma 6 + hardware + sistema)
bhs/piano.py            dalla selezione all'elenco ordinato di azioni (Flathub utente, ordine dei tweak)
bhs/runner.py           esecuzione con --dry-run e log
bhs/cli.py              modalità senza interfaccia: --elenco, --applica
bhs/gui.py              finestra Qt6 / PySide6 nativa
tools/fumo_gui.py       prova automatica della finestra con screenshot offscreen (PySide6)
tests/test_core.py      57 test della logica (tutti verdi)
guide/index.html                         hub delle guide passo-passo offline
guide/installazione_onexplayer_1s.html   guida passo-passo installazione Bazzite KDE (Rufus, BIOS, fix schermo nero) su OneXPlayer 1S
guide/ottimizzazione_onexplayer_1s.html  guida passo-passo ottimizzazione giochi .exe (RDR2, Witcher 3, Skyrim) su OneXPlayer 1S
guide/installazione_rog_ally.html        guida passo-passo installazione Bazzite KDE (Rufus, BIOS VRAM, VRR) su ROG Ally
guide/ottimizzazione_rog_ally.html       guida passo-passo ottimizzazione giochi .exe (RDR2, Witcher 3, Skyrim) su ROG Ally
```

Tweak: `tema_scuro` (Breeze Dark), `scala_display_125`, `scala_display_150`, `tastiera_schermo` (Maliit Wayland), `limite_carica_80`, `intel_norbc`, e (avanzati, nell'ordine in cui vengono eseguiti) `luminosita_game_mode`, `blocca_versione`, `aria2_conf` (+ `_adsl`, `_ftth` solo da `--applica`), `mullvad_vpn`, `aggiorna_sistema`.

## 3. Guida di riferimento: OneXPlayer 1S & ROG Ally su Bazzite KDE

File: `C:\Users\df\Dev\GitHub\siti-web\retrothink\bazzite_onexplayer_1s\index.html` (7 novembre 2026, scritta dopo un'installazione reale). Da lì ho preso, **verificato sul dispositivo**:

- Nome DMI: `product_name` = `ONE XPLAYER`. Il modello è quindi il **1S**: il profilo è stato rinominato.
- Immagine ufficiale: `bazzite-deck` (KDE Plasma 6). Il Game Mode **funziona** sull'Iris Xe con la correzione.
- **Schermo nero in Game Mode:** correzione `INTEL_DEBUG=norbc` nel file `~/.config/environment.d/10-gamescope-session.conf`, senza root. Implementata nel tweak `intel_norbc` e disponibile da console: `python3 -m bhs --applica intel_norbc`.
- **«Passa al desktop»:** su Bazzite KDE la sessione desktop di default per SteamOS è già KDE Plasma (`plasma.desktop`), non serve la correzione che serviva per GNOME.
- Aggiornamento: `ujust update` (le immagini Deck non si aggiornano da sole). Blocco della versione: `sudo ostree admin pin 0`. Implementati come tweak avanzati.
- **Controlli:** li gestisce InputPlumber, non hhd. Quindi i dubbi su hhd valgono solo per la ROG Ally.
- Ventola: nessuna curva personalizzata sul 1S Intel. Crash della Iris Xe: opzione Steam `INTEL_DEBUG=stall %command%` (non confermata).

### ROG Ally Z1 Extreme
- Immagine ufficiale: `bazzite-ally` (KDE Plasma 6 con kernel e driver ROG integrati).
- Limite di carica all'80%: consigliato ovunque.

## 4. Lista di prova sull'handheld

Per ogni dispositivo, nell'ordine. Annota l'esito accanto a ogni riga.

### A. Prima di tutto: diagnosi (non modifica nulla)
0. Usa lo script del tuo dispositivo: `install-onexplayer.sh` o `install-rog-ally.sh` (stessi comandi sotto, con `bash install-….sh --diagnosi` al posto di `python3 -m bhs --diagnosi`).
1. `python3 -m bhs --diagnosi` e **incolla l'output a Claude**.
2. `python3 -m bhs --elenco`: controlla gli stati («già attivo», «non supportato qui»).
3. In più, a mano:
   - `rpm-ostree status | head -20` (immagine esatta)
   - `ls /sys/class/power_supply/*/charge_control_end_threshold`
   - `command -v hhd steamosctl asusctl`

### B. Interfaccia
- [ ] `python3 -m bhs --dry-run` si apre (altrimenti copia l'errore)
- [ ] Il titolo mostra il nome giusto del dispositivo e **non** compare l'avviso di dispositivo diverso (se compare, copia la diagnosi: le stringhe DMI vanno corrette)
- [ ] Le righe si toccano bene col dito; «Indietro» e «Avanti» sono raggiungibili
- [ ] Navigazione col gamepad: funziona?
- [ ] Il testo è leggibile; nulla è tagliato; la finestra sta nello schermo (anche in verticale)
- [ ] Il riepilogo elenca i comandi giusti; in simulazione non cambia nulla
- [ ] Il pannello «Avanzate» si apre e le righe si possono attivare (non provato nemmeno in WSL)

### C. Esecuzione reale (dopo aver letto il riepilogo)
- [ ] Una sola app Flatpak a scelta si installa
- [ ] Tema scuro (Breeze Dark), scala display (kscreen-doctor) e tastiera su schermo (Maliit) si applicano
- [ ] `ujust setup-decky`: funziona senza input? (usa `stdin` vuoto: potrebbe chiedere conferme)
- [ ] `ujust update` dall'interfaccia: finisce senza chiedere nulla?
- [ ] Il comando `curl … | bash` da zero (dopo la pubblicazione su GitHub)

### D. Solo OneXPlayer 1S
- [ ] **Con lo schermo nero**, da console (Ctrl+Alt+F3): `curl -fsSL …/install.sh | bash -s -- --applica intel_norbc` funziona? (serve la rete: Wi-Fi o cavo)
- [ ] Dopo il riavvio il Game Mode compare sullo schermo interno, nel verso giusto
- [ ] «Passa al desktop» dal menu di Steam: apre la sessione KDE Plasma senza problemi
- [ ] **Luminosità in Game Mode** (cursore assente; in KDE funziona). Causa trovata l'11 novembre nel sorgente di `gamescope-session` (ChimeraOS): `device-quirks` mette `ONE XPLAYER` tra i dispositivi con `PANEL_TYPE=external`, e Steam non mostra il cursore su uno schermo «esterno». Prima `python3 -m bhs --diagnosi` (righe «Luminosità» e «Pannello»: il quirk deve dire `external`), poi `python3 -m bhs --applica luminosita_game_mode` e riavvio. Controlla: il cursore compare e regola davvero; lo schermo resta nel verso giusto (con `internal` entra in gioco `ORIENTATION=left` del quirk). Per annullare: `sed -i '/^PANEL_TYPE=/d' ~/.config/environment.d/10-gamescope-session.conf` e riavvio. La copia del file su Bazzite può differire da quella di ChimeraOS: mai provata sul dispositivo
- [ ] I tasti e il controller funzionano (InputPlumber)

### E. Solo ROG Ally
- [ ] hhd è presente? (`command -v hhd`)
- [ ] TDP: dove si cambia (menu rapido di Steam in Game Mode)? Funziona in Desktop Mode?
- [ ] Il limite di carica è esposto dal kernel? Dopo `limite_carica_80` e un **riavvio**: `cat /sys/class/power_supply/BAT0/charge_control_end_threshold` dà 80? `systemctl status bhs-limite-carica.service`

## 5. Fatto finora

- ✅ Tutti i 21 ID Flatpak esistono su Flathub. Resta «da verificare» solo EmuDeck (link manuale).
- ✅ Limite di carica all'80% con `pkexec` e servizio systemd, con percorsi sysfs validati. Testato solo come generazione dello script, mai eseguito: segnalazioni dicono che su alcune immagini il valore tornava a 100 al riavvio ([#3855](https://github.com/ublue-os/bazzite/issues/3855)).
- ✅ Rilevamento DMI anche da `board_vendor`/`board_name`; profilo 1S verificato con la guida; la Ally X non prende il profilo Z1.
- ✅ **Modalità da console** (`--elenco`, `--applica`), provata in Fedora 44 (WSL): applica la correzione, non duplica la riga se rilanciata, dà i codici di uscita giusti.
- ✅ **Finestra provata in WSL2** (Fedora 44, GTK 4.22, libadwaita 1.9, WSLg) con `tools/fumo_gui.py`: apre e naviga tutte le pagine in simulazione, per ROG Ally (1280×800) e OneXPlayer (800×1200 verticale). Rilancio: `wsl -d FedoraLinux-44 -- python3 -I tools/fumo_gui.py oxp 800 1280 /tmp/shots`.
- ✅ **Due installatori dedicati** (v0.3.0): `--profilo` fissa il profilo, nasconde la scelta manuale e avvisa se il dispositivo non corrisponde. Provati da copia locale in Fedora 44 (WSL, utente normale): creano due voci di menu distinte con il comando giusto. Il download da GitHub resta da provare dopo la pubblicazione.
- Test: 48, tutti verdi (aggiornati nella sezione 5b).

**Resta non provato:** touch vero, gamepad, rotazione dello schermo, GNOME di Bazzite (WSLg non è GNOME), esecuzione reale dei comandi su Bazzite (flatpak, ujust, steamosctl, pkexec).

## 5b. Novità del 10 novembre (sera): installatore, aria2, Mullvad

**Installatore** (`install.sh` e i due dedicati), provato in Fedora 44 (WSL) con un server locale al posto di GitHub: ramo di download, errori e ripristino.
- Corretto un difetto vero: a ogni esecuzione restava in `/tmp` una cartella con l'archivio (il `trap` non scattava dopo `exec`).
- Sostituzione dell'installazione in due tempi: se download o archivio sono rotti, la versione già installata resta intatta (provato con 404 e archivio danneggiato).
- `curl` con tentativi e timeout; controllo di Python 3.11+; da console senza sessione grafica il messaggio indica `--elenco` e `--applica`; colori solo su terminale.
- `BHS_URL` per specchi o prove; consigliato `BHS_REF` con un tag per risultati ripetibili.

**aria2** (guida `retrothink/posts/aria2c_guida.md`): app via Homebrew (`brew install aria2`, come la sezione 2.5 della guida; se Homebrew manca la finestra lo dice)
e tweak `aria2_conf`. **Provato con aria2 1.37.0 vero in Fedora:** il file generato viene accettato senza opzioni sconosciute, il download di prova è identico all'originale, la copia di
sicurezza viene creata. L'allocazione sceglie `falloc` su ext4/btrfs/xfs/f2fs e `none` altrove (verificato sui nomi di `stat -f`; btrfs non provato su un disco vero).

**Mullvad VPN** (guida OneXPlayer 1S, §7.6): tweak `mullvad_vpn`, in due tempi.
1. Prima fase: scarica il `.repo` come utente, poi **un solo** passaggio di password per root: copia il file, lo controlla riga per riga, blocca la versione (`ostree admin pin 0`), installa il repository e `rpm-ostree install mullvad-vpn`.
2. Riavvio (la finestra lo propone con «Riavvia ora»).
3. Seconda fase: rilanciando lo script il tweak risulta «installato: manca da attivare il servizio» e fa `systemctl enable --now mullvad-daemon.service`.
**Provato:** la validazione accetta il file ufficiale scaricato in quel momento e rifiuta baseurl diverso, `gpgcheck=0`, righe in più, `http`, file vuoto, dominio simile.
**Non provato:** l'installazione vera con `rpm-ostree` (serve Bazzite).

Altre migliorie: Flathub collegato per l'utente prima dei Flatpak (senza, `flatpak install --user flathub …` poteva fallire); ordine dei tweak deterministico (blocco versione prima, aggiornamento per ultimo);
pulsante «Riavvia ora» con conferma; riepilogo con una riga per comando.
**Non fatto** (idee): file di log dell'ultima esecuzione e blocco della chiusura della finestra durante l'installazione.

### Prove da fare sull'handheld per queste novità
- [ ] Homebrew presente (`brew --version`)? Se sì, `aria2` compare installabile; dopo l'installazione `aria2c --version`
- [ ] `aria2_conf`: `cat ~/.config/aria2/aria2.conf` ha `dir=` giusta e `file-allocation=falloc` (Bazzite usa btrfs); `aria2c URL` scarica con `CN:8`
- [ ] Mullvad, prima fase: una sola richiesta di password; poi `rpm-ostree status` mostra `LayeredPackages: mullvad-vpn` e la voce passa a «in attesa del riavvio»
- [ ] Dopo il riavvio e il rilancio, la voce dice «manca da attivare il servizio»; attivata, `systemctl is-enabled mullvad-daemon.service` risponde `enabled`
- [ ] Si apre l'app Mullvad VPN, inserisci il numero di account, la VPN si connette (anche in Gaming Mode: da verificare)
- [ ] Il Flatpak si installa dopo «Collega Flathub (utente)»; il pulsante «Riavvia ora» chiede conferma e riavvia davvero

## 6. Da completare / idee dalla guida

- [ ] `limite_carica_80`: manca il modo di disattivarlo; da provare con riavvio
- [ ] Verificare EmuDeck (link manuale)
- [x] Pubblicare il repository (`dilfal/bazzite-handheld-setup`) e attivare le scorciatoie e guide su `070293.xyz` (`curl -L 070293.xyz/oxp | sh` e `curl -L 070293.xyz/ally | sh`)
- [ ] Gestione di Decky e dei suoi plugin (CSS Loader, SimpleDeckyTDP, ecc.)
- [ ] TDP sul 1S Intel: la guida non ha trovato nulla; da esplorare dopo le prove (una sola strada alla volta: menu Steam, OpenGamepadUI/PowerStation o Decky)
- Idee dalla guida non ancora fatte (chiedi se le vuoi):
  - **Sincronizzazione Google Drive con rclone** (bisync, timer systemd): richiede un client id Google creato a mano, quindi solo in parte automatizzabile.
  - Dopo l'installazione di **Heroic**: avviarlo una volta in Desktop Mode e aggiungere i giochi a Steam (passaggi manuali, solo come istruzioni).
  - Visual novel Ren'Py: build Linux nativa aggiunta a Steam (solo istruzioni).

## 7. Comandi utili

```bash
python3 -m bhs --diagnosi                      # rapporto di sistema
python3 -m bhs --elenco                        # tweak e loro stato
python3 -m bhs --applica intel_norbc           # senza interfaccia (anche da console)
python3 -m bhs --profilo onexplayer1s --dry-run   # come lo script dedicato (anche: rogallyz1x)
python3 -m bhs --dry-run                       # interfaccia in simulazione
python3 -m bhs                                 # interfaccia vera
python3 -I -m unittest discover -s tests       # test della logica
python3 tools/genera_installatori.py           # rigenera i due script dedicati dopo aver toccato install.sh
```
