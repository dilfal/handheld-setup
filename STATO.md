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

- **Video delle due guide hardware** (richiesta dell'utente): uno per riga, larghi quanto la finestra e mai più alti dello schermo (CSS `.video-grid` più un piccolo script che misura la finestra senza barra di scorrimento); negli `iframe` c'è `?vq=hd2160`, che è solo una richiesta: la qualità la sceglie YouTube in base alla grandezza del riquadro e alla connessione. Misurato in Chrome a 1582×804 (video 1427×803), 982 e 504 px di larghezza (video a tutta larghezza, nessuno scorrimento orizzontale). Commit `84f03b1` qui e `db935dc` nel sito, online.

- **Guide «Ottimizzazione giochi» con scelta del sistema** (richiesta dell'utente del 14 novembre): in cima alle due pagine il riquadro «Che sistema usi?» (Bazzite / Windows (Winhanced)); chi è su Windows usa sicuramente Winhanced. La scelta segue `?sistema=`, un'àncora `…-windows`, `localStorage["guida-sistema"]`, poi lo user agent. Dati: `carica_guide(profilo, sistema="bazzite")`, tabelle `[parametri_windows]` e chiavi dei passi `titolo_windows`, `testo_windows`, `dove_windows`, `voci_windows`, `windows = false`; il generatore scrive per ogni gioco la sezione `<id>` (`solo-bazzite`) e `<id>-windows` (`solo-windows`). L'app Bazzite legge gli stessi dati di prima. Sezioni 1, 2 e 6 in variante Windows scritte a mano nelle pagine. Nell'indice del sottodominio ogni scheda «Ottimizzazione» ha due ingressi.
- **Regola per i testi su Winhanced**: solo fatti verificati (pannello nella Xbox Game Bar con potenza, risoluzione, frequenza, limite dei fotogrammi, profili per gioco; percorso dell'eseguibile nelle opzioni del gioco; «Gioca in locale»), niente nomi di menu inventati. Sul 1S il controllo della potenza da Winhanced resta «non provato».
- **Controlli**: 191 test OK, 13 saltati; `genera_guide.py --verifica` 0; clic del selettore provato in Chrome headless; una revisione Opus fatta. Pubblicato su `guide.070293.xyz` e su `070293.xyz`.

## Da fare
- **DNS e HTTPS**: fatti. Record `CNAME` `guide` → `dilfal.github.io` creato dall'utente su Cloudflare (solo DNS); certificato approvato, «Enforce HTTPS» attivo; le 7 pagine rispondono 200 su `https://guide.070293.xyz`. (Il token `CLOUDFLARE_API_TOKEN` del PC non vede la zona `070293.xyz`.)
- **Commit in questo repository**: fatto e pubblicato (`7e0f5d6`).
- Facoltativo: link a `guide.070293.xyz` dalla homepage di `070293.xyz`; `070293.xyz/guide/` resta com'è (lo usano gli indirizzi brevi `giochi-oxp` e `giochi-ally`).
- Prove sui dispositivi: `PROSSIMI_PASSI.md` (Bazzite) e `windows/ISTRUZIONI.md` (Windows).

## Come aggiungere una guida al sottodominio
1. Mettere il file `.html` in `guide/sottodominio/` (nome senza spazi).
2. Aggiungere la sua scheda in `guide/sottodominio/index.html`.
3. `python tools/pubblica_guide.py`, poi commit e push in `siti-web\guide.070293.xyz`.

## Note
- `desktop.ini` ricompare dentro `.git` e rompe fetch/merge: `find .git -iname desktop.ini -delete`.
- Push con il token di `dilfal` (memoria `push-github-account-dilfal`, nella cartella di memoria con il vecchio nome `bazzite-handheld-setup`); nel nuovo repository l'autore git locale è `dilfal`.
