"""Ingesta de sesiones FastF1 → DuckDB (data.nosync/f1.duckdb).

Uso:
  # una sesión concreta (año, GP, sesión):
  .venv.nosync/bin/python ingest.py 2026 "British Grand Prix" "Race"

  # todo lo que ya esté descargado en cache.nosync/ (no descarga nada nuevo):
  .venv.nosync/bin/python ingest.py --cached
  .venv.nosync/bin/python ingest.py --cached --solo-carreras --limit 8
"""
import argparse
import os
import re
import sys
import time

import fastf1 as ff1

from f1core import db

CACHE_DIR = "cache.nosync"


def _cached_sessions():
    """Enumera (year, gp, session) de lo que ya existe en la caché de FastF1."""
    out = []
    if not os.path.isdir(CACHE_DIR):
        return out
    for year in sorted(os.listdir(CACHE_DIR)):
        ydir = os.path.join(CACHE_DIR, year)
        if not (year.isdigit() and os.path.isdir(ydir)):
            continue
        for evdir in sorted(os.listdir(ydir)):
            m = re.match(r"\d{4}-\d{2}-\d{2}_(.+)", evdir)
            if not m:
                continue
            gp = m.group(1).replace("_", " ")
            for sesdir in sorted(os.listdir(os.path.join(ydir, evdir))):
                sm = re.match(r"\d{4}-\d{2}-\d{2}_(.+)", sesdir)
                if not sm:
                    continue
                full = os.path.join(ydir, evdir, sesdir)
                # solo si hay datos de timing (sin esto no hay vueltas que ingerir)
                if not os.path.exists(os.path.join(full, "_extended_timing_data.ff1pkl")):
                    continue
                out.append((int(year), gp, sm.group(1).replace("_", " ")))
    return out


def ingest_one(con, year, gp, session_name):
    t0 = time.time()
    ses = ff1.get_session(year, gp, session_name)
    ses.load(telemetry=False, weather=False, messages=False)
    sid = db.ingest_session(con, ses)
    n = con.execute("SELECT count(*) FROM laps WHERE session_id=?", [sid]).fetchone()[0]
    print(f"  OK {sid}  ({n} vueltas, {time.time()-t0:.1f}s)")
    return sid


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("year", nargs="?", type=int)
    ap.add_argument("gp", nargs="?")
    ap.add_argument("session", nargs="?")
    ap.add_argument("--cached", action="store_true",
                    help="ingiere todo lo ya descargado en cache.nosync/")
    ap.add_argument("--solo-carreras", action="store_true",
                    help="con --cached: solo sesiones 'Race'")
    ap.add_argument("--limit", type=int, default=0, help="máximo de sesiones")
    args = ap.parse_args()

    ff1.Cache.enable_cache(CACHE_DIR)
    con = db.connect()

    if args.cached:
        targets = _cached_sessions()
        if args.solo_carreras:
            targets = [t for t in targets if t[2] == "Race"]
        if args.limit:
            targets = targets[: args.limit]
        print(f"Ingiriendo {len(targets)} sesiones desde la caché…")
        ok = fail = 0
        for year, gp, ses_name in targets:
            try:
                ingest_one(con, year, gp, ses_name)
                ok += 1
            except Exception as e:
                print(f"  FALLO {year} {gp} {ses_name}: {type(e).__name__}: {e}")
                fail += 1
        print(f"Listo: {ok} ok, {fail} fallos.")
    elif args.year and args.gp and args.session:
        ingest_one(con, args.year, args.gp, args.session)
    else:
        ap.print_help()
        sys.exit(1)

    print("\nSesiones en la base:")
    print(db.list_sessions(con).to_string(index=False))


if __name__ == "__main__":
    main()
