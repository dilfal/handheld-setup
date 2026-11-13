# STATO: Bazzite Handheld Setup (v0.7.0)

Aggiornato il 13 novembre 2026. **Niente di questo blocco è in un commit né pubblicato**: è tutto nella copia di lavoro.

## Fatto in questa sessione: «Guide ai giochi»
- **Nell'app**: pulsante «Guide ai giochi» (benvenuto e fine installazione), un passo per schermata, la guida ricorda il passo a cui si era arrivati. Tre giochi (Red Dead Redemption 2, The Witcher 3, Skyrim Special Edition), passi e valori diversi per OneXPlayer 1S, ROG Ally e profilo generico.
- **Impostazioni automatiche**: «Applica» cambia solo le chiavi elencate nel file del gioco (`system.xml`, `user.settings`/`dx12user.settings`, `SkyrimPrefs.ini`), con copia `<file>.bhs-originale` e «Ripristina». Scritture atomiche, codifica e fine riga conservati, file di sola lettura rispettati, nei file XML non si aggiungono chiavi.
- **Riga di comando**: `--guide`, `--guida GIOCO`, `--imposta-gioco GIOCO` (anche con `--dry-run`), `--ripristina-gioco GIOCO`.
- **Sito**: le sezioni dei tre giochi delle due pagine `guide/ottimizzazione_*.html` sono generate dagli stessi dati dell'app (`python3 tools/genera_guide.py`, controllo con `--verifica`). Tolti i vecchi script «bash -c», che scrivevano nei file dei giochi chiavi inesistenti.
- **Installatore**: le opzioni senza finestra non fanno più partire la modalità console automatica (che sul OneXPlayer riavvia) e non rompono l'icona dell'app.
- **File nuovi**: `bhs/giochi.py`, `bhs/gui_guide.py`, `data/giochi/` (`_comune.toml` + un file per gioco), `tools/genera_guide.py`, `tests/test_guide_web.py`.
- **Test**: 183 verdi su Windows (13 saltati: servono `sh` o i collegamenti simbolici) e 183 in Fedora 44 WSL (3 saltati: da root la sola lettura non vale). Le due `--verifica` a 0, `tools/fumo_gui.py` senza errori per `oxp` e `ally`.

## Decisioni prese
- Fonti dei valori: guida ufficiale ASUS per RDR2 sulla Ally (1080p, FSR 2 Qualità); impostazioni per Steam Deck come base di RDR2 sul OneXPlayer; chiavi e intervalli controllati su file reali e sul parser `Forceflow/rdr2_settings_parser`.
- The Witcher 3 si avvia dall'eseguibile DirectX 11 (`bin/x64/witcher3.exe`); la qualità si sceglie dai preset del gioco, il programma scrive solo risoluzione, HairWorks, sfocatura e sincronia verticale.
- Skyrim resta a 60 fotogrammi anche sulla Ally (oltre, la fisica si rompe).
- Il profilo generico eredita la qualità del OneXPlayer ma non la risoluzione.
- Regola sui modelli scritta in `~\.claude\CLAUDE.md`: Fable decide, Opus rivede (una volta), Sonnet esegue.

## Non verificato (serve il dispositivo: elenco in `PROSSIMI_PASSI.md`, sezione 4.F)
- Nessuna guida è stata provata con i giochi veri: che i file vengano trovati, che i giochi accettino i valori scritti, i nomi italiani delle voci nei menu.
- Gli obiettivi di FPS sono stime (quello di The Witcher 3 sulla Ally non ha una fonte).
- Quali copie partono come «gioco non di Steam»: RDR2 fuori da Steam richiede il Rockstar Games Launcher.
- Dove si regolano TDP e VRR sulla Ally (menu di Steam o Handheld Daemon); «Risoluzione di gioco» e scalatura intera in Gaming Mode sul OneXPlayer.

## Manca
- Commit e push su `dilfal/bazzite-handheld-setup`.
- Pubblicazione del sito con `python tools/pubblica_070293.py`: solo dopo esistono `070293.xyz/giochi-oxp` e `/giochi-ally` (che l'app già cita) e i comandi `curl … | sh -s -- --imposta-gioco` delle pagine.
- Prove sui due dispositivi (sezioni 4.A-4.F).

## Prossimo passo
- Commit, push e pubblicazione; poi la prima prova vera: RDR2 sul OneXPlayer, seguendo la guida dall'app.
