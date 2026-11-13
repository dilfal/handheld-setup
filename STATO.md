# STATO: Bazzite Handheld Setup (v0.7.0)

Aggiornato il 13 novembre 2026. **La v0.7.0 è in un commit, su GitHub e sul sito**: resta solo da provarla sui dispositivi.

## Fatto
- **Guide ai giochi** (commit `80da79b` su `dilfal/handheld-setup`, ramo `main`): pulsante «Guide ai giochi» nell'app, un passo per schermata, passo ricordato alla riapertura. Tre giochi (Red Dead Redemption 2, The Witcher 3, Skyrim Special Edition), valori diversi per OneXPlayer 1S, ROG Ally e profilo generico.
- **Impostazioni automatiche**: «Applica» cambia solo le chiavi elencate nel file del gioco (`system.xml`, `user.settings`/`dx12user.settings`, `SkyrimPrefs.ini`), con copia `<file>.bhs-originale` e «Ripristina».
- **Riga di comando**: `--guide`, `--guida GIOCO`, `--imposta-gioco GIOCO` (anche con `--dry-run`), `--ripristina-gioco GIOCO`.
- **Sito pubblicato** (commit `23768b8` su `dilfal/070293`, con `python tools/pubblica_070293.py`): script e scorciatoie `/oxp`, `/ally`, `/bhs` aggiornati, guide rigenerate, indirizzi brevi nuovi `070293.xyz/giochi-oxp` e `070293.xyz/giochi-ally`.
- **Controlli prima del commit**: `tools/genera_guide.py --verifica` e `tools/genera_installatori.py --verifica` a 0. I test (183 verdi su Windows e in Fedora 44 WSL) sono quelli della sessione precedente, non rilanciati.

## Decisioni prese
- Fonti dei valori: guida ufficiale ASUS per RDR2 sulla Ally (1080p, FSR 2 Qualità); impostazioni per Steam Deck come base di RDR2 sul OneXPlayer; chiavi e intervalli controllati su file reali e sul parser `Forceflow/rdr2_settings_parser`.
- The Witcher 3 si avvia dall'eseguibile DirectX 11 (`bin/x64/witcher3.exe`); il programma scrive solo risoluzione, HairWorks, sfocatura e sincronia verticale.
- Skyrim resta a 60 fotogrammi anche sulla Ally (oltre, la fisica si rompe).
- Il profilo generico eredita la qualità del OneXPlayer ma non la risoluzione.
- `OneDrive_2026-11-13/` (archivi dei driver, 1,4 GB) è in `.gitignore`: i driver stanno nelle Release di `onexplayer-1s-drivers`.

## Non verificato (serve il dispositivo: elenco in `PROSSIMI_PASSI.md`, sezione 4.F)
- Nessuna guida è stata provata con i giochi veri: che i file vengano trovati, che i giochi accettino i valori scritti, i nomi italiani delle voci nei menu.
- Gli obiettivi di FPS sono stime (quello di The Witcher 3 sulla Ally non ha una fonte).
- Quali copie partono come «gioco non di Steam»: RDR2 fuori da Steam richiede il Rockstar Games Launcher.
- Dove si regolano TDP e VRR sulla Ally; «Risoluzione di gioco» e scalatura intera in Gaming Mode sul OneXPlayer.
- Il comando `curl -L 070293.xyz/oxp | sh` da zero su Bazzite con la versione nuova.

## Manca
- Prove sui due dispositivi (sezioni 4.A-4.F di `PROSSIMI_PASSI.md`).

## Prossimo passo
- Prima prova vera: RDR2 sul OneXPlayer, seguendo la guida dall'app. Prima `python3 -m bhs --imposta-gioco rdr2 --dry-run`, poi «Applica», poi il gioco; annotare gli esiti in 4.F e incollarli a Claude.
