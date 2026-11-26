"""Hourly PV output per kWp for the site, from the PVGIS typical meteorological year.

Model (kept simple and stated):
- PVGIS gives global horizontal irradiance G(h) and air temperature as snapshots at the
  start of each UTC hour. Each hour's mean is taken as the average of its two end
  snapshots, then shifted +1 h to local time (WAT) to line up with the hourly demand.
- At 5 deg N a near-flat array (tilted ~10 deg for rain run-off) receives almost the same
  energy as a horizontal surface over the year, so G(h) is used as plane-of-array
  irradiance. This slightly overstates the dry season and understates the rainy season.
- Cell temperature: T_cell = T_air + (NOCT - 20) / 800 * G, NOCT 45 C.
- Power: P/kWp = G/1000 * (1 + gamma (T_cell - 25)) * (1 - losses), gamma -0.4 %/C,
  losses 14 % (PVGIS default: wiring, inverter, soiling, mismatch).
"""
import numpy as np
import pandas as pd

import data_sources as ds

NOCT = 45.0
GAMMA = -0.004
LOSSES = 0.14
YEAR = "2021"


def weather() -> pd.DataFrame:
    """Hourly irradiance (W/m2) and air temperature (C) in local time, 8,760 rows."""
    d = ds.pvgis_tmy()
    h = pd.DataFrame(d["outputs"]["tmy_hourly"])
    # TMY months come from different years; index by position on one calendar year (UTC)
    out = pd.DataFrame({"ghi": h["G(h)"].to_numpy(), "t_air": h["T2m"].to_numpy()},
                       index=pd.date_range(f"{YEAR}-01-01", periods=len(h), freq="h"))
    # PVGIS values are snapshots at the start of each UTC hour (the daily centre of
    # irradiance falls on solar noon, 11:28 UTC here). Demand is an hourly mean, so the
    # hour's mean is taken as the average of its two end snapshots, then shifted to WAT.
    vals = out.to_numpy()
    vals = (vals + np.roll(vals, -1, axis=0)) / 2
    shift = ds.SITE["utc_offset_h"]
    return pd.DataFrame(np.roll(vals, shift, axis=0), index=out.index, columns=out.columns)


def pv_per_kwp(w: pd.DataFrame | None = None) -> pd.Series:
    """AC output per kWp installed (kW/kWp), hourly, local time."""
    w = weather() if w is None else w
    t_cell = w.t_air + (NOCT - 20) / 800 * w.ghi
    p = w.ghi / 1000 * (1 + GAMMA * (t_cell - 25)) * (1 - LOSSES)
    return p.clip(lower=0).rename("pv_per_kwp")
