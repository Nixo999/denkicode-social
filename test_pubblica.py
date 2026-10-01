"""python3 test_pubblica.py: la logica degli orari, l'unico pezzo che puo' pubblicare a sproposito."""
from datetime import datetime
from pubblica import ROMA, dovuti

c = [{"id": "futuro", "quando": "2026-10-04T21:00"},
     {"id": "ora", "quando": "2026-10-04T20:50"},
     {"id": "tardi", "quando": "2026-10-04T10:00"},
     {"id": "gia", "quando": "2026-10-04T20:00", "fatto": "1"},
     {"id": "scartato", "quando": "2026-10-04T20:00", "saltato": "x"}]
pub, salta = dovuti(c, datetime(2026, 10, 4, 21, 0, tzinfo=ROMA))
assert [i["id"] for i in pub] == ["ora"], pub
assert [i["id"] for i in salta] == ["tardi"], salta
# passaggio all'ora solare, 25/10/2026: le 21:00 di Roma restano le 21:00 di Roma
assert not dovuti([{"id": "a", "quando": "2026-10-25T21:00"}], datetime(2026, 10, 25, 20, 59, tzinfo=ROMA))[0]
assert dovuti([{"id": "a", "quando": "2026-10-25T21:00"}], datetime(2026, 10, 25, 21, 1, tzinfo=ROMA))[0]
print("ok")
