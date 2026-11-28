# Cost table (approved 26 Nov 2026)

Exchange rate: **₦1,391.75 per US$**, CBN central rate, 25 Nov 2026 (reported by WithinNigeria and Galaxy TV; to confirm on cbn.gov.ng).
Finance: **10 % real discount rate, 20-year project life** (your choice; ESMAP's own modelling used 6.41 % real).

## Costs that the optimiser trades off

| Item | Value (US$) | Value (₦) | Source | Sweep |
|---|---|---|---|---|
| Solar PV, incl. PV inverter | $441 /kWp | ₦613,762 /kWp | ESMAP 2022, Table 1.4, median of 351 mini-grids | 25th-75th pct: $388-599 |
| Li-ion battery | $314 /kWh | ₦437,010 /kWh | ESMAP 2022, Table 1.4, median of 217 | $271-414 |
| Battery inverter + energy management | $415 /kW | ₦577,576 /kW | ESMAP 2022, Table 1.4, median of 313 | $325-716 |
| Diesel generator (equipment) | $172 /kW ($138 /kVA at pf 0.8) | ₦239,381 /kW | Esan et al. 2019 (Heliyon), Nigerian retail prices of 200/100/50 kVA sets, 2019, at ₦350/$ | none yet |
| Diesel fuel, delivered | ₦3,727.74 /L = $2.68 /L | | NBS Cross River price May 2026 (₦3,388.85, via Legit.ng) + 10 % transport (your choice) | planned diesel sweep |
| Generator fuel use | 0.339 L/kWh effective | | HOMER manual worked example (50 kW set: 0.273 L/kWh slope + 0.033 L/h per rated kW), evaluated at half load | |
| PV upkeep | $10 /kW per year | ₦13,918 | ESMAP 2022, note 12 | |
| Battery upkeep | $10 /kW per year | ₦13,918 | ESMAP 2022, note 12 | |
| Generator upkeep (non-fuel) | $0.03 /kWh | ₦41.75 /kWh | ESMAP 2022, note 12 | |

## Performance and lifetimes

| Item | Value | Source |
|---|---|---|
| Li-ion battery | 3,000 full cycles, 80 % depth of discharge, 90 % round trip | ESMAP 2022, Table 1.6 |
| Battery calendar life | at least 10 years | Esan et al. 2019, Table 3 |
| PV life | 25 years | Esan et al. 2019, Table 3 |
| Generator life | 15,000 operating hours | Esan et al. 2019, Table 3 |
| Battery inverter life | 10 years | assumption (author), flagged |

## Fixed costs (do not change the optimal mix, but do change cost per kWh)

| Item | Value | Source |
|---|---|---|
| Distribution network and meters | $250 per customer (median; 75th pct $331) | ESMAP 2022, Table 1.4 |
| Balance of system (genset, structures, fencing, civil works, powerhouse, cooling) | $340 per kWp of PV (2021 average, read from the chart) | ESMAP 2022, Figure 1.10 |
| Staff | $5,100 per year (3 staff, up to 500 customers) | ESMAP 2022, modelling assumptions |

## Known weaknesses

- The generator price is equipment only, from 2019 retail prices converted at the 2019 rate; installation is not included.
- The linear model cannot charge for running a generator at low load; the 0.339 L/kWh figure (0.273 + 0.033/0.5) is a compromise between full-load (about 0.31) and quarter-load (about 0.40) fuel use from the same curve.
- The diesel price is from May 2026, the exchange rate from November 2026.
