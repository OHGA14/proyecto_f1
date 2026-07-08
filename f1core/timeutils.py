"""Formato de tiempos y utilidades de sectores."""
import pandas as pd
import numpy as np


def format_time(seconds): return "-" if pd.isna(seconds) else f"{int(seconds//60)}:{seconds%60:06.3f}"

def _to_seconds(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if hasattr(value, "total_seconds"):
        return value.total_seconds()
    try:
        return pd.to_timedelta(value).total_seconds()
    except Exception:
        return None

def _describe_circuit_zone(percent):
    if percent < 25:
        return "zona de frenadas"
    if percent < 55:
        return "curvas medias"
    if percent < 75:
        return "curvas rápidas"
    return "rectas largas"

def _get_sector_times_seconds(lap):
    if lap is None:
        return None, None, None
    s1 = _to_seconds(lap.get('Sector1Time')) if 'Sector1Time' in lap else None
    s2 = _to_seconds(lap.get('Sector2Time')) if 'Sector2Time' in lap else None
    s3 = _to_seconds(lap.get('Sector3Time')) if 'Sector3Time' in lap else None
    if s3 is None and s1 is not None and s2 is not None and 'LapTime' in lap:
        lap_time = _to_seconds(lap.get('LapTime'))
        if lap_time is not None:
            rem = lap_time - s1 - s2
            s3 = rem if rem > 0 else None
    return s1, s2, s3

def _format_sector_time(value_s):
    if value_s is None or (isinstance(value_s, float) and np.isnan(value_s)):
        return "N/A"
    return format_time(value_s)

def _get_sector_cut_distances(lap, tel):
    if lap is None or tel is None or tel.empty:
        return [], True
    tel_clean = tel.dropna(subset=['Distance', 'Time']).sort_values('Distance')
    if tel_clean.empty:
        return [], True
    max_distance = float(tel_clean['Distance'].max())
    s1, s2, _ = _get_sector_times_seconds(lap)
    if s1 is None or s2 is None:
        return [
            ("S1", max_distance / 3.0),
            ("S2", max_distance * 2.0 / 3.0),
            ("S3", max_distance)
        ], True
    time_sec = tel_clean['Time'].dt.total_seconds().values
    time_zero = time_sec[0]
    time_lap = time_sec - time_zero
    s1_dist = float(np.interp(s1, time_lap, tel_clean['Distance'].values))
    s2_dist = float(np.interp(s1 + s2, time_lap, tel_clean['Distance'].values))
    return [("S1", s1_dist), ("S2", s2_dist), ("S3", max_distance)], False
