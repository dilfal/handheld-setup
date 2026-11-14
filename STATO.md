# STATO: Handheld Setup (repository unico `dilfal/handheld-setup`)

Aggiornato il 14 novembre 2026 (sera). Bazzite alla radice (v0.7.0), utility Windows in `windows/` (v1.0.0).

## Fatto in questo blocco: Lossless Scaling sul OneXPlayer 1S con Windows
- **Problema** (provato dall'utente con RDR2): in schermo intero a 1280×800 l'immagine resta piccola in basso a sinistra (pannello verticale girato da Windows). L'override DPI di Compatibilità **non** serve.
- **Soluzione provata**: gioco in finestra a 1280×800; profilo di Lossless Scaling con filtro `RDR2.exe`, `RDR2`, `Red Dead Redemption 2` **più** il percorso completo dell'exe (con il solo nome non scattava); in «Modifica profilo» «Ridimensionamento automatico» attivo, ritardo 20 s.
- **Guide**: passo comune in `_comune.toml` (prima della chiusura, `solo = ["onexplayer1s"]`, nuova chiave `bazzite = false` = solo Windows, gestita in `bhs/giochi.py`); ogni gioco dà `filtro_ls` ed `exe_ls` in `[parametri_windows.onexplayer1s]`. RDR2, Witcher 3 e Skyrim in finestra nelle tabelle Windows del OneXPlayer; «Risoluzione nel gioco» dell'HUD di Winhanced = 2560×1600 (dedotto, **non provato**).
- **Non provati sul dispositivo**: Witcher 3 e Skyrim con Lossless Scaling (titoli delle finestre nel filtro presunti).
- Commit `2254ffd`, `3da9824` qui; `895df5b` in `siti-web\guide.070293.xyz`; push fatti (token di `dilfal`).
- Test: 192, 1 errore (`test_sincronizza_crea_i_rimandi`) dovuto alla modifica **non mia e non committata** di un'altra sessione a `tools/pubblica_070293.py` (tolti i rimandi `giochi-oxp`): il test va aggiornato da chi chiude quel lavoro. La guida (`nota_app` di RDR2) cita ancora `070293.xyz/giochi-oxp`.

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
