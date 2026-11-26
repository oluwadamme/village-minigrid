"""Sensitivity sweeps: how the least-cost design moves with the uncertain inputs.

Every point is the optimal hybrid (PV, battery and a main generator all allowed), then
operated with the no-foresight rule plus the clinic/school backup generator, exactly like
the final design in notebook 02. Results are for clinic 'low' unless stated.

Sweeps (agreed in the project plan):
    diesel      delivered price per litre, from cheap to well above today's
    battery     Li-ion cost -30 % / +30 % around the ESMAP median
    components  ESMAP 25th and 75th percentiles for PV, battery and inverter together
    reliability households may go without 0 %, 1 % or 5 % of their energy
    growth      household demand +5 % a year for 5 years: size for today, or for year 5
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
    out = []
    for label, i in (("25th percentile", 0), ("median", None), ("75th percentile", 1)):
        kw = {} if i is None else {"pv_cost": cst.COMPONENTS["pv_capex"][3][i], "battery_cost": cst.COMPONENTS["battery_capex"][3][i],
                                   "inverter_cost": cst.COMPONENTS["inverter_capex"][3][i]}
        out.append(_point(demand, pv, "ESMAP component costs", label, demand=dem, cost_kw=kw))
    return out


def reliability(demand, pv, dem):
    return [_point(demand, pv, "households unserved target %", 100 * u, demand=dem, unserved_share=u) for u in (0.0, 0.01, 0.05)]


def growth(demand, pv, dem, rate=0.05, years=5):
    """Size for today and run 5 years of growth through it, or size for year 5."""
    grown = demand.copy()
    grown[f"households_{dem}"] = demand[f"households_{dem}"] * (1 + rate) ** years
    case = m.Case(design="hybrid", demand=dem)
    n_today, s_today = m.solve(case, demand, pv)
    f_today = m.final_design(n_today, s_today | {"case": case.name}, case, grown, pv)   # today's sizes, year-5 demand
    n5, s5 = m.solve(case, grown, pv)
    f5 = m.final_design(n5, s5 | {"case": case.name}, case, grown, pv)
    rows = []
    for label, f in (("sized for today, run in year 5", f_today), ("sized for year 5", f5)):
        rows.append({"sweep": "demand growth", "value": label, "demand": dem, "clinic": case.clinic,
                     **{k: v for k, v in f.items() if k != "case"}})
    return rows


def run_all(demand, pv) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, dsl = [], []
    for dem in ("low", "high"):
        rows += diesel(demand, pv, dem) + battery(demand, pv, dem) + components(demand, pv, dem)
        rows += reliability(demand, pv, dem) + growth(demand, pv, dem)
        dsl += diesel_only_lcoe(demand, pv, dem)
    return pd.DataFrame(rows), pd.DataFrame(dsl)
