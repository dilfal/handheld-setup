# STATO: Handheld Setup (repository unico `dilfal/handheld-setup`)

Aggiornato il 14 novembre 2026. Bazzite alla radice (v0.7.0), utility Windows in `windows/` (v1.0.0).

## Fatto in questo blocco: voci reali di Winhanced nelle guide di ottimizzazione
- **Fonte**: installer Winhanced 1.0.0.6 (beta dell'11 novembre 2026, `ota.winhanced.com`), aperto con 7-Zip **senza eseguirlo né installarlo**; 4834 testi dell'interfaccia in italiano. Installer e file estratti già cancellati; sul PC Winhanced non è mai stato installato.
- **Decisione dell'utente**: niente installazione sul ThinkPad e niente schermate nelle guide (l'installazione metterebbe RTSS, il driver di kernel PawnIO, il servizio `WHService`, attività pianificate con privilegi alti e un certificato tra gli attendibili).
- **Correzioni, solo variante Windows** (`data/giochi/_comune.toml`, `rdr2.toml`, `skyrim.toml`, `witcher3.toml`; sezioni 1 e «problemi» scritte a mano nelle due pagine `guide/ottimizzazione_*.html`):
  - «pannello di Winhanced» → «HUD di Winhanced» (widget «Winhanced HUD» della Xbox Game Bar); si apre con Select + Start, Win+G resta come alternativa da tastiera; sul ROG Ally anche il tasto Armoury Crate, se è attiva la riassegnazione dei pulsanti hardware.
  - «Limite dei fotogrammi» → «Limite FPS»; «Nessun limite» → «FPS illimitati»; «Potenza (TDP)» → «TDP (watt)»; «Risoluzione» → «Risoluzione nel gioco».
  - Prima della potenza: «Attiva il controllo del dispositivo di Winhanced» (nelle impostazioni di Winhanced).
  - Profili: interruttore «Usa profilo per gioco»; tre profili per gioco («Collegato», «Batteria», «eGPU»); i valori a caricatore vanno in «Collegato», quelli a batteria in «Batteria».
  - RTSS: Winhanced lo installa e lo usa da sé, non va chiuso né disinstallato; se il «Limite FPS» non ha effetto si usa il limite del gioco.
- **Controlli**: `genera_guide.py --verifica` 0; `python -m unittest discover -s tests` 191 test OK, 13 saltati (`python -m unittest` da solo trova 0 test); una revisione Opus fatta (quattro frasi riformulate, variante Bazzite intatta).

- **Pubblicato** (con il sì dell'utente): commit `3124fac` qui; `python tools/pubblica_guide.py` (0, 7 pagine) e commit `4facbee` in `siti-web\guide.070293.xyz`; `python tools/pubblica_070293.py` (0) e commit `c554f45` in `siti-web\070293` (guide sia nella radice sia in `guide/`). I tre push sono andati a buon fine.

## Da fare
- Sul OneXPlayer 1S la regolazione della potenza da Winhanced resta «non provata»: nel codice c'è il riconoscimento «ONEXPLAYER», ma nessun testo dice che il TDP si regoli. Serve la prova sul dispositivo.
- Non verificati a schermo: ordine e nomi delle schede di Winhanced, valori disponibili (risoluzioni, Hz), se il widget va prima messo nello «slot dispositivo» della Game Bar. Si chiariscono con schermate fatte sull'handheld.
- Facoltativo: link a `guide.070293.xyz` dalla homepage di `070293.xyz`.
- Prove sui dispositivi: `PROSSIMI_PASSI.md` (Bazzite) e `windows/ISTRUZIONI.md` (Windows).

## Regola per i testi su Winhanced
Nomi delle voci tra «» esattamente come nell'interfaccia italiana; niente nomi di schede o percorsi di menu non visti a schermo.

## Come aggiungere una guida al sottodominio
1. Mettere il file `.html` in `guide/sottodominio/` (nome senza spazi).
2. Aggiungere la sua scheda in `guide/sottodominio/index.html`.
3. `python tools/pubblica_guide.py`, poi commit e push in `siti-web\guide.070293.xyz`.

## Note
- `desktop.ini` ricompare dentro `.git` e rompe fetch/merge: `find .git -iname desktop.ini -delete`.
- Push con il token di `dilfal` (memoria `push-github-account-dilfal`, nella cartella di memoria con il vecchio nome `bazzite-handheld-setup`); nel nuovo repository l'autore git locale è `dilfal`.
