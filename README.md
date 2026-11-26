# village-minigrid

**What is the cheapest reliable way to power an off-grid village in Cross River State, Nigeria?**

A solar mini-grid design study for Umon South (Biase LGA, Cross River State): about 312 households plus a primary health centre and a primary school. A model chooses the size of the solar panels, the battery and a diesel generator to keep the clinic and school always on at the lowest cost per kWh.

> Work in progress. A modelling study built on public data, not a site survey. Least-cost designs assume one typical weather year.

## Data sources

| Data | Source | Licence |
|---|---|---|
| Village cluster (customers, population, facilities, grid distance) | Reiner Lemoine Institut / GIZ Nigerian Energy Support Programme, *Rural Electrification Modelling for five Nigerian Federal States*, on [energydata.info](https://energydata.info/dataset/rural-electrification-modelling-for-five-nigerian-federal-states) | CC BY-SA 4.0 |
| Household energy use | World Bank ESMAP, *Multi-Tier Framework survey, Nigeria 2018*, on [energydata.info](https://energydata.info/en/dataset/nigeria-multi-tier-framework-mtf-survey-59) | CC BY 4.0 |
| Health centre load (high case) | SEforALL, [*Nigeria roadmap: powering healthcare*](https://www.seforall.org/system/files/2022-03/nigeria-roadmap-powering-healthcare-March-22.pdf): Type 2 PHC, about 36 kWh/day | cited |
| School and clinic appliance lists, most wattages | Lighting Global, [*PV System Design Tool and Example Designs*](https://www.lightingglobal.org/wp-content/uploads/2023/03/PV-System-Design-Tool-and-Example-Designs.pdf) (Nigerian school and clinic designs, FCT) | cited |
| Radio, freezer, blender wattages; demand tool | [RAMP](https://github.com/RAMP-project/RAMP) (Lombardi et al. 2019) example inputs and model | EUPL-1.2 |
| Equipment costs, battery performance, upkeep, staff | World Bank ESMAP, [*Mini Grids for Half a Billion People*](https://openknowledge.worldbank.org/entities/publication/b53273b6-b19a-578e-8949-8dc5c7a3cd79) (2022) | CC BY 3.0 IGO |
| Diesel generator price and lifetimes | Esan et al., [*Heliyon* 5(5) e01632](https://pmc.ncbi.nlm.nih.gov/articles/PMC6517602/) (2019) | CC BY |
| Generator fuel curve | HOMER Pro manual, generator fuel curve example | cited |
| Diesel price | National Bureau of Statistics, Diesel Price Watch, Cross River, May 2026 | cited |
| Exchange rate | Central Bank of Nigeria central rate, 25 Nov 2026 (₦1,391.75 per US$) | cited |
| Solar | EU JRC [PVGIS 5.3](https://re.jrc.ec.europa.eu/pvg_tools/en/) typical year (SARAH3, 2005-2023) | free to use, cited |

Raw files are downloaded by script into `data/` and are not stored in this repo.

## Progress

**Notebook 01 (site and demand)** builds one year of hourly solar output and village demand:

- Solar: about 1,450 kWh per kWp a year, dipping to about 3.1 kWh/kWp/day in July (rainy season).
- Demand, two cases: **low** about 136 kWh/day (households like the average rural survey household, most not yet electrified) and **high** about 568 kWh/day (households like rural households already on the grid). The evening peak is at 21:00-22:00, after sunset.

Assumptions of my own, not from a published source:
- Cross River households use electricity like the North-West households in the survey.
- Nameplate wattages for irons (1,000 W), kettles (1,500 W), incandescent bulbs (60 W), CFLs (15 W) and fluorescent tubes (36 W).
- Usage windows for each appliance (in `src/demand.py`).
- The school calendar (closed in August and two weeks each at Christmas and Easter).
- A 10 % surcharge on the state diesel price for delivery to the village.
- A 10-year life for the battery inverter.
- ESMAP's balance-of-system cost ($524/kW) applied per kW of peak demand (ESMAP does not state the unit basis).

**Costs** are in [`docs/cost_table.md`](docs/cost_table.md) and `src/costs.py`, every number with its source. Diesel delivered to the village is about $2.68 per litre (₦3,728), so electricity from the generator costs about $0.94 per kWh, against about $0.04 per kWh of solar output before storage.

**Notebook 02 (optimal mix)** sizes the system with PyPSA for 3 designs x 2 household-demand cases x 2 clinic cases. Every run passes hand checks: supply equals demand every hour, the battery stays in its limits, and the cost recomputed outside PyPSA matches the solver.

![Cost per kWh by design](figures/lcoe_by_design.png)

- **At today's diesel price (about $2.68 a litre delivered) the least-cost design is solar plus battery.** The optimiser builds no main generator in any case. Diesel only would cost $1.03-1.26 per kWh.
- **The optimiser cheats a little: it knows the weather in advance.** It keeps the clinic and school on by rationing households before cloudy spells. Run hour by hour with a simple rule and no foresight, the same system would cut the clinic and school for about 330 hours a year.
- **Fix: a 3-5 kW backup generator for the clinic and school only.** It keeps them on in every hour, burns 60-100 litres of diesel a year and adds about $220-380 a year.

| Final design | Low household demand | High household demand |
|---|---|---|
| Solar PV | 54-62 kWp | 209-217 kWp |
| Battery (Li-ion) | 133-141 kWh | 558-565 kWh |
| Battery inverter | 16-17 kW | 65-67 kW |
| Backup generator (clinic and school only) | 3-5 kW | 3-5 kW |
| Households' energy not served | 4.3-4.6 % | 4.8-4.9 % |
| Delivered cost per kWh | $0.52-0.57 (₦723-786) | $0.34 (₦468-475) |

![A dry-season and a rainy-season week](figures/dispatch_weeks.png)

RLI's own design for this cluster (96 kWp, 168 kWh, 77 kW generator; units not stated) was made under different, unstated assumptions, most likely much cheaper diesel.

**Notebook 03 (sensitivity)** moves one uncertain input at a time (38 optimisations).

![Diesel price sweep](figures/diesel_price_sweep.png)

- **The solar design is insulated from the diesel price; diesel-only is not.** Above about $1.50 a litre the optimum has no main generator and costs about $0.34 per kWh (high demand) whatever diesel costs. Diesel-only rises from about $0.32 to $1.14 per kWh over the same range.
- **A main generator only pays with cheap diesel.** At $0.50 a litre the optimum is diesel-led; at ESMAP's 2022 assumption of $1 it is already under 1 kW. RLI's 77 kW generator therefore implies diesel well under $1 a litre, or other assumptions.
- **Equipment cost is the biggest remaining uncertainty.** ESMAP's 25th to 75th percentile costs give $0.31-0.43 per kWh (high demand). The sizes hardly change; the price does.

  ![What moves the cost](figures/sensitivity_range.png)

- **Full reliability is cheap.** Designing for 0 % household shortfall instead of 5 % adds only about 2 US cents per kWh, but without foresight even that design leaves households about 1.5-2.5 % short.
- **Size for growth.** Built for today and run with 5 years of 5 % yearly growth, the system leaves households about a fifth of their energy short. Sized for year 5 (about 264 kWp and 710 kWh, high demand) it costs about the same per kWh.
