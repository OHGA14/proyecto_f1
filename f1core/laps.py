"""Selección y filtrado de vueltas: validez, vuelta rápida, ritmo, outliers."""
import pandas as pd
import numpy as np


def _is_valid_lap(lap_row):
    if lap_row is None:
        return False
    if 'LapTime' in lap_row and pd.isna(lap_row['LapTime']):
        return False
    if 'IsAccurate' in lap_row and lap_row['IsAccurate'] is False:
        return False
    if 'PitInTime' in lap_row and pd.notna(lap_row['PitInTime']):
        return False
    if 'PitOutTime' in lap_row and pd.notna(lap_row['PitOutTime']):
        return False
    return True

def get_selected_lap(laps_df, driver, mode, lap_number=None):
    l = laps_df.pick_driver(driver)
    if l.empty:
        return None, "no-data"

    if mode == "Vuelta Rápida":
        try:
            lap = l.pick_fastest()
        except Exception:
            return None, "no-fastest"
        if not _is_valid_lap(lap):
            return None, "invalid-fastest"
        return lap, "fastest"

    if lap_number is None:
        return None, "no-lap-number"
    target = l[l['LapNumber'] == lap_number]
    if target.empty:
        return None, f"missing-lap-{lap_number}"
    lap = target.iloc[0]
    if not _is_valid_lap(lap):
        return None, f"invalid-lap-{lap_number}"
    return lap, f"lap-{lap_number}"

def _filter_pace_laps(laps_df, filter_outliers=True):
    l = laps_df.copy()
    if hasattr(l, "pick_quicklaps"):
        try:
            l = l.pick_quicklaps()
        except Exception:
            pass
    if 'IsAccurate' in l.columns:
        l = l[l['IsAccurate'] == True]
    if 'PitInTime' in l.columns:
        l = l[l['PitInTime'].isna()]
    if 'PitOutTime' in l.columns:
        l = l[l['PitOutTime'].isna()]
    if 'TrackStatus' in l.columns:
        status = l['TrackStatus'].astype(str)
        l = l[~status.str.contains("4|5|6", regex=True)]
    if 'LapTime' not in l.columns:
        return pd.Series(dtype=float)

    seconds = l['LapTime'].dt.total_seconds().dropna()
    if seconds.empty:
        return seconds

    if filter_outliers and len(seconds) >= 6:
        q1 = seconds.quantile(0.25)
        q3 = seconds.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            seconds = seconds[(seconds >= lower) & (seconds <= upper)]
        else:
            p5, p95 = seconds.quantile(0.05), seconds.quantile(0.95)
            seconds = seconds[(seconds >= p5) & (seconds <= p95)]

    return seconds

def _mark_outlier_laps(df_driver):
    """Marca vueltas atípicas por piloto: pits, SC/VSC o fuera de Q3+1.5*IQR.
    Devuelve una Serie booleana alineada con el índice del DataFrame."""
    out = pd.Series(False, index=df_driver.index)
    if 'IsPit' in df_driver.columns:
        out |= df_driver['IsPit'].fillna(False).astype(bool)
    if 'PitOutTime' in df_driver.columns:
        out |= df_driver['PitOutTime'].notna()
    if 'IsScVsc' in df_driver.columns:
        out |= df_driver['IsScVsc'].fillna(False).astype(bool)
    secs = df_driver['Seconds'].dropna()
    if len(secs) >= 6:
        q1, q3 = secs.quantile(0.25), secs.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            out |= df_driver['Seconds'] > (q3 + 1.5 * iqr)
    return out
