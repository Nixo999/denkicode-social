# denkicode-social

Pubblica su `@denkicode` quello che sta in `coda.json`. Repo **pubblico** di proposito:
Instagram scarica le immagini da `raw.githubusercontent.com`, e un repo privato non le serve.
Il piano (cosa, quando, perché) sta nel vault: `02-Sales/processo/piano-instagram.md`.

## Come si aggiunge un post

Le immagini (JPEG 1080x1350 per post e caroselli, 1080x1920 per storie, MP4 per i Reel) vanno in
`media/`, poi una voce in `coda.json`. **L'ora è quella di Roma**, scritta senza fuso:

```json
{"id": "2026-10-04-reel-albybike", "tipo": "reel", "quando": "2026-10-04T21:00",
 "file": ["albybike.mp4"], "didascalia": "Albybike vende biciclette..."}
```

`tipo`: `post`, `carosello` (da 2 a 10 JPEG), `storia`, `reel`. Le storie non hanno didascalia.
Commit e push: il resto lo fa il cron. Controllo prima di pushare: `python3 pubblica.py --prova`.

## Come si comporta

- Il cron di GitHub non è puntuale: chiesto ogni 20 minuti, l'1-2/10/2026 è girato 5 volte in 21 ore.
  Per questo ogni giro che parte **aspetta sul posto** il prossimo post, se cade entro 5 ore e mezza, e lo
  pubblica al minuto. Se nessun giro parte in quella finestra il post esce in ritardo, fino a 6 ore.
- Un post fuori orario di più di 6 ore viene **saltato** (`saltato` in `coda.json`), non pubblicato.
- Se un post fallisce riprova al giro dopo, per 6 ore. Il workflow rosso manda una mail a Nicola.
- Si ferma se il token non è di `@denkicode`.
- Il log di `fatto` in `coda.json` è la memoria: un post con `fatto` non esce due volte.

## Setup, una volta

App Meta di tipo Business, caso d'uso «Manage messaging & content on Instagram», «API setup with
Instagram business login»: niente Pagina Facebook, niente App Review per il proprio account. Il token deve
avere `instagram_business_basic` e `instagram_business_content_publish`.

Secret del repo: `IG_TOKEN` (token lungo dell'app Meta) e `GH_PAT` (token fine-grained di Nicola con
*Secrets: read/write* su questo solo repo, serve a `rinnova.yml` per riscrivere `IG_TOKEN`
ogni lunedì: il token vale 60 giorni). I secret li inserisce una persona, mai nel repo.

Se per 60 giorni nessuno committa, GitHub spegne i cron: ogni post in coda è un commit, quindi basta
tenere la coda piena.

## Non verificato

Nessuna chiamata all'API è stata ancora fatta con un token vero: endpoint e parametri vengono dalla
documentazione Meta letta il 01/10/2026. Il primo giro si fa con una storia (dura 24 ore).
Le storie via API potrebbero richiedere un account Business, non Creator.
