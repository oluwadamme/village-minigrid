# village-minigrid

**What is the cheapest reliable way to power an off-grid village in Cross River State, Nigeria?**

A solar mini-grid design study for Umon South (Biase LGA, Cross River State): about 312 households plus a primary health centre and a primary school. A model chooses the size of the solar panels, the battery and a diesel generator to keep the clinic and school always on at the lowest cost per kWh.

> Work in progress. A modelling study built on public data, not a site survey.

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
