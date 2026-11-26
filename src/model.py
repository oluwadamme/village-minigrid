"""Least-cost mini-grid design with PyPSA: sizes and hourly operation over one year.

Network (one AC bus, hourly, 8,760 steps, local time):
    PV            generator, size free, output <= size x PV-per-kWp profile
    battery       a store (kWh, free size, kept between 20 % and 100 % = 80 % depth of
                  discharge) connected through a two-way inverter (kW, free size, same
                  rating both ways), 90 % round trip split evenly between charging and
                  discharging
    diesel        generator, size free, linear fuel use (no minimum load: a stated limit)
    loads         critical (clinic + school): always served
                  households: may go unserved, but in total at most 5 % of their yearly
                  energy (base case). The 5 % is a design target, not a priced penalty;
                  unserved energy carries only a tiny tie-breaking cost (UNSERVED_TIEBREAK).
                  The optimisation knows the whole year's weather in advance, so it may
                  ration households while the battery still holds charge to get through a
                  coming cloudy spell. simulate_rule() re-runs the chosen sizes with a
                  simple rule and no foresight, to show what an operator would really get.
The objective is the yearly cost: annualised investments plus fuel and upkeep (costs.py).
Fixed costs (distribution, balance of system, staff) are added afterwards for the cost
per kWh; they do not change the design.

Designs: "diesel_only" (no PV, no battery), "pv_battery" (no diesel), "hybrid" (all).
"""
import logging
import os
from dataclasses import dataclass, field

os.environ.setdefault("TQDM_DISABLE", "1")  # no linopy progress bars (set before import)

import numpy as np
import pandas as pd
import pypsa

import costs as cst


CO2_KG_PER_L = 2.67   # diesel: IPCC 2006 default 74.1 t CO2/TJ x 36 MJ/L
CUSTOMERS = 312
UNSERVED_TIEBREAK = 0.01   # $/kWh, tie-breaker only (see docstring)
DESIGNS = ("diesel_only", "pv_battery", "hybrid")


@dataclass
class Case:
    design: str = "hybrid"
    demand: str = "high"            # households: "low" | "high"
    clinic: str = "low"             # clinic: "low" | "high"
    unserved_share: float = 0.05    # max share of household energy not served
    cost_kw: dict = field(default_factory=dict)  # overrides for costs.annual_costs()

    @property
    def name(self) -> str:
        return f"{self.design} | demand {self.demand} | clinic {self.clinic}"


def build(case: Case, demand: pd.DataFrame, pv_per_kwp: pd.Series) -> pypsa.Network:
    c = cst.annual_costs(**case.cost_kw)
    hh = demand[f"households_{case.demand}"].to_numpy()
    critical = (demand["school"] + demand[f"clinic_{case.clinic}"]).to_numpy()
    n = pypsa.Network()
    n.set_snapshots(demand.index)
    for carrier, co2 in [("solar", 0), ("battery", 0), ("diesel", 0), ("unserved", 1), ("AC", 0)]:
        n.add("Carrier", carrier, co2_emissions=co2)   # 'co2' only tags unserved energy
    n.add("Bus", "village", carrier="AC")
    n.add("Load", "critical", bus="village", p_set=critical)
    n.add("Load", "households", bus="village", p_set=hh)

    # unserved household energy: a free 'generator' limited to the household load each hour
    n.add("Generator", "unserved", bus="village", carrier="unserved", p_nom=hh.max(),
          p_max_pu=hh / hh.max(), marginal_cost=UNSERVED_TIEBREAK)
    n.add("GlobalConstraint", "reliability", type="primary_energy", carrier_attribute="co2_emissions",
          sense="<=", constant=case.unserved_share * hh.sum())

    if case.design in ("pv_battery", "hybrid"):
        n.add("Generator", "pv", bus="village", carrier="solar", p_nom_extendable=True,
              p_max_pu=pv_per_kwp.to_numpy(), capital_cost=c["pv_per_kwp_yr"])
        eta = np.sqrt(cst.BATTERY["round_trip"])
        n.add("Bus", "battery", carrier="battery")
        n.add("Store", "battery", bus="battery", carrier="battery", e_nom_extendable=True, e_cyclic=True,
              e_min_pu=1 - cst.BATTERY["depth_of_discharge"], capital_cost=c["battery_per_kwh_yr"])
        n.add("Link", "inverter discharge", bus0="battery", bus1="village", carrier="battery",
              efficiency=eta, p_nom_extendable=True, capital_cost=c["inverter_per_kw_yr"])
        n.add("Link", "inverter charge", bus0="village", bus1="battery", carrier="battery",
              efficiency=eta, p_nom_extendable=True, capital_cost=0.0)
    if case.design in ("diesel_only", "hybrid"):
        n.add("Generator", "diesel", bus="village", carrier="diesel", p_nom_extendable=True,
              capital_cost=c["genset_per_kw_yr"], marginal_cost=c["genset_per_kwh"])
    return n


def _same_inverter_both_ways(n, snapshots):
    """One two-way inverter: the charging rating equals the (paid) discharging rating."""
    if "inverter charge" not in n.links.index:
        return
    p_nom = n.model.variables["Link-p_nom"]
    n.model.add_constraints(p_nom.loc["inverter charge"] == p_nom.loc["inverter discharge"],
                            name="inverter_two_way")


def solve(case: Case, demand: pd.DataFrame, pv_per_kwp: pd.Series) -> tuple[pypsa.Network, dict]:
    n = build(case, demand, pv_per_kwp)
    logging.getLogger("pypsa").setLevel(logging.ERROR)
    logging.getLogger("linopy").setLevel(logging.ERROR)
    status, cond = n.optimize(solver_name="highs", extra_functionality=_same_inverter_both_ways,
                              log_to_console=False)
    if status != "ok":
        raise RuntimeError(f"{case.name}: solver {status} / {cond}")
    return n, summarise(n, case)


def summarise(n: pypsa.Network, case: Case) -> dict:
    c = cst.annual_costs(**case.cost_kw)
    gen = n.generators_t.p
    hh_load, crit_load = n.loads_t.p["households"], n.loads_t.p["critical"]
    unserved = gen["unserved"].sum()
    served = hh_load.sum() + crit_load.sum() - unserved
    size = lambda comp, name, attr: getattr(n, comp).at[name, attr] if name in getattr(n, comp).index else 0.0
    pv_kwp, diesel_kw = size("generators", "pv", "p_nom_opt"), size("generators", "diesel", "p_nom_opt")
    bat_kwh, inv_kw = size("stores", "battery", "e_nom_opt"), size("links", "inverter discharge", "p_nom_opt")
    diesel_kwh = gen["diesel"].sum() if "diesel" in gen else 0.0
    pv_kwh = gen["pv"].sum() if "pv" in gen else 0.0
    discharged = n.links_t.p1["inverter discharge"].abs().sum() if inv_kw else 0.0
    usable = bat_kwh * cst.BATTERY["depth_of_discharge"]

    # yearly cost recomputed from sizes and flows, independently of PyPSA's objective
    yearly = (pv_kwp * c["pv_per_kwp_yr"] + bat_kwh * c["battery_per_kwh_yr"] + inv_kw * c["inverter_per_kw_yr"]
              + diesel_kw * c["genset_per_kw_yr"] + diesel_kwh * c["genset_per_kwh"])
    fixed = sum(cst.fixed_annual(CUSTOMERS, (hh_load + crit_load).max()).values())
    litres = diesel_kwh * cst.FUEL_L_PER_KWH
    # Battery wear: 3,000 full cycles. If it cycles more than 300 times a year it dies before
    # its 10-year calendar life; re-annualise its cost over the shorter life (after the fact,
    # so the design itself still assumes 10 years).
    cycles = discharged / usable if usable else 0.0
    bat_life = min(cst.LIFETIME_YEARS["battery"], cst.BATTERY["cycles"] / cycles) if cycles else cst.LIFETIME_YEARS["battery"]
    bat_extra = bat_kwh * cst.COMPONENTS["battery_capex"][0] * (cst.crf(bat_life) - cst.crf(cst.LIFETIME_YEARS["battery"])) if bat_kwh else 0.0
    # When households lose power: hours with any shortfall, longest run, worst month
    short = gen["unserved"] > 1e-6
    runs = (short != short.shift()).cumsum()[short]
    longest = int(runs.value_counts().max()) if short.any() else 0
    monthly = gen["unserved"].groupby(gen.index.month).sum()
    return {
        "case": case.name, "design": case.design, "demand": case.demand, "clinic": case.clinic,
        "PV kWp": pv_kwp, "battery kWh": bat_kwh, "inverter kW": inv_kw, "diesel kW": diesel_kw,
        "demand kWh/yr": hh_load.sum() + crit_load.sum(), "served kWh/yr": served,
        "unserved % of households": 100 * unserved / hh_load.sum(),
        "diesel share %": 100 * diesel_kwh / served, "PV curtailed %": 100 * (1 - pv_kwh / (pv_kwp * n.generators_t.p_max_pu["pv"].sum())) if pv_kwp else 0.0,
        "battery full cycles/yr": cycles, "battery life years": bat_life,
        "hours with household shortfall": int(short.sum()), "longest shortfall h": longest,
        "worst month for shortfall": int(monthly.idxmax()) if short.any() else None,
        "diesel litres/yr": litres, "CO2 t/yr": litres * CO2_KG_PER_L / 1000,
        "generation cost $/yr": yearly, "objective $/yr": n.objective, "fixed cost $/yr": fixed,
        "battery wear extra $/yr": bat_extra,
        "LCOE generation $/kWh": (yearly + bat_extra) / served,
        "LCOE delivered $/kWh": (yearly + bat_extra + fixed) / served,
        "LCOE delivered N/kWh": (yearly + bat_extra + fixed) / served * cst.FX_NGN_PER_USD,
    }


def check(n: pypsa.Network, s: dict, tol: float = 1e-3) -> dict:
    """Hand checks: energy balance every hour, battery limits, cost recomputed outside PyPSA."""
    supply = n.generators_t.p.sum(axis=1)
    if "inverter discharge" in n.links.index:
        supply = supply + n.links_t.p1["inverter discharge"].abs() - n.links_t.p0["inverter charge"]
    balance = (supply - n.loads_t.p.sum(axis=1)).abs().max()
    expected = s["generation cost $/yr"] + UNSERVED_TIEBREAK * n.generators_t.p["unserved"].sum()
    out = {"max hourly imbalance kW": balance,
           "cost recomputed vs objective (rel. diff)": abs(expected - s["objective $/yr"]) / s["objective $/yr"]}
    if "battery" in n.stores.index and s["battery kWh"] > 0:
        e = n.stores_t.e["battery"]
        out["battery min / max state (share of size)"] = (e.min() / s["battery kWh"], e.max() / s["battery kWh"])
    out["ok"] = balance < tol * max(1, n.loads_t.p.sum(axis=1).max()) and out["cost recomputed vs objective (rel. diff)"] < 1e-4
    return out


def run_cases(demand: pd.DataFrame, pv_per_kwp: pd.Series, cases: list[Case]) -> tuple[pd.DataFrame, dict]:
    """Solve and check every case. Returns (summary table, {case name: network})."""
    rows, nets = [], {}
    for case in cases:
        n, s = solve(case, demand, pv_per_kwp)
        ch = check(n, s)
        if not ch["ok"]:
            raise RuntimeError(f"{case.name}: checks failed {ch}")
        s["checks ok"] = True
        rows.append(s)
        nets[case.name] = n
    return pd.DataFrame(rows).set_index("case"), nets


def main_cases() -> list[Case]:
    return [Case(design=d, demand=dm, clinic=cl) for dm in ("low", "high") for cl in ("low", "high")
            for d in DESIGNS]


def simulate_rule(n: pypsa.Network, case: Case, demand: pd.DataFrame, pv_per_kwp: pd.Series,
                  reserve_share: float = 0.0, backup_kw: float = 0.0) -> dict:
    """Operate the optimised sizes hour by hour with no foresight.

    Rule: solar serves the load first; surplus charges the battery (inverter limit);
    a deficit is met from the battery down to its 20 % floor (inverter limit), then from
    the generator if there is one; whatever is still missing is cut from households first
    and from the clinic and school only as a last resort.

    reserve_share: households are served from the battery only while its charge is above
        this share of its size; below it, the battery is kept for the clinic and school.
    backup_kw: an extra small generator that serves only the clinic and school, and only
        when the battery cannot.
    """
    get = lambda comp, name, attr: getattr(n, comp).at[name, attr] if name in getattr(n, comp).index else 0.0
    pv_kwp, gen_kw = get("generators", "pv", "p_nom_opt"), get("generators", "diesel", "p_nom_opt")
    cap, inv = get("stores", "battery", "e_nom_opt"), get("links", "inverter discharge", "p_nom_opt")
    eta = np.sqrt(cst.BATTERY["round_trip"])
    floor = cap * (1 - cst.BATTERY["depth_of_discharge"])
    hh = demand[f"households_{case.demand}"].to_numpy()
    crit = (demand["school"] + demand[f"clinic_{case.clinic}"]).to_numpy()
    pv = pv_kwp * pv_per_kwp.to_numpy()
    e = cap  # start full
    hh_cut = crit_cut = diesel = 0.0
    hh_hours = crit_hours = 0
    for t in range(len(hh)):
        need = hh[t] + crit[t] - pv[t]
        if need <= 0:
            e = min(cap, e + min(-need, inv) * eta)
            continue
        # critical part of the deficit can use the battery down to its floor; the household
        # part only down to the reserve
        crit_need = max(0.0, min(need, crit[t] - pv[t])) if pv[t] < crit[t] else 0.0
        hh_need = need - crit_need
        reserve = max(floor, cap * reserve_share)
        from_bat_hh = min(hh_need, inv, max(0.0, (e - reserve) * eta))
        from_bat_cr = min(crit_need, inv - from_bat_hh, max(0.0, (e - from_bat_hh / eta - floor) * eta)) if eta else 0.0
        e -= (from_bat_hh + from_bat_cr) / eta if eta else 0
        hh_need -= from_bat_hh; crit_need -= from_bat_cr
        g = min(hh_need + crit_need, gen_kw); diesel += g
        take_cr = min(g, crit_need); crit_need -= take_cr; hh_need -= g - take_cr
        b = min(crit_need, backup_kw); diesel += b; crit_need -= b
        if hh_need > 1e-9:
            hh_cut += hh_need; hh_hours += 1
        if crit_need > 1e-9:
            crit_cut += crit_need; crit_hours += 1
    return {"unserved % of households (rule)": 100 * hh_cut / hh.sum(),
            "hours with household shortfall (rule)": hh_hours,
            "clinic/school kWh not served (rule)": crit_cut, "clinic/school hours cut (rule)": crit_hours,
            "diesel share % (rule)": 100 * diesel / (hh.sum() + crit.sum()),
            "diesel kWh (rule)": diesel, "served kWh (rule)": hh.sum() + crit.sum() - hh_cut - crit_cut}


def final_design(n: pypsa.Network, s: dict, case: Case, demand: pd.DataFrame, pv_per_kwp: pd.Series) -> dict:
    """The optimised sizes plus a small backup generator for the clinic and school only.

    The optimisation keeps the clinic on with perfect foresight; run with a simple rule it
    would not. A backup generator sized to the clinic + school peak (rounded up to whole
    kW) closes that gap. Its capital, fuel, upkeep and wear are added to the yearly cost,
    and every result here comes from the no-foresight rule, not the optimisation.
    """
    crit = demand["school"] + demand[f"clinic_{case.clinic}"]
    backup_kw = float(np.ceil(crit.max()))
    r = simulate_rule(n, case, demand, pv_per_kwp, backup_kw=backup_kw)
    c = cst.annual_costs(**case.cost_kw)
    backup_cost = backup_kw * c["genset_per_kw_yr"] + r["diesel kWh (rule)"] * c["genset_per_kwh"]
    litres = r["diesel kWh (rule)"] * cst.FUEL_L_PER_KWH
    total = s["generation cost $/yr"] + s["battery wear extra $/yr"] + s["fixed cost $/yr"] + backup_cost
    return {"case": s["case"], "PV kWp": s["PV kWp"], "battery kWh": s["battery kWh"], "inverter kW": s["inverter kW"],
            "main diesel kW": s["diesel kW"], "backup generator kW": backup_kw,
            "households unserved %": r["unserved % of households (rule)"],
            "hours with household shortfall": r["hours with household shortfall (rule)"],
            "clinic/school hours cut": r["clinic/school hours cut (rule)"],
            "diesel litres/yr": litres, "CO2 t/yr": litres * CO2_KG_PER_L / 1000,
            "backup cost $/yr": backup_cost, "total cost $/yr": total,
            "LCOE delivered $/kWh": total / r["served kWh (rule)"],
            "LCOE delivered N/kWh": total / r["served kWh (rule)"] * cst.FX_NGN_PER_USD}
