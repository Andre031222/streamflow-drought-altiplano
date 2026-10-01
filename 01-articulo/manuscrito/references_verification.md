# Reference verification log

Checked on 2026-09-30 against the Crossref REST API (`api.crossref.org/works/<DOI>`) and, for Zenodo DOIs, the DataCite API (`api.datacite.org/dois/<DOI>`). `references.bib` has 60 entries and compiles under `spmpsci.bst` with no BibTeX warnings.

Legend: **yes** means the metadata matched. **fixed** means the DOI resolved but some metadata was wrong and has been corrected. **new** means the entry was added and verified. **no-DOI** means the work has no DOI.

## Entry table

| key | DOI | verified | note |
|---|---|---|---|
| aguayo2026andeangc | 10.5281/zenodo.18035801 | fixed | DataCite lists 7 creators: Aguayo, Zekollari, van Tiel, Bolibar, Van Tricht, Ayala Ramos, Ultee. They replace "Aguayo and others". The version field is **empty** for this DOI (issued 2026-01-01), so "v1.0" was removed. Note that this is a version DOI. The concept DOI is 10.5281/zenodo.18035800 (version v1.1), and a newer version DOI exists: 10.5281/zenodo.22670730. Cite the one you actually downloaded. |
| hersbach2020era5 | 10.1002/qj.3803 | fixed | The .bib had a stub @techreport. It is now the QJRMS article 146(730):1999–2049 with the full author list. |
| munozsabater2021era5land | 10.5194/essd-13-4349-2021 | fixed | This key was missing from the .bib and has been added: ESSD 13(9):4349–4383. |
| openmeteo | 10.5281/zenodo.7970649 | fixed | The @misc website entry was replaced by the DataCite record: Zippenfenig, P., *Open-Meteo.com Weather API*, Zenodo. This is the concept DOI. DataCite reports **version 1.4.0 and publicationYear 2024**, not 2023. The key `openmeteo` is kept because manuscript.tex uses it. |
| torres2026agroyachay | 10.1016/j.softx.2026.103037 | yes | SoftwareX 36, 103037 (2026). The Zenodo DOI 10.5281/zenodo.20829992 is kept in `note`. DataCite lists that record as v1.0.1. |
| vilca2026agrocommish | 10.5281/zenodo.20655609 | yes | DataCite: 5 authors match, Software, version 1.1.0, 2026. |
| torres2025frost | 10.14569/IJACSA.2025.0160992 | fixed | The **title differs** in Crossref. The correct title ends "...Frost Prediction in the Peruvian Altiplano", not "...High Andean Region of Peru". Volume 16(9) is confirmed and there are no pages. |
| torres2026bayescar | 10.1007/978-3-032-20151-5_4 | fixed | Now @incollection, pp. 43–55. Editors are S. Duarte Correia and M. Lahby. Springer Nature Switzerland, Cham, 2026. The book subtitle is "Applications, Case Studies, and Future Challenges" (Proc. ISGTA-2025). **Series volume 352 is not in Crossref.** It was taken from your brief, so check it against SpringerLink. |
| torres2026blockedcv | 10.1007/978-3-032-20151-5_1 | fixed | Same book, pp. 3–13. Authors: Vilca Apaza, W.; Torres Cruz, F.; Carpio Vargas, E. E. Same caveat about volume 352. |
| nash1970 | 10.1016/0022-1694(70)90255-6 | yes | 10(3):282–290. |
| klinggupta2009 | 10.1016/j.jhydrol.2009.08.003 | fixed | This key was missing from the .bib and has been added: 377(1–2):80–91. |
| knoben2019kge | 10.5194/hess-23-4323-2019 | yes | Issue 10 added. |
| moriasi2007 | 10.13031/2013.23153 | fixed | This key was missing from the .bib and has been added: 50(3):885–900. |
| murphy1988skill | 10.1175/1520-0493(1988)116<2417:SSBOTM>2.0.CO;2 | yes | |
| pappenberger2015benchmarks | 10.1016/j.jhydrol.2015.01.024 | new | J. Hydrol. 522:697–713. |
| schaefer1990csi | 10.1175/1520-0434(1990)005<0570:TCSIAA>2.0.CO;2 | new | Wea. Forecasting 5(4):570–575. |
| diebold1995dm | 10.1080/07350015.1995.10524599 | new | JBES 13(3):253–263. |
| harvey1997dm | 10.1016/S0169-2070(96)00719-4 | new | IJF 13(2):281–291. |
| kunsch1989block | 10.1214/aos/1176347265 | new | Ann. Stat. 17(3). Crossref has no pages; the standard pages 1217–1241 were used. Crossref spells the name "Kunsch"; the .bib uses K{\"u}nsch. |
| politis1994stationary | 10.1080/01621459.1994.10476870 | new | JASA 89(428):1303–1313. |
| bergmeir2012cv | 10.1016/j.ins.2011.12.028 | new | Inf. Sci. 191:192–213. |
| roberts2017cv | 10.1111/ecog.02881 | new | Ecography 40(8):913–929 (14 authors). |
| hoerl1970ridge | 10.1080/00401706.1970.10488634 | new | Technometrics 12(1):55–67. |
| breiman2001rf | 10.1023/A:1010933404324 | new | Mach. Learn. 45(1):5–32. |
| friedman2001gbm | 10.1214/aos/1013203451 | new | Ann. Stat. 29(5). Crossref has no pages; the standard pages 1189–1232 were used. |
| chen2016xgboost | 10.1145/2939672.2939785 | new | KDD '16, pp. 785–794. |
| kratzert2018lstm | 10.5194/hess-22-6005-2018 | new | HESS 22(11):6005–6022. |
| kratzert2019lstm | 10.5194/hess-23-5089-2019 | yes | Issue 12 added. |
| gauch2021lstm | 10.5194/hess-25-2045-2021 | yes | Issue 4 added. |
| nearing2021role | 10.1029/2020WR028091 | new | WRR 57(3), e2020WR028091. |
| addor2017camels | 10.5194/hess-21-5293-2017 | yes | Issue 10 added. |
| yaseen2015ai | 10.1016/j.jhydrol.2015.10.038 | new | J. Hydrol. 530:829–844. |
| mosavi2018flood | 10.3390/w10111536 | new | Water 10(11):1536. |
| munoz2018rf | 10.3390/w10111519 | yes | |
| munoz2025rf | 10.1007/s11069-024-06939-w | yes | Issue 4 added. It was published online in 2024 and in print in 2025. |
| teverovsky2023svr | 10.1016/j.envc.2023.100680 | fixed | Crossref gives the last author as **"Cara, Leandro"**, not "Cara Ramirez, Leandro Javier". |
| ramos2023crisnejas | 10.24850/j-tyca-14-01-04 | fixed | **The authors were wrong.** The real authors are Luis Vásquez-Ramírez and Luis Félix Vásquez-Paredes (Crossref and the journal's citation_author metadata); "C. Ramos et al." is incorrect. Pages 124–199 are confirmed by the landing-page metadata. The key is unchanged as instructed, but the in-text description must say "Vásquez-Ramírez and Vásquez-Paredes". |
| quispe2023ramis | 10.24850/j-tyca-14-02-05 | fixed | **The authors were wrong.** The real authors are Efrain Lujano, Rene Lujano, Juan Carlos Huamani and Apolinario Lujano; "W. Quispe et al." is incorrect. Pages 169–203. The key is unchanged as instructed. |
| llauca2023vilcanota | 10.3390/w15223944 | new | Water 15(22):3944 (recent antecedent). |
| mckee1993spi | — | no-DOI | 8th Conf. Applied Climatology, AMS, Anaheim, pp. 179–184. This is the standard citation and has no DOI. It is used by manuscript.tex. |
| mishra2010review | 10.1016/j.jhydrol.2010.07.012 | new | 391(1–2):202–216. |
| vanloon2015explained | 10.1002/wat2.1085 | new | WIREs Water 2(4):359–392. |
| vanloon2015severity | 10.1016/j.jhydrol.2014.10.059 | new | J. Hydrol. 526:3–14. |
| fleig2006threshold | 10.5194/hess-10-535-2006 | new | The real title is "A global evaluation of streamflow drought characteristics", HESS 10(4):535–552. |
| hao2018prediction | 10.1002/2016RG000549 | new | Rev. Geophys. 56(1):108–141 ("Seasonal drought prediction..."). |
| sutanto2021definitions | 10.5194/hess-25-3991-2021 | new | HESS 25(7):3991–4023 (recent antecedent). |
| shukla2008sri | 10.1029/2007GL032487 | yes | Issue 2 added. The article number is L02405. |
| vicenteserrano2010spei | 10.1175/2009JCLI2909.1 | yes | |
| vicenteserrano2012ssi | 10.1061/(ASCE)HE.1943-5584.0000433 | fixed | This key was missing from the .bib and has been added: 17(2):318–332. |
| farahmand2015nonparametric | 10.1016/j.advwatres.2014.11.012 | new | AWR 76:140–145. |
| gringorten1963 | 10.1029/JZ068i003p00813 | new | JGR 68(3):813–814. |
| tijdeman2020ssi | 10.1029/2019WR026315 | new | WRR 56(10), e2019WR026315 (recent antecedent). |
| sucozhanay2026threshold | 10.1080/02626667.2025.2600086 | new | HSJ 71(3):391–409 (recent antecedent). |
| garreaud2003altiplano | 10.1016/S0031-0182(03)00269-4 | new | 194(1–3):5–22. |
| lavado2012peru | 10.1080/02626667.2012.672985 | new | HSJ 57(4):625–642. |
| aybar2020pisco | 10.1080/02626667.2019.1649411 | new | HSJ 65(5):770–785 (online 2019). |
| baraer2012glacier | 10.3189/2012JoG11J186 | new | J. Glaciol. 58(207):134–150. |
| vuille2018andes | 10.1016/j.earscirev.2017.09.019 | new | The real title is "Rapid decline of snow and ice in the tropical Andes – Impacts, uncertainties and challenges ahead", 176:195–213. |
| zubieta2021titicaca | 10.3390/w13020175 | new | Water 13(2):175 (recent antecedent). |
| lujano2025gridded | 10.1590/2318-0331.302520240068 | new | RBRH 30, e10 (recent antecedent). |

**Dropped:** none. Every candidate DOI in the brief resolved to the intended work.

**Keys used in manuscript.tex that are not in this .bib:** `era5land` and `nash1970river`. These are older aliases; use `munozsabater2021era5land` and `nash1970` instead. The file caudal-sequia-altiplano.tex cites only keys that are in the .bib.

## New recent antecedents (2019–2026) for Related Work

These summaries are based on the Crossref abstracts. Sucozhañay et al. had no abstract available, so only its title is used and it is marked below.

- **zubieta2021titicaca** (Zubieta et al., 2021, *Water*): For the Titicaca–Desaguadero–Poopó (TDPS) system, bias-corrected CMIP5 RCP8.5 projections (2034–2064 vs. 1984–2014) indicate more intense, frequent and prolonged meteorological (SPI), agricultural and hydrological (standardized runoff index) droughts. The study also projects more short 1–2-month agricultural and hydrological droughts, especially in the southern basin.
- **lujano2025gridded** (Lujano et al., 2025, *RBRH*): In Peruvian Altiplano basins, AgERA5 and ERA5-Land gave the best daily precipitation among four gridded products compared with 33 stations. However, driving the GR4J model with gridded precipitation *and* PET together clearly degraded streamflow simulation. This is relevant to using ERA5-Land forcings.
- **sucozhanay2026threshold** (Sucozhañay et al., 2026, *Hydrol. Sci. J.*): This study identifies and characterizes streamflow droughts in a tropical Andean basin and compares threshold methods. It shows that drought characteristics depend on the threshold choice (based on the title; no abstract was available, so check the paper before citing specific results).
- **tijdeman2020ssi** (Tijdeman et al., 2020, *WRR*): Across 369 European rivers, SSI series and the drought characteristics derived from them were sensitive to the choice of distribution and fitting method. Parametric SSI was sensitive to both tails of the sample. This supports a nonparametric (empirical plotting-position) SSI.
- **sutanto2021definitions** (Sutanto & Van Lanen, 2021, *HESS*): Streamflow drought forecasting needs a drought-identification step on top of the streamflow forecast. The daily and monthly variable-threshold, fixed-threshold and SSI methods identify substantially different droughts, both historically and in ECMWF SEAS5-driven forecasts.
- **llauca2023vilcanota** (Llauca et al., 2023, *Water*): In the data-sparse Vilcanota basin (tropical Andes of Peru), assimilating hourly discharge into a GR4H ensemble with EnKF or a particle filter improved 1–24 h streamflow forecasts for about the first 6–8 h. The GSMaP-NRT + EnKF combination performed best. This is a Peruvian short-range forecasting benchmark.
