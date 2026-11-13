# STATO: Handheld Setup (repository unico `dilfal/handheld-setup`)

Aggiornato il 13 novembre 2026 (sera). Bazzite alla radice (v0.7.0), utility Windows in `windows/` (v1.0.0).

## Fatto in questo blocco: sottodominio `guide.070293.xyz`
- **Sito nuovo**: repository pubblico `dilfal/guide.070293.xyz` (locale: `C:\Users\df\Dev\GitHub\siti-web\guide.070293.xyz`, commit `8402607`), GitHub Pages attivo su `main`, dominio personalizzato impostato e verificato. Le 7 pagine rispondono 200 dai server di GitHub (provate con `curl --resolve`).
- **Contenuto**: indice (`index.html`, due gruppi: OneXPlayer 1S e ASUS ROG Ally) più sei guide: le quattro di `guide/` (installazione e ottimizzazione) e le due hardware.
- **Sorgente, in questo repository**:
  - `guide/sottodominio/index.html`: l'indice del sottodominio (scritto a mano).
  - `guide/sottodominio/manutenzione_onexplayer_1s.html` (era `come cambiare la batteria.html`) e `guide/sottodominio/nvme_rog_ally.html` (era `guida ally nvme.html`): spostate dalla radice, con il link «← Tutte le guide» e i link YouTube in https.
  - `tools/pubblica_guide.py`: copia `guide/*.html` (tranne `index.html`) e `guide/sottodominio/*.html` nella radice del sito; si ferma con 1 se una pagina non è collegata dall'indice o se un `href`/`src` locale non esiste.
- **Controlli**: `pubblica_guide.py` 0 (7 pagine); `genera_guide.py --verifica` 0; `python -m unittest tests.test_guide_web` 13 test OK (pytest non è installato). Una revisione Opus fatta (corretto solo «passo-passo» → «passo passo» nell'indice).

## Da fare
- **Utente, Cloudflare**: record `CNAME`, nome `guide`, destinazione `dilfal.github.io`, proxy spento (solo DNS). Il token `CLOUDFLARE_API_TOKEN` del PC non vede la zona `070293.xyz`, quindi non si può fare da qui.
- **Dopo il DNS**: attivare «Enforce HTTPS» (`gh api -X PUT repos/dilfal/guide.070293.xyz/pages -F https_enforced=true` con il token di `dilfal`, quando il certificato è pronto) e provare `https://guide.070293.xyz`.
- **Commit in questo repository**: `guide/sottodominio/` e `tools/pubblica_guide.py` sono ancora non tracciati (nessun commit fatto: aspetta il sì dell'utente).
- Facoltativo: link a `guide.070293.xyz` dalla homepage di `070293.xyz`; `070293.xyz/guide/` resta com'è (lo usano gli indirizzi brevi `giochi-oxp` e `giochi-ally`).
- Prove sui dispositivi: `PROSSIMI_PASSI.md` (Bazzite) e `windows/ISTRUZIONI.md` (Windows).

## Come aggiungere una guida al sottodominio
1. Mettere il file `.html` in `guide/sottodominio/` (nome senza spazi).
2. Aggiungere la sua scheda in `guide/sottodominio/index.html`.
3. `python tools/pubblica_guide.py`, poi commit e push in `siti-web\guide.070293.xyz`.

## Note
- `desktop.ini` ricompare dentro `.git` e rompe fetch/merge: `find .git -iname desktop.ini -delete`.
- Push con il token di `dilfal` (memoria `push-github-account-dilfal`, nella cartella di memoria con il vecchio nome `bazzite-handheld-setup`); nel nuovo repository l'autore git locale è `dilfal`.
