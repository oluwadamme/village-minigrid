"""Sensitivity sweeps: how the least-cost design moves with the uncertain inputs.

Every point is the optimal hybrid (PV, battery and a main generator all allowed), then
operated with the no-foresight rule plus the clinic/school backup generator, exactly like
the final design in notebook 02. Results are for clinic 'low' unless stated.

Sweeps (agreed in the project plan):
    diesel      delivered price per litre, from cheap to well above today's
    battery     Li-ion cost -30 % / +30 % around the ESMAP median
    components  ESMAP 25th and 75th percentiles for PV, battery and inverter, each swept
                alone (others at the median); plus all three together as outer bounds
                (ESMAP's note says the percentiles should not be read together)
    reliability households may go without 0 %, 1 % or 5 % of their energy
    discount    real discount rate 6.41 % (ESMAP's), 10 % (base), 15 %
    growth      households grow 5 % a year in years 1-5, flat to year 20 (commercial and
                public loads do not grow). Size for today or for year 5; reported as the
                year-5 shortfall and as a lifetime delivered cost over 20 years.
Distribution cost is held at 312 customers throughout (it does not grow with demand).
"""
import numpy as np
import pandas as pd

import costs as cst
import model as m

DIESEL_PRICES = [0.50, 0.75, 1.00, 1.25, 1.50, 2.00, round(cst.diesel_usd_per_litre(), 2), 3.00]


def _point(load, pv, sweep, value, **case_kw) -> dict:
    case = m.Case(design="hybrid", **case_kw)
    n, s = m.solve(case, load, pv)
    f = m.final_design(n, s | {"case": case.name}, case, load, pv)
    return {"sweep": sweep, "value": value, "demand": case.demand, "clinic": case.clinic,
            "main diesel kW": s["diesel kW"], "diesel share % (optimised)": s["diesel share %"], **{k: v for k, v in f.items() if k != "case"}}


def diesel(demand, pv, dem):
    return [_point(demand, pv, "diesel $/L", p, demand=dem, cost_kw={"diesel_price": p}) for p in DIESEL_PRICES]


def diesel_only_lcoe(demand, pv, dem):
    """Cost per kWh of the diesel-only design at each price (optimised, generator only)."""
    out = []
    for p in DIESEL_PRICES:
        case = m.Case(design="diesel_only", demand=dem, cost_kw={"diesel_price": p})
        _, s = m.solve(case, demand, pv)
        out.append({"value": p, "demand": dem, "LCOE delivered $/kWh": s["LCOE delivered $/kWh"]})
    return out


def battery(demand, pv, dem):
    base = cst.COMPONENTS["battery_capex"][0]
    return [_point(demand, pv, "battery $/kWh", round(base * f), demand=dem, cost_kw={"battery_cost": base * f})
            for f in (0.7, 1.0, 1.3)]


def components(demand, pv, dem):
    """PV, battery and inverter cost percentiles one at a time, then all together."""
    pct = {"PV": ("pv_cost", "pv_capex"), "battery": ("battery_cost", "battery_capex"),
           "inverter": ("inverter_cost", "inverter_capex")}
    out = []
    for name, (kw, comp) in pct.items():
        for label, i in (("25th percentile", 0), ("75th percentile", 1)):
            out.append(_point(demand, pv, f"ESMAP cost: {name} only", label, demand=dem,
                              cost_kw={kw: cst.COMPONENTS[comp][3][i]}))
    for label, i in (("25th percentile", 0), ("median", None), ("75th percentile", 1)):
        kw = {} if i is None else {k: cst.COMPONENTS[c][3][i] for k, c in pct.values()}
        out.append(_point(demand, pv, "all components (bounds)", label, demand=dem, cost_kw=kw))
    return out


def reliability(demand, pv, dem):
    return [_point(demand, pv, "households unserved target %", 100 * u, demand=dem, unserved_share=u) for u in (0.0, 0.01, 0.05)]


def discount(demand, pv, dem):
    return [_point(demand, pv, "discount rate %", label, demand=dem, cost_kw={"rate": r})
            for label, r in (("6.41", 0.0641), ("10.0", cst.DISCOUNT_RATE), ("15.0", 0.15))]


GROWTH_RATE, GROWTH_YEARS = 0.05, 5


def _grown(demand, dem, year):
    g = demand.copy()
    g[f"households_{dem}"] = demand[f"households_{dem}"] * (1 + GROWTH_RATE) ** min(year, GROWTH_YEARS)
    return g


def lifetime_lcoe(n, s, case, demand, pv, dem, rate=cst.DISCOUNT_RATE) -> dict:
    """Delivered cost over the 20-year project: sum of discounted yearly costs / sum of
    discounted served energy. Capital is the same annualised charge every year; fuel,
    battery wear and served energy come from a rule run on each year's demand (years 5-20
    are identical, so six distinct runs). Year 0 is today's demand."""
    cost = energy = 0.0
    snap = {}
    for y in range(1, cst.PROJECT_YEARS + 1):
        k = min(y, GROWTH_YEARS)
        if k not in snap:
            snap[k] = m.final_design(n, s, case, _grown(demand, dem, k), pv)
        f = snap[k]
        df = (1 + rate) ** -y
        cost += f["total cost $/yr"] * df
        energy += f["served kWh/yr"] * df
    return {"lifetime LCOE delivered $/kWh": cost / energy}


def growth(demand, pv, dem):
    """Size for today, or for year 5; run through the growth path."""
    case = m.Case(design="hybrid", demand=dem)
    n_today, s_today = m.solve(case, demand, pv)
    grown5 = _grown(demand, dem, GROWTH_YEARS)
    n5, s5 = m.solve(case, grown5, pv)
    rows = []
    for label, n, s in (("sized for today", n_today, s_today), ("sized for year 5", n5, s5)):
        s = s | {"case": case.name}
        f = m.final_design(n, s, case, grown5, pv)            # year-5 snapshot
        rows.append({"sweep": "demand growth", "value": label, "demand": dem, "clinic": case.clinic,
                     "main diesel kW": s["diesel kW"], **{k: v for k, v in f.items() if k != "case"},
                     **lifetime_lcoe(n, s, case, demand, pv, dem)})
    return rows


def run_all(demand, pv) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, dsl = [], []
    for dem in ("low", "high"):
        rows += diesel(demand, pv, dem) + battery(demand, pv, dem) + components(demand, pv, dem)
        rows += reliability(demand, pv, dem) + discount(demand, pv, dem) + growth(demand, pv, dem)
        dsl += diesel_only_lcoe(demand, pv, dem)
    return pd.DataFrame(rows), pd.DataFrame(dsl)
