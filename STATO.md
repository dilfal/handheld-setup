# STATO: Handheld Setup (repository unico `dilfal/handheld-setup`)

Aggiornato il 13 novembre 2026. Bazzite alla radice (v0.7.0), utility Windows in `windows/` (v1.0.0).

## Fatto oggi
- **Fusione**: `onexplayer-1s-drivers` è dentro questo repository (merge, storia conservata) nella cartella `windows/`. Repository rinominato da `bazzite-handheld-setup` a `handheld-setup` (rinvio automatico di GitHub dai vecchi indirizzi). Commit `9425092` e `2b0e327`.
- **Driver**: 13 archivi nella Release `windows-v1.0.0` (0,9 GB); in locale in `windows/drivers/` (ignorata da git). `windows/publish-release.ps1` la ricrea.
- **Sito**: `070293.xyz/oxp-win` serve lo script `windows/oxp1s.ps1` completo (copia byte per byte, ASCII senza BOM, LF), scritta da `python tools/pubblica_070293.py` (commit `87b94d4` su `dilfal/070293`). `/oxp`, `/ally`, `/bhs` usano `dilfal/handheld-setup`.
- **Controlli**: installatori e guide `--verifica` a 0; 183 test OK (13 saltati su Windows); script Windows senza errori di sintassi in PS 5.1.

## Da fare
- **Vecchio repo `dilfal/onexplayer-1s-drivers`**: ancora attivo e non archiviato. Il comando di archiviazione è stato bloccato dal sistema di permessi: va deciso dall'utente. Piano: `oxp1s.ps1` ridotto a rinvio a `irm 070293.xyz/oxp-win | iex`, README di rinvio, poi archivio.
- **Pages di `handheld-setup`** (`dilfal.click/handheld-setup/`) ancora acceso e duplicato di 070293.xyz: spegnerlo (`gh api -X DELETE repos/dilfal/handheld-setup/pages`) quando l'utente conferma.
- **Cloudflare**: per `070293.xyz` non serve nulla (DNS-only verso i 4 IP di GitHub Pages, `www` CNAME). Facoltativo: record AAAA IPv6.
- **Cartella locale** `C:\Users\df\Dev\GitHub\onexplayer-1s-drivers`: da cancellare a mano dopo l'archiviazione.
- Prove sui dispositivi: `PROSSIMI_PASSI.md` (Bazzite) e `windows/ISTRUZIONI.md` (Windows: driver, touch, rotazione).

## Note
- `desktop.ini` ricompare dentro `.git` (Drive?) e rompe fetch/merge: `find .git -iname desktop.ini -delete`.
- Push con il token di `dilfal` (vedi memoria `push-github-account-dilfal`); `GH_TOKEN="$(gh auth token --user dilfal)"` per `gh`.
- Cartella locale e memoria del progetto restano con il vecchio nome `bazzite-handheld-setup`.
