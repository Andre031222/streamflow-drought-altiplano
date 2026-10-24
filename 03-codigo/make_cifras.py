#!/usr/bin/env python3
"""Write every number quoted in the manuscript (cifras.tex) and the LaTeX tables
from the result tables, so no figure in the text is typed by hand.

Usage: python 03-codigo/make_cifras.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg
from plots import LEARNERS, REGION_ORDER, short, val_selected

OUT = cfg.MANUSCRIPT


PROSE = {"RandomForest": "random forest", "HistGB": "histogram gradient boosting",
         "XGBoost": "XGBoost", "XGBoost-log": "XGBoost-log", "Ridge": "Ridge regression", "MLP": "MLP"}


def f3(x) -> str:
    return "n/a" if pd.isna(x) else f"{x:.3f}".replace("-", "$-$")


def f2(x) -> str:
    return "n/a" if pd.isna(x) else f"{x:.2f}".replace("-", "$-$")


def pval(p) -> str:
    if pd.isna(p):
        return "--"
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def main() -> None:
    met = pd.read_csv(cfg.TAB / "metrics_by_station.csv")
    fus = pd.read_csv(cfg.TAB / "metrics_fusion_ablation.csv")
    wf = pd.read_csv(cfg.TAB / "metrics_walkforward.csv")
    meta_run = json.load(open(cfg.TAB / "experiment_meta.json"))
    st = pd.read_csv(cfg.STATION_META)
    best = val_selected(met)
    pers = met[met.model == "persistence"]
    mac: dict[str, str] = {}

    words = {1: "One", 3: "Three", 7: "Seven"}
    mac["nGauges"] = str(len(st))
    for r, key in zip(REGION_ORDER, ["Alti", "CB", "WSA"]):
        mac[f"nGauges{key}"] = str(int((st.region == r).sum()))
    mac["nPeru"] = str(int((st.country == "Peru").sum()))
    mac["nChile"] = str(int((st.country == "Chile").sum()))
    mac["nFeatures"] = str(meta_run["n_features_base"])
    mac["runtimeMin"] = f"{meta_run['runtime_seconds'] / 60:.0f}"
    mac["nBoot"] = str(cfg.N_BOOT)
    mac["bootBlock"] = str(cfg.BOOT_BLOCK)

    # --- focus gauge
    fid = cfg.FOCUS_STATION_ID
    sp = meta_run["splits"][fid]["7"]
    mac["focusTestStart"], mac["focusTestEnd"] = sp["test"]
    mac["focusTrainStart"] = sp["train"][0]
    for h in cfg.HORIZONS:
        w = words[h]
        fm = met[(met.gauge_id == fid) & (met.horizon == h)].set_index("model")
        b = best[(best.gauge_id == fid) & (best.horizon == h)].iloc[0]
        mac[f"focusNTest{w}"] = str(int(fm.n_test.iloc[0]))
        mac[f"focusPersNse{w}"] = f3(fm.loc["persistence", "NSE"])
        mac[f"focusBest{w}"] = PROSE.get(b.model, b.model)
        mac[f"focusBestNse{w}"] = f3(b.NSE)
        mac[f"focusBestKge{w}"] = f3(b.KGE)
        mac[f"focusBestSkill{w}"] = f3(b.skill_vs_persistence)
        mac[f"focusBestLo{w}"] = f3(b.skill_lo)
        mac[f"focusBestHi{w}"] = f3(b.skill_hi)
        mac[f"focusBestDmp{w}"] = pval(b.dm_p)
        mac[f"focusRidgeSkill{w}"] = f3(fm.loc["Ridge", "skill_vs_persistence"])

    # --- multi-gauge
    for h in cfg.HORIZONS:
        w = words[h]
        b = best[best.horizon == h]
        mac[f"nPos{w}"] = str(int((b.skill_vs_persistence > 0).sum()))
        mac[f"nSig{w}"] = str(int((b.skill_lo > 0).sum()))
        mac[f"nEval{w}"] = str(len(b))
        mac[f"medSkill{w}"] = f3(b.skill_vs_persistence.median())
        mac[f"medPersNse{w}"] = f3(pers[pers.horizon == h].NSE.median())
        mac[f"medBestNse{w}"] = f3(b.NSE.median())
        for r, key in zip(REGION_ORDER, ["Alti", "CB", "WSA"]):
            mac[f"medSkill{key}{w}"] = f3(b[b.region == r].skill_vs_persistence.median())
        ridge = met[(met.model == "Ridge") & (met.horizon == h)]
        mac[f"nRidgePos{w}"] = str(int((ridge.skill_vs_persistence > 0).sum()))
    counts = best[best.horizon == 7].model.value_counts()
    mac["mostSelected"] = PROSE.get(counts.index[0], counts.index[0])
    mac["mostSelectedN"] = str(int(counts.iloc[0]))
    tgt = met[met.model.isin(LEARNERS) & (met.horizon == 7)].config.map(lambda c: json.loads(c).get("target"))
    mac["pctDeltaTarget"] = f"{100 * (tgt != 'level').mean():.0f}"

    # --- drought detection (h = 7)
    b7 = best[best.horizon == 7].set_index("gauge_id")
    p7 = pers[pers.horizon == 7].set_index("gauge_id")
    xl = met[(met.model == "XGBoost-log") & (met.horizon == 7)].set_index("gauge_id")
    mac["medCsiPers"] = f2(p7.drought_CSI.median())
    mac["medCsiBest"] = f2(b7.drought_CSI.median())
    mac["medCsiXgbLog"] = f2(xl.drought_CSI.median())
    mac["medFarPers"] = f2(p7.drought_FAR.median())
    mac["medFarBest"] = f2(b7.drought_FAR.median())
    mac["medPodPers"] = f2(p7.drought_POD.median())
    mac["medPodBest"] = f2(b7.drought_POD.median())
    mac["nCsiBestBeats"] = str(int((b7.drought_CSI > p7.drought_CSI.reindex(b7.index)).sum()))
    mac["nCsiXgbLogBeats"] = str(int((xl.drought_CSI > p7.drought_CSI.reindex(xl.index)).sum()))
    # drought decision calibrated on validation CSI (same procedure for every method)
    mac["medCsiCalPers"] = f2(p7.droughtcal_CSI.median())
    mac["medCsiCalBest"] = f2(b7.droughtcal_CSI.median())
    mac["medPodCalBest"] = f2(b7.droughtcal_POD.median())
    mac["medFarCalBest"] = f2(b7.droughtcal_FAR.median())
    mac["nCsiCalBestBeats"] = str(int((b7.droughtcal_CSI > p7.droughtcal_CSI.reindex(b7.index)).sum()))
    mac["nCsiCalImproves"] = str(int((b7.droughtcal_CSI > b7.drought_CSI).sum()))

    # --- fusion ablation (h = 7)
    f7 = fus[fus.horizon == 7]
    if not f7.empty:
        piv = f7[f7.model.isin(["Ridge", "XGBoost"])].pivot_table(
            index=["gauge_id", "model"], columns="feature_set", values="skill_vs_persistence")
        piv["d"] = piv.fused - piv.base
        mac["nFusion"] = str(f7.gauge_id.nunique())
        for mdl in ["Ridge", "XGBoost"]:
            d = piv.xs(mdl, level="model").d
            mac[f"fusionMedDelta{mdl}"] = f3(d.median())
            mac[f"fusionNPos{mdl}"] = str(int((d > 0).sum()))
        g = f7[f7.model == "GloFAS"]
        mac["glofasMedNse"] = f2(g.NSE.median())
        mac["glofasNPosNse"] = str(int((g.NSE > 0).sum()))
    else:
        mac["nFusion"] = "0"

    # --- resolution test: ERA5 vs ERA5 + CHIRPS (h = 7)
    chf = cfg.TAB / "metrics_chirps_ablation.csv"
    c7 = pd.read_csv(chf) if chf.exists() else pd.DataFrame()
    c7 = c7[c7.horizon == 7] if not c7.empty else c7
    if not c7.empty:
        piv = c7.pivot_table(index=["gauge_id", "model"], columns="feature_set",
                             values="skill_vs_persistence")
        piv["d"] = piv.era5_chirps - piv.era5
        mac["nChirps"] = str(c7.gauge_id.nunique())
        for mdl in ["Ridge", "XGBoost"]:
            d = piv.xs(mdl, level="model").d
            mac[f"chirpsMedDelta{mdl}"] = f3(d.median())
            mac[f"chirpsNPos{mdl}"] = str(int((d > 0).sum()))
            mac[f"chirpsMaxDelta{mdl}"] = f3(d.max())
        ratios = []
        for gid in c7.gauge_id.unique():  # ERA5 / CHIRPS mean precipitation on common days
            ch = pd.read_csv(cfg.CLIMATE_DIR / "chirps" / f"{gid}.csv", parse_dates=["date"])
            er = pd.read_csv(cfg.CLIMATE_DIR / "era5" / f"{gid}.csv", parse_dates=["date"])
            m = ch.merge(er, on="date").dropna(subset=["precip_chirps", "precip_era5"])
            ratios.append(m.precip_era5.mean() / m.precip_chirps.mean())
        mac["eraChirpsRatio"] = f"{np.median(ratios):.1f}"
    else:
        mac["nChirps"] = "0"

    # --- walk-forward (h = 7)
    w7 = wf[wf.horizon == 7]
    mac["wfNFolds"] = str(len(w7))
    mac["wfNPos"] = str(int((w7.skill_vs_persistence > 0).sum()))
    mac["wfMedSkill"] = f3(w7.skill_vs_persistence.median())
    wff = w7[w7.gauge_id == fid].skill_vs_persistence
    mac["wfFocusSkills"] = ", ".join(f3(x) for x in wff)

    # --- spatial statistics (written by spatial_analysis.py)
    sp = cfg.TAB / "spatial_summary.json"
    if sp.exists():
        ss = json.load(open(sp))
        mac["nPairs"] = str(ss["n_pairs"])
        mac["corrDzero"] = f"{ss['corr_d0_km']:.0f}"
        mac["corrDzeroLo"] = f"{ss['corr_d0_ci'][0]:.0f}"
        mac["corrDzeroHi"] = f"{ss['corr_d0_ci'][1]:.0f}"
        mac["corrC"] = f2(ss["corr_c"])
        mac["rhoDist"] = f2(ss["spearman_rho_dist"])
        mac["pDist"] = pval(ss["spearman_p_dist"])
        mac["rhoSameRegion"] = f2(ss["median_rho_same_region"])
        mac["rhoCrossRegion"] = f2(ss["median_rho_cross_region"])
        mac["moranI"] = f3(ss["moran_I"])
        mac["moranP"] = pval(ss["moran_p"])
        mac["moranExp"] = f3(ss["moran_expected"])
        td = ss["top_driver"]
        mac["topDriver"] = td["label"].lower()
        mac["topDriverRho"] = f2(td["rho"])
        mac["topDriverP"] = pval(td["p_perm"])
        mac["topDriverPholm"] = pval(td["p_holm"])

    with open(OUT / "cifras.tex", "w") as f:
        for k, v in mac.items():
            f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
        f.write("\\newcommand{\\githubUrl}{https://github.com/Andre031222/streamflow-drought-altiplano}\n")
        f.write("\\newcommand{\\orcidAndre}{0009-0003-2385-5263}\n")
        f.write("\\newcommand{\\orcidMaribel}{0009-0003-6218-2735}\n")
        f.write("\\newcommand{\\orcidRenato}{0009-0005-2367-7852}\n")
        f.write("\\newcommand{\\emailAndre}{75521963@est.unap.edu.pe}\n")
        f.write("\\newcommand{\\emailMaribel}{maribelbel201314@gmail.com}\n")
        f.write("\\newcommand{\\emailRenato}{72535253@est.unap.edu.pe}\n")

    # --- Table: gauges
    ev = met[met.horizon == 7].groupby("gauge_id").agg(n_test=("n_test", "first"),
                                                       ts=("test_start", "first"), te=("test_end", "first"))
    rows = []
    for r in REGION_ORDER:
        for s in st[st.region == r].sort_values("gauge_name").itertuples():
            e = ev.loc[s.gauge_id] if s.gauge_id in ev.index else None
            name = short(s.gauge_name) + (r"$^\star$" if s.gauge_id == fid else "")
            rows.append(f"{s.gauge_id} & {name} & {s.country[:2]} & {r.replace('Western/Southern Andes', 'W/S Andes')} & "
                        f"{s.basin_area:,.0f} & {s.date_start[:4]}--{s.date_end[:4]} & "
                        f"{s.days_w_data_qc:,} & {'' if e is None else int(e.n_test)} \\\\")
    with open(OUT / "tab_gauges.tex", "w") as f:
        f.write("\n".join(rows) + "\n")

    # --- Table: focus gauge, all models x horizons
    rows = []
    for h in cfg.HORIZONS:
        fm = met[(met.gauge_id == fid) & (met.horizon == h)]
        bsel = best[(best.gauge_id == fid) & (best.horizon == h)].model.iloc[0]
        for m in ["persistence", "climatology"] + LEARNERS:
            x = fm[fm.model == m].iloc[0]
            name = {"persistence": "Persistence", "climatology": "Climatology"}.get(m, m)
            if m == bsel:
                name = r"\textbf{" + name + r"}$^\dagger$"
            ci = "--" if m == "persistence" else f"[{f2(x.skill_lo)}, {f2(x.skill_hi)}]"
            rows.append(f"{h if m == 'persistence' else ''} & {name} & {x.RMSE:.2f} & {f3(x.NSE)} & {f3(x.KGE)} & "
                        f"{f3(x.skill_vs_persistence)} & {ci} & {pval(x.dm_p)} & {f2(x.drought_CSI)} \\\\")
        rows.append(r"\midrule" if h != cfg.HORIZONS[-1] else "")
    with open(OUT / "tab_focus.tex", "w") as f:
        f.write("\n".join(rows) + "\n")

    # --- Compact focus table (h = 1 and 7 side by side) for the 8-page version
    rows = []
    names = {"persistence": "Persistence", "climatology": "Climatology", "Ridge": "Ridge",
             "RandomForest": "Random forest", "HistGB": "Hist. gradient boosting", "XGBoost": "XGBoost",
             "MLP": "MLP", "XGBoost-log": "XGBoost-log"}
    sel = {h: best[(best.gauge_id == fid) & (best.horizon == h)].model.iloc[0] for h in (1, 7)}
    for m in ["persistence"] + LEARNERS:
        cells = [names[m]]
        for h in (1, 7):
            x = met[(met.gauge_id == fid) & (met.horizon == h) & (met.model == m)].iloc[0]
            mark = r"$^\dagger$" if m == sel[h] else ""
            sk = "--" if m == "persistence" else f"{f3(x.skill_vs_persistence)}{mark} [{f2(x.skill_lo)}, {f2(x.skill_hi)}]"
            cells += [f3(x.NSE), sk]
        x7 = met[(met.gauge_id == fid) & (met.horizon == 7) & (met.model == m)].iloc[0]
        cells.append(f2(x7.drought_CSI))
        rows.append(" & ".join(cells) + r" \\")
    with open(OUT / "tab_focus_compact.tex", "w") as f:
        f.write("\n".join(rows) + "\n")

    # --- Table: regional summary
    rows = []
    for h in cfg.HORIZONS:
        for r in REGION_ORDER:
            b = best[(best.horizon == h) & (best.region == r)]
            p = pers[(pers.horizon == h) & (pers.region == r)]
            rows.append(f"{h if r == REGION_ORDER[0] else ''} & {r.replace('Western/Southern Andes', 'W/S Andes')} & "
                        f"{len(b)} & {f3(p.NSE.median())} & {f3(b.NSE.median())} & "
                        f"{f3(b.skill_vs_persistence.median())} & {int((b.skill_lo > 0).sum())}/{len(b)} & "
                        f"{f2(p.drought_CSI.median())} & {f2(b.drought_CSI.median())} \\\\")
        if h != cfg.HORIZONS[-1]:
            rows.append(r"\midrule")
    with open(OUT / "tab_regions.tex", "w") as f:
        f.write("\n".join(rows) + "\n")

    # --- Markdown summary for humans
    with open(cfg.TAB / "metrics_summary.md", "w") as f:
        f.write("# Benchmark summary (auto-generated by make_cifras.py)\n\n")
        for k, v in mac.items():
            f.write(f"- `{k}`: {v}\n")
    print(f"Wrote cifras.tex ({len(mac)} macros), tab_gauges/tab_focus/tab_regions.tex, metrics_summary.md")


if __name__ == "__main__":
    main()
