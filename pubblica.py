#!/usr/bin/env python3
"""Pubblica su @denkicode i post di coda.json il cui orario (ora di Roma) e' passato.

Gira ogni 20 minuti da GitHub Actions (pubblica.yml). Solo libreria standard.

  pubblica.py            pubblica quello che e' dovuto
  pubblica.py --prova    elenca cosa pubblicherebbe, non chiama l'API
  pubblica.py aspetta    dorme fino al prossimo post, se cade entro 5 ore e mezza
  pubblica.py rinnova    rinnova il token lungo e stampa quello nuovo
  pubblica.py verifica   dice di chi e' il token e che tipo di account e', senza pubblicare niente

Variabili: IG_TOKEN (token lungo, solo nei secret di GitHub, mai nel repo),
IG_USERNAME (default denkicode: se il token e' di un altro profilo si ferma).
Le immagini le scarica Instagram da raw.githubusercontent.com/<repo>/main/media/.
"""
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

QUI = pathlib.Path(__file__).parent
CODA = QUI / "coda.json"
API = "https://graph.instagram.com/v23.0"
ROMA = ZoneInfo("Europe/Rome")  # il cron di Actions e' in UTC: l'ora la decide questo, non il cron
RITARDO_MAX = timedelta(hours=6)  # oltre, il post e' fuori orario: si salta, non si pubblica a caso
# Il cron di GitHub non e' puntuale: l'1-2/10/2026, chiesto ogni 20 minuti, e' girato 5 volte in
# 21 ore. Quindi ogni giro che parte aspetta il prossimo post sul posto, e lo pubblica al minuto.
ATTESA_MAX = timedelta(hours=5, minutes=30)  # un job di Actions muore a 6 ore
MEDIA = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', 'Nixo999/denkicode-social')}/main/media/"
TIPI = {"post", "carosello", "storia", "reel"}


def dovuti(coda, ora):
    """(da_pubblicare, da_saltare): gli elementi con orario passato, senza esito."""
    pub, salta = [], []
    for it in coda:
        if "fatto" in it or "saltato" in it:
            continue
        q = datetime.fromisoformat(it["quando"]).replace(tzinfo=ROMA)
        if q <= ora:
            (salta if ora - q > RITARDO_MAX else pub).append(it)
    return pub, salta


def attesa(coda, ora):
    """Secondi da dormire fino al prossimo post: 0 se ce n'e' uno dovuto adesso o se e' oltre ATTESA_MAX."""
    if dovuti(coda, ora)[0]:
        return 0
    futuri = [q - ora for it in coda if "fatto" not in it and "saltato" not in it
              and (q := datetime.fromisoformat(it["quando"]).replace(tzinfo=ROMA)) > ora]
    return min(futuri).total_seconds() if futuri and min(futuri) <= ATTESA_MAX else 0


def controlla(it):
    assert it["tipo"] in TIPI, f"{it['id']}: tipo {it['tipo']!r} sconosciuto"
    assert it["file"], f"{it['id']}: nessun file"
    for f in it["file"]:
        assert (QUI / "media" / f).is_file(), f"{it['id']}: media/{f} non esiste"
        assert f.lower().endswith((".jpg", ".jpeg", ".mp4")), f"{it['id']}: {f} non e' JPEG o MP4"
        # un video senza media_type l'API lo rifiuta: i video escono solo come reel o storia
        assert it["tipo"] in ("reel", "storia") or not f.lower().endswith(".mp4"), f"{it['id']}: un video va come reel o storia"


def chiama(percorso, post=False, base=API, **p):
    p["access_token"] = os.environ["IG_TOKEN"]
    q = urllib.parse.urlencode(p)
    req = urllib.request.Request(f"{base}/{percorso}" + ("" if post else "?" + q), data=q.encode() if post else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # `from None`: l'eccezione originale porterebbe l'URL, e nell'URL c'e' il token
        raise RuntimeError(f"{percorso}: {e.code} {e.read().decode()[:300]}") from None


def sorgente(f):
    chiave = "video_url" if f.lower().endswith(".mp4") else "image_url"
    return {chiave: MEDIA + urllib.parse.quote(f)}


def aspetta(cid):
    for _ in range(30):
        s = chiama(cid, fields="status_code")["status_code"]
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"contenitore {cid}: {s}")
        time.sleep(10)
    raise RuntimeError(f"contenitore {cid}: ancora in lavorazione dopo 5 minuti")


def pubblica(uid, it):
    cap, f = it.get("didascalia", ""), it["file"]
    crea = lambda **p: chiama(f"{uid}/media", True, **p)["id"]
    if it["tipo"] == "carosello":
        figli = []
        for x in f:  # ponytail: solo immagini nei caroselli, i video vorrebbero media_type=VIDEO
            figli.append(crea(is_carousel_item="true", **sorgente(x)))
            aspetta(figli[-1])
        cid = crea(media_type="CAROUSEL", children=",".join(figli), caption=cap)
    elif it["tipo"] == "storia":
        cid = crea(media_type="STORIES", **sorgente(f[0]))
    elif it["tipo"] == "reel":
        cid = crea(media_type="REELS", share_to_feed="true", caption=cap, **sorgente(f[0]))
    else:
        cid = crea(caption=cap, **sorgente(f[0]))
    aspetta(cid)
    return chiama(f"{uid}/media_publish", True, creation_id=cid)["id"]


def salva(coda):
    CODA.write_text(json.dumps(coda, indent=2, ensure_ascii=False) + "\n")


def rinnova():
    r = chiama("refresh_access_token", base="https://graph.instagram.com", grant_type="ig_refresh_token")
    print(f"token rinnovato, scade tra {r['expires_in'] // 86400} giorni", file=sys.stderr)
    print(r["access_token"])


def main(prova):
    coda = json.loads(CODA.read_text())
    for it in coda:
        if "fatto" not in it and "saltato" not in it:
            controlla(it)
    ora = datetime.now(ROMA)
    pub, salta = dovuti(coda, ora)
    for it in salta:
        it["saltato"] = f"fuori orario: previsto {it['quando']}, visto {ora:%Y-%m-%dT%H:%M}"
        print(f"SALTATO {it['id']}: {it['saltato']}")
    if prova:
        for it in pub:
            print(f"PUBBLICHEREI {it['id']} ({it['tipo']}, {len(it['file'])} file, previsto {it['quando']})")
        return 0
    if salta:
        salva(coda)
    if not pub:
        return 0
    me = chiama("me", fields="user_id,username")
    atteso = os.environ.get("IG_USERNAME", "denkicode")
    if me["username"] != atteso:
        print(f"Il token e' di @{me['username']}, non di @{atteso}: mi fermo.")
        return 1
    errori = 0
    for it in pub:
        try:
            it["fatto"] = f"{pubblica(me['user_id'], it)} {ora:%Y-%m-%dT%H:%M}"
            salva(coda)  # subito: se il commit finale va storto, il prossimo giro non ripubblica
            print(f"PUBBLICATO {it['id']}")
        except (RuntimeError, OSError) as e:  # OSError: timeout e rete giu', che non sono HTTPError
            errori += 1
            print(f"ERRORE {it['id']}: {e}")  # resta in coda: riprova al giro dopo, fino a RITARDO_MAX
    return 1 if errori else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["rinnova"]:
        rinnova()
    elif sys.argv[1:] == ["verifica"]:
        me = chiama("me", fields="user_id,username,account_type")
        print(f"token valido: @{me['username']}, account {me.get('account_type', '?')}, id {me['user_id']}")
    elif sys.argv[1:] == ["aspetta"]:
        s = attesa(json.loads(CODA.read_text()), datetime.now(ROMA))
        print(f"aspetto {s / 60:.0f} minuti")
        time.sleep(s)
    else:
        sys.exit(main("--prova" in sys.argv))
