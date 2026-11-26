"""Hourly electricity demand for the village: 312 households, a primary school, a clinic.

Households
    312 households are drawn (with the survey weights) from rural households in the World
    Bank MTF Nigeria 2018 survey, with what they own and how many hours a day they use it:
      low case   all rural households (73 % have no electricity, so many own nothing yet)
      high case  rural households already on the grid (what people use once they have power)
    The survey covers North-West Nigeria only; using it for a Cross River village is an
    assumption. RAMP (Lombardi et al. 2019) spreads each appliance's daily hours randomly
    inside its usage windows, a new random draw every day.

Wattages (table APPLIANCES, source in each row)
    LG    Lighting Global, "PV System Design Tool and Example Designs" (Nigerian school and
          clinic designs at Gudupe/Bwari, FCT)
    RAMP  RAMP example inputs (rural village, Lombardi et al. 2019)
    NP    common nameplate value, my assumption (flagged in the README)

School and clinic come from the same Lighting Global designs (appliance lists below).
The clinic has a low case (Gudupe full PHC design, ~17.6 kWh/day) and a high case (the
same shape scaled to SEforALL's Type 2 PHC, ~36 kWh/day).

All times are local (WAT, UTC+1). Output: hourly kW for one year (8,760 hours).
"""
import logging
import warnings

import numpy as np
import pandas as pd

import data_sources as ds

N_HOUSEHOLDS = 312
YEAR = "2021"              # a non-leap year for 8,760 hours; the weekday pattern only
SEED = 0
CLINIC_HIGH_KWH_DAY = 36.0  # SEforALL Type 2 PHC

# MTF item -> watts, source, default hours/day when the survey has none, windows (h), on-block (min)
# A window [a, b] with b < a wraps past midnight and is split into two.
APPLIANCES = {
    "LED Light Bulb":                  dict(w=10, src="LG", hours=None, kind="light"),
    "Incandescent Light Bulb":         dict(w=60, src="NP", hours=None, kind="light"),
    "Compact Fluorescent Light (CFL) Bulb": dict(w=15, src="NP", hours=None, kind="light"),
    "Fluorescent Tube":                dict(w=36, src="NP", hours=None, kind="light"),
    "Fan":                             dict(w=70, src="LG", hours=6, win=[(12, 16), (21, 2)], cycle=60),
    "Regular Color TV":                dict(w=100, src="LG", hours=5, kind="tv"),
    "Flat color TV":                   dict(w=100, src="LG", hours=5, kind="tv"),
    "Black & White TV":                dict(w=100, src="LG", hours=5, kind="tv"),
    "VCD/DVD":                         dict(w=20, src="LG", hours=1, win=[(19, 23)], cycle=30),
    "Radio/CD Players/sound system":   dict(w=36, src="RAMP", hours=4.4, win=[(6, 9), (18, 22)], cycle=30),
    "Regular mobile phone charger":    dict(w=10, src="LG", hours=1, win=[(18, 23)], cycle=30),
    "Smartphone (internet phone) charger": dict(w=10, src="LG", hours=1, win=[(18, 23)], cycle=30),
    "Electric Iron":                   dict(w=1000, src="NP", hours=0.25, win=[(6, 8)], cycle=10),
    "Electric hot water pot/kettle":   dict(w=1500, src="NP", hours=1 / 6, win=[(6, 8)], cycle=5),
    "Refrigerator":                    dict(w=130, src="LG", hours=9.4, win=[(0, 24)], cycle=30),
    "Freezer":                         dict(w=200, src="RAMP", hours=9.4, win=[(0, 24)], cycle=30),
    "Computer":                        dict(w=60, src="LG", hours=2, win=[(19, 22)], cycle=30),
    "Electric food processor/blender": dict(w=50, src="RAMP", hours=0.25, win=[(7, 8), (18, 20)], cycle=5),
}
LIGHT_WIN, LIGHT_OVERNIGHT, LIGHT_MAIN_MAX = [(18, 24), (5, 7)], [(0, 5)], 8.0
TV_WIN, TV_EXTRA, TV_MAIN_MAX = [(17, 24)], [(12, 15)], 7.0

# (name, number, watts, hours/day, windows, on-block minutes, school days only)
SCHOOL = [  # Lighting Global "basic" school design, Bwari (FCT): 3.65 kWh/day
    ("fan", 5, 70, 4, [(8, 13)], 60, True),
    ("light, interior", 22, 10, 4, [(8, 13)], 60, True),
    ("light, outdoor/security", 12, 10, 10, [(18.5, 6.5)], 600, False),
    ("phone charging", 5, 10, 1, [(8, 13)], 30, True),
    ("remote monitoring", 1, 5, 24, [(0, 24)], 1440, False),
]
CLINIC = [  # Lighting Global "full" PHC design, Gudupe (FCT): 17.6 kWh/day stated
    ("refrigerator/freezer", 1, 130, 9.4, [(0, 24)], 30),
    ("fan", 16, 70, 9, [(9, 18)], 60),
    ("light, interior", 73, 10, 6, [(18, 6)], 60),
    ("light, outdoor/security", 8, 10, 10, [(18.5, 6.5)], 600),
    ("procedure lamp", 1, 50, 4, [(8, 18)], 30),
    ("oxygen concentrator", 1, 200, 4, [(8, 18)], 60),
    ("portable ultrasound", 1, 28, 1, [(8, 18)], 15),
    ("fetal heart monitor", 1, 3, 2, [(8, 18)], 15),
    ("television", 2, 100, 4, [(9, 13)], 60),
    ("DVD player", 2, 20, 1, [(9, 13)], 30),
    ("laptop", 1, 60, 6, [(9, 15)], 60),
    ("phone charging", 3, 10, 1, [(9, 18)], 30),
    ("USB modem", 1, 2.5, 6, [(9, 15)], 60),
    ("remote monitoring", 1, 5, 24, [(0, 24)], 1440),
]
# School closed (assumption): August, and two weeks each at Christmas and Easter
SCHOOL_CLOSED = [("2021-08-01", "2021-08-31"), ("2021-12-18", "2021-12-31"),
                 ("2021-01-01", "2021-01-03"), ("2021-04-01", "2021-04-14")]


# --- survey -------------------------------------------------------------------------------

def survey_households() -> pd.DataFrame:
    """One row per rural household and owned appliance type: count and reported hours."""
    folder = ds.mtf_nigeria()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ident = pd.read_stata(folder / "MTF_NG_HH_Identification.dta")[["HH_ID", "Urbanization"]]
        grid = pd.read_stata(folder / "MTF_NG_HH_SEC_C.dta")[["HH_ID", "C2"]]
        wt = pd.read_stata(ds.mtf_weights())[["HH_ID", "wt"]]
        assets = pd.read_stata(folder / "MTF_NG_HH_SEC_N_ELEC_ASSET.dta")
    hh = ident.merge(grid, on="HH_ID").merge(wt, on="HH_ID")
    hh = hh[hh.Urbanization.astype(str) == "Rural"].assign(on_grid=lambda d: d.C2.astype(str) == "Yes")
    a = assets[assets.own_asset.astype(str) == "Yes"].copy()
    a["item"] = a.item_id.astype(str)
    a["count"] = pd.to_numeric(a.N1A_N31A, errors="coerce").fillna(1).clip(1, 20).astype(int)
    a["hours"] = pd.to_numeric(a.N1B_N31B, errors="coerce")
    a = a[a.item.isin(APPLIANCES)][["HH_ID", "item", "count", "hours"]]
    return hh[["HH_ID", "on_grid", "wt"]], a


def sample_households(case: str, n: int = N_HOUSEHOLDS, seed: int = SEED):
    """Draw n survey households (weighted) for the 'low' or 'high' demand case."""
    hh, assets = survey_households()
    pool = hh if case == "low" else hh[hh.on_grid]
    rng = np.random.default_rng(seed)
    ids = rng.choice(pool.HH_ID.to_numpy(), size=n, replace=True, p=(pool.wt / pool.wt.sum()).to_numpy())
    return ids, assets


# --- RAMP helpers -----------------------------------------------------------------------------

def _windows_min(win):
    """[(a, b) hours] -> list of [start, end] minutes, splitting windows that wrap midnight."""
    out = []
    for a, b in win:
        a, b = int(round(a * 60)), int(round(b * 60))
        out += [[a, 1440], [0, b]] if b < a else [[a, b]]
    return out


def _add(user, name, number, watts, hours, win, cycle, wd_we=2):
    minutes = _windows_min(win)[:3]
    span = sum(b - a for a, b in minutes)
    func_time = int(min(round(hours * 60), span))
    if func_time <= 0 or number <= 0 or watts <= 0:
        return
    fill = func_time / span
    # Loads that fill their window (monitoring, security lights) are simply on for all of
    # it; loads that nearly fill it get less randomness, or RAMP cannot place them.
    # fixed="yes": all units of an appliance run together, so energy = count x watts x hours
    # (RAMP's default switches on a random subset and loses up to half the design energy).
    flat = "yes" if fill >= 0.95 else "no"
    r_t, r_w = (0.0, 0.0) if fill >= 0.7 else (0.2, 0.1)
    cycle = int(max(1, min(cycle, func_time if fill < 0.5 else func_time // 4)))
    app = user.add_appliance(number=int(number), power=float(watts), num_windows=len(minutes),
                             func_time=func_time, time_fraction_random_variability=r_t,
                             func_cycle=cycle, flat=flat, fixed="yes", wd_we_type=wd_we, name=name)
    kw = {f"window_{i + 1}": m for i, m in enumerate(minutes)}
    app.windows(random_var_w=r_w, **kw)


def _household_user(i, items: pd.DataFrame):
    from ramp import User
    user = User(user_name=f"hh{i}", num_users=1)
    for _, r in items.iterrows():
        spec = APPLIANCES[r["item"]]
        h = r["hours"] if pd.notna(r["hours"]) and r["hours"] > 0 else spec["hours"]
        if spec.get("kind") == "light":
            h = 7.0 if h is None else h  # survey median when a household gave no hours
            _add(user, r["item"], r["count"], spec["w"], min(h, LIGHT_MAIN_MAX), LIGHT_WIN, 30)
            _add(user, r["item"] + " (overnight)", r["count"], spec["w"], h - LIGHT_MAIN_MAX, LIGHT_OVERNIGHT, 60)
        elif spec.get("kind") == "tv":
            _add(user, r["item"], r["count"], spec["w"], min(h, TV_MAIN_MAX), TV_WIN, 30)
            _add(user, r["item"] + " (daytime)", r["count"], spec["w"], h - TV_MAIN_MAX, TV_EXTRA, 30)
        else:
            _add(user, r["item"], r["count"], spec["w"], h, spec["win"], spec["cycle"])
    return user


def _run(users, seed) -> pd.Series:
    """RAMP use case for one year -> hourly mean kW (local time)."""
    from ramp import UseCase
    logging.getLogger("ramp").setLevel(logging.ERROR)
    with warnings.catch_warnings():  # RAMP 0.5.2 emits pandas deprecation warnings
        warnings.simplefilter("ignore")
        uc = UseCase(users=users, date_start=f"{YEAR}-01-01", date_end=f"{YEAR}-12-31", random_seed=seed)
        minute_w = np.asarray(uc.generate_daily_load_profiles()).ravel()
    idx = pd.date_range(f"{YEAR}-01-01", periods=len(minute_w), freq="min")
    return pd.Series(minute_w / 1e3, index=idx).resample("h").mean()


# --- public -------------------------------------------------------------------------------------

def households(case: str, seed: int = SEED) -> pd.Series:
    """Hourly kW of all 312 households for the 'low' or 'high' case."""
    ids, assets = sample_households(case, seed=seed)
    by_hh = {k: g for k, g in assets.groupby("HH_ID")}
    users = [u for i, h in enumerate(ids)
             if (u := _household_user(i, by_hh.get(h, assets.iloc[0:0]))).App_list]
    return _run(users, seed).rename(f"households_{case}")


def school(seed: int = SEED) -> pd.Series:
    from ramp import User
    term = User(user_name="school", num_users=1)
    always = User(user_name="school_24h", num_users=1)
    for name, n, w, h, win, cyc, term_only in SCHOOL:
        _add(term if term_only else always, name, n, w, h, win, cyc, wd_we=0 if term_only else 2)
    teach, rest = _run([term], seed), _run([always], seed + 1)
    for a, b in SCHOOL_CLOSED:
        teach.loc[a:f"{b} 23:59"] = 0.0
    return (teach + rest).rename("school")


def clinic(case: str = "low", seed: int = SEED) -> pd.Series:
    from ramp import User
    user = User(user_name="clinic", num_users=1)
    for name, n, w, h, win, cyc in CLINIC:
        _add(user, name, n, w, h, win, cyc)
    p = _run([user], seed)
    if case == "high":
        p = p * CLINIC_HIGH_KWH_DAY / (p.sum() / 365)
    return p.rename(f"clinic_{case}")


def build_all(seed: int = SEED) -> pd.DataFrame:
    """All demand series in one frame (kW, hourly, local time)."""
    return pd.concat([households("low", seed), households("high", seed), school(seed),
                      clinic("low", seed), clinic("high", seed)], axis=1)
