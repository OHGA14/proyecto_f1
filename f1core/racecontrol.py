"""Track status (SC/VSC/banderas), race control y paradas en pits."""
import pandas as pd
import numpy as np

from f1core.timeutils import _to_seconds


def _has_yellow_track_status(race_session):
    try:
        ts = race_session.track_status
        if 'Status' not in ts.columns:
            return False
        return ts['Status'].astype(str).str.contains("2", regex=False).any()
    except Exception:
        return False

def _parse_race_control_messages(race_session):
    segments = []
    try:
        rcm = race_session.race_control_messages.copy()
        if rcm.empty or 'Time' not in rcm.columns or 'Message' not in rcm.columns:
            return segments
        rcm = rcm.dropna(subset=['Time', 'Message']).sort_values('Time')
    except Exception:
        return segments

    active = {"SC": None, "VSC": None, "RED": None}
    for _, row in rcm.iterrows():
        msg = str(row['Message']).upper()
        t = row['Time']
        if "VIRTUAL SAFETY CAR DEPLOYED" in msg or "VSC DEPLOYED" in msg:
            if active["VSC"] is None:
                active["VSC"] = t
        if "VIRTUAL SAFETY CAR ENDING" in msg or "VSC ENDING" in msg or "VIRTUAL SAFETY CAR ENDED" in msg:
            if active["VSC"] is not None:
                segments.append({"type": "VSC", "start": active["VSC"], "end": t})
                active["VSC"] = None

        if "SAFETY CAR DEPLOYED" in msg:
            if active["SC"] is None:
                active["SC"] = t
        if "SAFETY CAR ENDING" in msg or "SAFETY CAR IN THIS LAP" in msg or "SAFETY CAR ENDED" in msg:
            if active["SC"] is not None:
                segments.append({"type": "SC", "start": active["SC"], "end": t})
                active["SC"] = None

        if "RED FLAG" in msg:
            if active["RED"] is None:
                active["RED"] = t
        if "GREEN FLAG" in msg or "SESSION RESUMED" in msg or "TRACK CLEAR" in msg or "RED FLAG ENDED" in msg:
            if active["RED"] is not None:
                segments.append({"type": "RED", "start": active["RED"], "end": t})
                active["RED"] = None

    return segments

def _parse_track_status(race_session):
    segments = []
    try:
        ts = race_session.track_status.copy()
        if ts.empty or 'Time' not in ts.columns or 'Status' not in ts.columns:
            return segments
        ts = ts.dropna(subset=['Time', 'Status']).sort_values('Time')
    except Exception:
        return segments

    def _status_type(code_str):
        if "5" in code_str:
            return "RED"
        if "4" in code_str:
            return "SC"
        if "6" in code_str:
            return "VSC"
        if "2" in code_str:
            return "YELLOW"
        return None

    prev_type = None
    start_time = None
    for _, row in ts.iterrows():
        status_str = str(row['Status'])
        t_type = _status_type(status_str)
        if t_type != prev_type:
            if prev_type is not None and start_time is not None:
                segments.append({"type": prev_type, "start": start_time, "end": row['Time']})
            start_time = row['Time'] if t_type is not None else None
            prev_type = t_type

    return segments

def _segments_to_distance(segments, car_ref):
    if car_ref is None or car_ref.empty or 'Time' not in car_ref.columns or 'Distance' not in car_ref.columns:
        return []
    car = car_ref.dropna(subset=['Time', 'Distance']).sort_values('Time')
    time_sec = car['Time'].dt.total_seconds()
    dist = car['Distance'].values
    if time_sec.empty:
        return []
    t_min = time_sec.min()
    t_max = time_sec.max()
    mapped = []
    for seg in segments:
        s = _to_seconds(seg['start'])
        e = _to_seconds(seg['end'])
        if s is None or e is None:
            continue
        seg_start = max(s, t_min)
        seg_end = min(e, t_max)
        if seg_end <= seg_start:
            continue
        d0 = float(np.interp(seg_start, time_sec, dist))
        d1 = float(np.interp(seg_end, time_sec, dist))
        if d1 <= d0:
            continue
        mapped.append({
            "type": seg["type"],
            "start_dist": d0,
            "end_dist": d1,
            "start_time": seg['start'],
            "end_time": seg['end']
        })
    return mapped

def _sc_vsc_lap_ranges(race_session):
    """Devuelve [(tipo, lap_ini, lap_fin)] de los periodos de Safety Car / VSC,
    mapeando `race.track_status` (por SessionTime) a números de vuelta vía el
    tiempo del líder al final de cada vuelta. Códigos FastF1: '4'=SC, '6'=VSC,
    '7'=fin de VSC. Devuelve [] si no hay datos."""
    try:
        ts = race_session.track_status
        laps_df = race_session.laps
        if ts is None or ts.empty or laps_df is None or laps_df.empty:
            return []
        lt = laps_df.dropna(subset=['LapNumber', 'Time'])
        if lt.empty:
            return []
        lead = lt.groupby('LapNumber')['Time'].min().dt.total_seconds().sort_index()
        lap_nums = lead.index.astype(int).values
        lap_end_t = lead.values
        if len(lap_nums) == 0:
            return []

        def _t2lap(t):
            i = int(np.searchsorted(lap_end_t, t))
            return int(lap_nums[min(i, len(lap_nums) - 1)])

        def _typ(c):
            if c == '4':
                return 'SC'
            if c in ('6', '7'):
                return 'VSC'
            return None

        t_arr = ts['Time'].dt.total_seconds().values
        codes = ts['Status'].astype(str).values
        ranges = []
        cur, cur_start = None, None
        for i in range(len(codes)):
            typ = _typ(codes[i])
            if typ != cur:
                if cur is not None:
                    ranges.append((cur, _t2lap(cur_start), _t2lap(t_arr[i])))
                cur, cur_start = typ, t_arr[i]
        if cur is not None:
            ranges.append((cur, _t2lap(cur_start), _t2lap(t_arr[-1])))
        return [(t, a, b) for (t, a, b) in ranges if t and b >= a]
    except Exception:
        return []

def _build_lap_timeline(laps_df):
    cols = ['LapNumber', 'LapStartTime', 'LapTime', 'Time']
    df = laps_df[[c for c in cols if c in laps_df.columns]].dropna(subset=['LapNumber']).copy()
    if df.empty:
        return pd.DataFrame()
    df = df.drop_duplicates(subset=['LapNumber']).sort_values('LapNumber')
    lap_nums = []
    start_sec = []
    end_sec = []
    for _, row in df.iterrows():
        start = row.get('LapStartTime', None)
        lap_time = row.get('LapTime', None)
        end = row.get('Time', None)
        if pd.isna(start) and pd.notna(end) and pd.notna(lap_time):
            start = end - lap_time
        if pd.isna(end) and pd.notna(start) and pd.notna(lap_time):
            end = start + lap_time
        s = _to_seconds(start)
        e = _to_seconds(end)
        if s is None or e is None or e <= s:
            continue
        lap_nums.append(int(row['LapNumber']))
        start_sec.append(s)
        end_sec.append(e)
    if not start_sec:
        return pd.DataFrame()
    timeline = pd.DataFrame({
        'LapNumber': lap_nums,
        'StartSec': start_sec,
        'EndSec': end_sec
    })
    timeline = timeline.sort_values('StartSec')
    return timeline

def _segments_to_laps(segments, laps_df):
    timeline = _build_lap_timeline(laps_df)
    if timeline.empty:
        return [], segments
    start_secs = timeline['StartSec'].values
    end_secs = timeline['EndSec'].values
    lap_nums = timeline['LapNumber'].astype(int).values
    mapped = []
    unmapped = []

    def _map_time_to_lap(t_sec):
        idx = np.searchsorted(start_secs, t_sec, side='right') - 1
        if idx < 0 or idx >= len(start_secs):
            return None
        if t_sec > end_secs[idx]:
            return None
        return int(lap_nums[idx])

    for seg in segments:
        s = _to_seconds(seg['start'])
        e = _to_seconds(seg['end'])
        if s is None or e is None:
            unmapped.append(seg)
            continue
        lap_s = _map_time_to_lap(s)
        lap_e = _map_time_to_lap(e)
        if lap_s is None or lap_e is None:
            unmapped.append(seg)
            continue
        if lap_e < lap_s:
            unmapped.append(seg)
            continue
        mapped.append({
            "type": seg["type"],
            "lap_start": lap_s,
            "lap_end": lap_e
        })
    return mapped, unmapped

def _get_pits_from_laps(laps_df, drivers):
    """Duración de cada parada = PitOutTime (vuelta siguiente) - PitInTime
    (vuelta de entrada). En FastF1 entrada y salida están en FILAS DISTINTAS,
    por eso no sirve exigir ambas en la misma vuelta."""
    if 'PitInTime' not in laps_df.columns or 'PitOutTime' not in laps_df.columns:
        return pd.DataFrame()
    driver_col = 'Driver' if 'Driver' in laps_df.columns else ('Abbreviation' if 'Abbreviation' in laps_df.columns else None)
    if driver_col is None:
        return pd.DataFrame()

    rows = []
    for d in drivers:
        df_d = laps_df[laps_df[driver_col] == d].dropna(subset=['LapNumber']).sort_values('LapNumber')
        if df_d.empty:
            continue
        in_laps = df_d[df_d['PitInTime'].notna()]
        for _, row in in_laps.iterrows():
            lap_n = int(row['LapNumber'])
            nxt = df_d[df_d['LapNumber'] == lap_n + 1]
            out_time = None
            compound_after = None
            if not nxt.empty and pd.notna(nxt.iloc[0].get('PitOutTime', None)):
                out_time = nxt.iloc[0]['PitOutTime']
                compound_after = nxt.iloc[0].get('Compound', None)
            elif pd.notna(row.get('PitOutTime', None)):
                # drive-through o parada registrada en la misma vuelta
                out_time = row['PitOutTime']
                compound_after = row.get('Compound', None)
            if out_time is None:
                continue
            dur = (out_time - row['PitInTime']).total_seconds()
            # descartar duraciones imposibles (bandera roja en boxes, datos corruptos)
            if not np.isfinite(dur) or dur <= 0 or dur > 180:
                continue
            entry = {'DriverCode': d, 'LapNumber': lap_n, 'PitDuration_s': float(dur)}
            if compound_after is not None and pd.notna(compound_after):
                entry['CompoundAfter'] = compound_after
            rows.append(entry)

    return pd.DataFrame(rows)

def _get_pits_from_session(session, drivers):
    pit_stops = getattr(session, "pit_stops", None)
    if pit_stops is None or not isinstance(pit_stops, pd.DataFrame) or pit_stops.empty:
        return pd.DataFrame()
    df = pit_stops.copy()
    driver_col = 'Driver' if 'Driver' in df.columns else ('Abbreviation' if 'Abbreviation' in df.columns else None)
    if driver_col is None:
        return pd.DataFrame()
    df = df[df[driver_col].isin(drivers)]
    if df.empty:
        return pd.DataFrame()
    lap_col = 'LapNumber' if 'LapNumber' in df.columns else ('Lap' if 'Lap' in df.columns else None)
    if lap_col is None:
        return pd.DataFrame()
    if 'Duration' in df.columns:
        df['PitDuration_s'] = df['Duration'].dt.total_seconds() if hasattr(df['Duration'].iloc[0], "total_seconds") else df['Duration']
    elif 'PitInTime' in df.columns and 'PitOutTime' in df.columns:
        df['PitDuration_s'] = (df['PitOutTime'] - df['PitInTime']).dt.total_seconds()
    else:
        return pd.DataFrame()
    df = df[df['PitDuration_s'].notna()]
    if df.empty:
        return pd.DataFrame()
    out = pd.DataFrame({
        'DriverCode': df[driver_col],
        'LapNumber': df[lap_col].astype(int),
        'PitDuration_s': df['PitDuration_s'].astype(float)
    })
    if 'Compound' in df.columns:
        out['CompoundAfter'] = df['Compound']
    return out

def get_pits_dataframe(session, laps_df, drivers):
    pit_df = _get_pits_from_laps(laps_df, drivers)
    if not pit_df.empty:
        pit_df['Source'] = 'laps'
        return pit_df
    pit_df = _get_pits_from_session(session, drivers)
    if not pit_df.empty:
        pit_df['Source'] = 'pit_stops'
        return pit_df
    return pd.DataFrame()
