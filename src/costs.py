"""Cost and performance assumptions, each with its source. Approved by the author 26 Nov 2026.

Money is in US$ (2021-2026 values as published, not inflated); Naira at the CBN central
rate of 25 Nov 2026. Sources:
    ESMAP 2022  World Bank ESMAP, Mini Grids for Half a Billion People (2022), CC BY 3.0 IGO
    Esan 2019   Esan et al., Reliability assessments of an islanded hybrid PV-diesel-battery
                system for a typical rural community in Nigeria, Heliyon 5(5) e01632 (2019)
    HOMER       HOMER Pro manual, generator fuel curve worked example (50 kW set)
    NBS         National Bureau of Statistics, Diesel Price Watch, May 2026 (via Legit.ng)
    CBN         Central Bank of Nigeria central rate, 25 Nov 2026 (via WithinNigeria)
    ASSUMPTION  mine, flagged in the README

How costs enter the optimisation (method, stated in the README):
- Every investment becomes an equivalent annual cost: capex x CRF(10 %, component life).
  Components living past the 20-year project are treated the same way (no salvage term).
- Battery: annualised over its 10-year calendar life; cycling is checked afterwards
  against 3,000 full cycles (300 a year over 10 years).
- Generator: annualised over the 20-year project, plus a wear cost per operating hour
  (capex / 15,000 h) turned into a cost per kWh at half load, added to fuel and upkeep.
"""
FX_NGN_PER_USD = 1391.75          # CBN central rate, 25 Nov 2026
DISCOUNT_RATE = 0.10              # real, author's choice (ESMAP used 6.41 % real)
PROJECT_YEARS = 20

COMPONENTS = {
    # name: value, unit, source, (low, high) for the cost sweep
    "pv_capex":         (441, "$/kWp", "ESMAP 2022 Table 1.4 median (incl. PV inverter)", (388, 599)),
    "battery_capex":    (314, "$/kWh", "ESMAP 2022 Table 1.4 median, Li-ion", (271, 414)),
    "inverter_capex":   (415, "$/kW", "ESMAP 2022 Table 1.4 median, inverter + EMS", (325, 716)),
    "genset_capex":     (172, "$/kW", "Esan 2019: $48,286 for 350 kVA, at pf 0.8; equipment only", None),
    "pv_om":            (10, "$/kW/yr", "ESMAP 2022 note 12", None),
    "battery_om":       (10, "$/kW/yr", "ESMAP 2022 note 12 (per kW of inverter)", None),
    "genset_om":        (0.03, "$/kWh", "ESMAP 2022 note 12, non-fuel", None),
}
LIFETIME_YEARS = {"pv": 25, "battery": 10, "inverter": 10}   # Esan 2019; inverter ASSUMPTION
GENSET_LIFE_HOURS = 15_000                                     # Esan 2019 Table 3

BATTERY = {"cycles": 3000, "depth_of_discharge": 0.80, "round_trip": 0.90}  # ESMAP 2022 Table 1.6

DIESEL_NGN_PER_L_STATE = 3388.85   # NBS, Cross River, May 2026
TRANSPORT_SURCHARGE = 0.10         # ASSUMPTION (author's choice): delivery to the village
FUEL_L_PER_KWH = 0.33              # HOMER curve (0.273 L/kWh + 0.033 L/h per rated kW) at half load

FIXED = {
    "distribution_per_customer": (250, "$/customer", "ESMAP 2022 Table 1.4 median, distribution and meters"),
    "bos_per_kw_peak": (524, "$/kW", "ESMAP 2022 text near Fig. 1.10, 2021 average BOS; unit basis not "
                                     "stated, applied per kW of peak demand (ASSUMPTION)"),
    "staff_per_year": (5100, "$/yr", "ESMAP 2022 modelling assumptions, 3 staff up to 500 customers"),
}


def crf(years: float, rate: float = DISCOUNT_RATE) -> float:
    """Capital recovery factor: turns an upfront cost into an equal annual cost."""
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


def diesel_usd_per_litre() -> float:
    return DIESEL_NGN_PER_L_STATE * (1 + TRANSPORT_SURCHARGE) / FX_NGN_PER_USD


def annual_costs(pv_cost: float | None = None, battery_cost: float | None = None,
                 inverter_cost: float | None = None, diesel_price: float | None = None) -> dict:
    """Costs in the form the optimiser needs (US$). Arguments override the base values."""
    c = {k: v[0] for k, v in COMPONENTS.items()}
    pv = pv_cost or c["pv_capex"]
    bat = battery_cost or c["battery_capex"]
    inv = inverter_cost or c["inverter_capex"]
    fuel = diesel_usd_per_litre() if diesel_price is None else diesel_price
    gen_wear_per_kwh = c["genset_capex"] / GENSET_LIFE_HOURS / 0.5   # at half load
    return {
        "pv_per_kwp_yr": pv * crf(LIFETIME_YEARS["pv"]) + c["pv_om"],
        "battery_per_kwh_yr": bat * crf(LIFETIME_YEARS["battery"]),
        "inverter_per_kw_yr": inv * crf(LIFETIME_YEARS["inverter"]) + c["battery_om"],
        "genset_per_kw_yr": c["genset_capex"] * crf(PROJECT_YEARS),
        "genset_per_kwh": fuel * FUEL_L_PER_KWH + c["genset_om"] + gen_wear_per_kwh,
        "fuel_usd_per_l": fuel,
    }


def fixed_annual(customers: int, peak_kw: float) -> dict:
    """Costs that do not depend on the generation mix (US$/yr)."""
    dist = FIXED["distribution_per_customer"][0] * customers
    bos = FIXED["bos_per_kw_peak"][0] * peak_kw
    return {"distribution": dist * crf(PROJECT_YEARS), "balance_of_system": bos * crf(PROJECT_YEARS),
            "staff": FIXED["staff_per_year"][0]}


def table() -> "pd.DataFrame":
    """Every assumption with its source, US$ and Naira, for the README and notebooks."""
    import pandas as pd
    rows = [{"item": k, "value": v[0], "unit": v[1], "naira": v[0] * FX_NGN_PER_USD if "$" in v[1] else None,
             "source": v[2], "sweep": v[3]} for k, v in COMPONENTS.items()]
    rows += [{"item": k, "value": v[0], "unit": v[1], "naira": v[0] * FX_NGN_PER_USD, "source": v[2], "sweep": None}
             for k, v in FIXED.items()]
    rows += [{"item": "diesel delivered", "value": round(diesel_usd_per_litre(), 3), "unit": "$/L",
              "naira": DIESEL_NGN_PER_L_STATE * (1 + TRANSPORT_SURCHARGE), "source": "NBS May 2026 + 10 % transport", "sweep": "planned"}]
    return pd.DataFrame(rows)
