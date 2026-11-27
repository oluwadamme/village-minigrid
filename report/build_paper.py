"""Build report/village_minigrid_paper.html from paper_src.html: fills the related-work and
discussion sections, numbers citations [@key] in order of first use and writes the reference list.

    python report/build_paper.py report/paper_src.html report/village_minigrid_paper.html

Then print the HTML to PDF with Chrome (headless --print-to-pdf, no header/footer).
"""
RELATED = """<p>Most techno-economic studies of off-grid hybrid systems in Nigeria use HOMER [@homer]. Olatomiwa <i>et al.</i> [@olatomiwa15] compared hybrid systems for rural communities in each of Nigeria&rsquo;s six geo-political zones and found PV&ndash;diesel&ndash;battery systems to be the most economic, testing diesel prices of US$1.1 and 1.3/L. Esan <i>et al.</i> [@esan] designed a PV&ndash;diesel&ndash;battery system for Lade&nbsp;II in Kwara State (about 2.7&#8239;MWh/day) and assessed its reliability with a capacity outage probability table; with diesel at US$0.6/L the optimum combined 1.5&#8239;MW of PV with a 350&#8239;kW generator, at US$0.396/kWh. Ndukwe <i>et al.</i> [@ndukwe19] sized a hybrid system for Umuokpo Amumara in eastern Nigeria. Lewis <i>et al.</i> [@lewis24] studied a village in north-east Nigeria with about 610&#8239;kWh/day of demand and found a 99&#8239;% renewable system (375&#8239;kW PV, 869&#8239;kWh lead-acid storage, 15&#8239;kW generator) at US$0.093/kWh with diesel at US$1/L, varied from US$0.40 to 2.50/L. Rural health facilities, whose loads are critical, have been studied separately [@olatomiwa16], [@oladigbolu21].</p>
<p>Two points motivate the present study. First, most of these studies assume diesel prices of US$0.6&ndash;1.3/L, well below the current delivered price in Cross River, so their conclusions about the role of diesel may not carry over. Second, HOMER evaluates each candidate system with rule-based dispatch strategies [@homer], whereas open linear-programming capacity models such as PyPSA [@pypsa] optimise capacity and hourly dispatch together over a whole year. The linear-programming approach is transparent and scriptable, but its dispatch has perfect foresight of demand and weather. This study uses such a model and then operates the resulting design with a rule-based dispatch to measure the effect of that foresight.</p>"""

DISCUSSION = """<h3>A. Comparison with other designs</h3>
<p>The trend across the diesel-price sweep agrees with the studies reviewed in Section&nbsp;II. With diesel at US$0.6/L Esan <i>et al.</i> [@esan] retained a large generator; at US$1/L Lewis <i>et al.</i> [@lewis24] found a 99&#8239;% renewable system with a small generator, as this model does at the same price. Their reported costs of energy (US$0.093&ndash;0.396/kWh) differ widely from each other and from this study&rsquo;s, because the studies differ in load, cost inputs and system boundary; the value reported here includes distribution, balance of system and staff. RLI&rsquo;s own design for this cluster [@rli] includes a 77&#8239;kW generator. In the present model a generator of tens of kW is chosen only at US$0.50/L, which suggests that RLI assumed much cheaper diesel or a different reliability criterion.</p>
<h3>B. Implications</h3>
<p>At current diesel prices the planning question for a village of this kind is no longer whether to use solar, but how much storage to install. Diesel keeps a small role as a backup that protects the health centre and school through rainy spells, and that role only appears once the optimiser&rsquo;s perfect foresight is removed. For studies that size systems with linear programs, a no-foresight operating check is cheap and can change the design. A dedicated backup generator protects critical loads at lower cost to households than a battery reserve does (Table&nbsp;IV). The curtailed dry-season PV output is an opportunity for daytime productive uses such as grain milling or cold storage, which were not modelled.</p>"""

REFS = {
"nbs": "National Bureau of Statistics, &ldquo;Diesel Price Watch (May 2026),&rdquo; Abuja, Nigeria, 2026.",
"homer": "HOMER Energy, &ldquo;HOMER Pro user manual: generator fuel curve and dispatch strategies,&rdquo; [Online]. Available: homerenergy.com/products/pro/docs",
"olatomiwa15": "L. Olatomiwa, S. Mekhilef, A. S. N. Huda, and O. S. Ohunakin, &ldquo;Economic evaluation of hybrid energy systems for rural electrification in six geo-political zones of Nigeria,&rdquo; <i>Renew. Energy</i>, vol. 83, pp. 435&ndash;446, 2015, doi: 10.1016/j.renene.2015.04.057.",
"esan": "A. B. Esan, A. F. Agbetuyi, O. Oghorada, K. Ogbeide, A. A. Awelewa, and A. E. Afolabi, &ldquo;Reliability assessments of an islanded hybrid PV-diesel-battery system for a typical rural community in Nigeria,&rdquo; <i>Heliyon</i>, vol. 5, no. 5, Art. no. e01632, 2019, doi: 10.1016/j.heliyon.2019.e01632.",
"ndukwe19": "C. Ndukwe, M. T. Iqbal, X. Liang, and J. Khan, &ldquo;Optimal sizing and analysis of a small hybrid power system for Umuokpo Amumara in eastern Nigeria,&rdquo; <i>Int. J. Photoenergy</i>, vol. 2019, Art. no. 6960191, 2019, doi: 10.1155/2019/6960191.",
"lewis24": "C. G. Lewis, M. W. Ijeoma, R. O. Yakubu, B. N. Chukwu, H. Chen, and M. Carbajales-Dale, &ldquo;Achieving universal energy access in remote locations using HOMER energy model: a techno-economic and environmental analysis of hybrid microgrid systems for rural electrification in northeast Nigeria,&rdquo; <i>Front. Energy Res.</i>, vol. 12, Art. no. 1454281, 2024, doi: 10.3389/fenrg.2024.1454281.",
"olatomiwa16": "L. Olatomiwa, &ldquo;Optimal configuration assessments of hybrid renewable power supply for rural healthcare facilities,&rdquo; <i>Energy Rep.</i>, vol. 2, pp. 141&ndash;146, 2016, doi: 10.1016/j.egyr.2016.06.001.",
"oladigbolu21": "J. O. Oladigbolu, Y. A. Al-Turki, and L. Olatomiwa, &ldquo;Comparative study and sensitivity analysis of a standalone hybrid energy system for electrification of rural healthcare facility in Nigeria,&rdquo; <i>Alexandria Eng. J.</i>, vol. 60, no. 6, pp. 5547&ndash;5565, 2021, doi: 10.1016/j.aej.2021.04.042.",
"pypsa": "T. Brown, J. H&ouml;rsch, and D. Schlachtberger, &ldquo;PyPSA: Python for Power System Analysis,&rdquo; <i>J. Open Res. Softw.</i>, vol. 6, no. 1, p. 4, 2018, doi: 10.5334/jors.188.",
"rli": "Reiner Lemoine Institut and GIZ Nigerian Energy Support Programme, &ldquo;Rural electrification modelling for five Nigerian federal states: Cross River,&rdquo; dataset, CC BY-SA 4.0. [Online]. Available: energydata.info (accessed Nov. 2026).",
"pvgis": "European Commission Joint Research Centre, &ldquo;Photovoltaic Geographical Information System (PVGIS) 5.3: typical meteorological year,&rdquo; [Online]. Available: re.jrc.ec.europa.eu/pvg_tools (accessed Nov. 2026).",
"ramp": "F. Lombardi, S. Balderrama, S. Quoilin, and E. Colombo, &ldquo;Generating high-resolution multi-energy load profiles for remote areas with an open-source stochastic model,&rdquo; <i>Energy</i>, vol. 177, pp. 433&ndash;444, 2019, doi: 10.1016/j.energy.2019.04.097.",
"mtf": "World Bank ESMAP, &ldquo;Nigeria Multi-Tier Framework (MTF) survey 2018,&rdquo; dataset, CC BY 4.0. [Online]. Available: energydata.info (accessed Nov. 2026).",
"mtfbook": "M. Bhatia and N. Angelou, &ldquo;Beyond Connections: Energy Access Redefined,&rdquo; ESMAP, World Bank, Washington, DC, USA, 2015. [Online]. Available: hdl.handle.net/10986/24368",
"lg": "Lighting Global, &ldquo;PV system design tool and example designs,&rdquo; World Bank Group, 2023.",
"seforall": "Sustainable Energy for All, &ldquo;Nigeria roadmap: powering healthcare,&rdquo; Mar. 2022.",
"esmap": "ESMAP, <i>Mini Grids for Half a Billion People: Market Outlook and Handbook for Decision Makers</i>. Washington, DC, USA: World Bank, 2022. CC BY 3.0 IGO.",
"cbn": "Central Bank of Nigeria, &ldquo;Exchange rates: central rate, 25 November 2026,&rdquo; Abuja, Nigeria, 2026.",
"highs": "Q. Huangfu and J. A. J. Hall, &ldquo;Parallelizing the dual revised simplex method,&rdquo; <i>Math. Program. Comput.</i>, vol. 10, no. 1, pp. 119&ndash;142, 2018, doi: 10.1007/s12532-017-0130-5.",
"ipcc": "IPCC, <i>2006 IPCC Guidelines for National Greenhouse Gas Inventories</i>, vol. 2, <i>Energy</i>, ch. 2. Hayama, Japan: IGES, 2006.",
"huld": "T. Huld, R. M&uuml;ller, and A. Gambardella, &ldquo;A new solar radiation database for estimating PV performance in Europe and Africa,&rdquo; <i>Sol. Energy</i>, vol. 86, no. 6, pp. 1803&ndash;1815, 2012, doi: 10.1016/j.solener.2012.03.006.",
}

import re, sys
src, out = sys.argv[1], sys.argv[2]
s = open(src).read().replace("<!--RELATED-->", RELATED).replace("<!--DISCUSSION-->", DISCUSSION)
s = s.replace("[@pvgis]", "[@pvgis], [@huld]", 1)
order = []
for k in re.findall(r"\[@(\w+)\]", s):
    if k not in order: order.append(k)
missing = [k for k in order if k not in REFS]; unused = [k for k in REFS if k not in order]
assert not missing, missing
s = re.sub(r"\[@(\w+)\]", lambda m: f"[{order.index(m.group(1)) + 1}]", s)
refs = "\n".join(f'<div><span class="k">[{i+1}]</span><span class="t">{REFS[k]}</span></div>' for i, k in enumerate(order))
s = s.replace("<!--REFS-->", refs)
open(out, "w").write(s)
print(len(order), "refs; unused:", unused)
