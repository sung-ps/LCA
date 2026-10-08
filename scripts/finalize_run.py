"""Make a compact QA report, chart, and classroom manifest from the real run."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "independent"


def main():
    result = json.loads((OUT / "result.json").read_text())
    total = result["partial_characterized_kg_co2e"]
    rows = result["rows"]
    calculated = [r for r in rows if r["calculated"]]
    gaps = result["process_models"]
    mass_kettle = sum(r["finished_mass_g"] for r in rows if r["scope"] == "Kettle")
    mass_packaging = sum(r["finished_mass_g"] for r in rows if r["scope"] == "Packaging")
    subtotal = sum(r["partial_characterized_kg_co2e"] for r in calculated)
    provider_count = sum(len(v["provider_gaps"]) for v in gaps.values())
    unmatched_count = sum(v["uncharacterized_exchange_count"] for v in gaps.values())
    distinct_gaps = {(g["process_id"], g["flow"], g["reason"])
                     for model in gaps.values() for g in model["provider_gaps"]}
    checks = {
        "bom_rows": {"status": "pass" if len(rows) == 12 else "fail", "observed": len(rows)},
        "kettle_mass_g": {"status": "pass" if abs(mass_kettle - 723) < 1e-9 else "fail", "observed": mass_kettle},
        "packaging_mass_g": {"status": "pass" if abs(mass_packaging - 137.8) < 1e-9 else "fail", "observed": mass_packaging},
        "contribution_sum": {"status": "pass" if abs(subtotal-total) < 1e-9 else "fail", "observed": subtotal},
        "matrix_balance": {"status": "pass" if all(v["balance_residual"] < 1e-7 for v in gaps.values()) else "fail",
                           "worst_residual": max(v["balance_residual"] for v in gaps.values())},
        "provider_closure": {"status": "fail" if provider_count else "pass", "gap_instances": provider_count,
                             "distinct_gaps": len(distinct_gaps)},
        "characterization_coverage": {"status": "fail" if unmatched_count else "pass",
                                      "uncharacterized_exchange_instances": unmatched_count},
        "full_foreground_coverage": {"status": "fail" if len(calculated) != 12 else "pass",
                                     "calculated_bom_rows": len(calculated),
                                     "missing_bom_rows": [r["material"] for r in rows if not r["calculated"]],
                                     "assembly_electricity": "unknown", "inbound_freight": "unknown"},
        "double_counting": {"status": "pass for explicit PP model",
                            "evidence": "PP resin is input to injection molding process and not added as a second foreground process"},
    }
    (OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    data = sorted(calculated, key=lambda r: r["partial_characterized_kg_co2e"], reverse=True)
    labels = {"Polypropylene (PP)": "PP molded part", "Cardboard packaging": "Corrugated board",
              "Polyvinyl chloride (PVC)": "PVC resin", "Acrylonitrile-butadiene-styrene (ABS)": "ABS resin",
              "LDPE packaging foil": "LDPE resin"}
    bars = []
    for i, row in enumerate(data):
        y = 70 + i * 54
        width = 440 * row["partial_characterized_kg_co2e"] / data[0]["partial_characterized_kg_co2e"]
        bars.append(f'<text x="20" y="{y+19}" font-size="15">{labels[row["material"]]}</text>'
                    f'<rect x="185" y="{y}" width="{width:.1f}" height="24" fill="#3479ac"/>'
                    f'<text x="{195+width:.1f}" y="{y+19}" font-size="14">{row["partial_characterized_kg_co2e"]:.3f}</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="370" viewBox="0 0 760 370">' \
          '<rect width="100%" height="100%" fill="white"/><text x="20" y="32" font-size="20" font-weight="bold">Partial characterized GWP100 contributions</text>' \
          '<text x="20" y="52" font-size="13">kg CO2-eq per packaged kettle; incomplete model, not total GWP100</text>' \
          + ''.join(bars) + '</svg>\n'
    (OUT / "partial_contributions.svg").write_text(svg)
    template = json.loads((ROOT / "data/source/classroom/run-manifest.template.json").read_text())
    template.update({"student_alias": "sung-ps", "run_id": result["run_id"], "run_date_utc": result["run_date_utc"],
                     "codex_model_displayed": "GPT-6 (Codex)",
                     "codex_settings_known": {"reasoning_effort": "unknown", "service_tier": "unknown"},
                     "manufacturing_geography": "US-modelled proxy; actual factory unknown",
                     "reference_year": "2026 modelling year; process years vary/unknown"})
    template["characterization_method"] = {"name": "IPCC AR6-100", "version": "01.01.004",
        "time_horizon_years": 100, "source_url": "https://github.com/FLCAC-admin/commons_merged/releases/tag/v0.1.0-alpha",
        "category_id": "a6206006-65bc-395c-8dc9-f12262f45a04"}
    template["database_releases"] = [
        {"name": "Commons Merged", "release": "v0.1.0-alpha", "sha256": result["archive_sha256"],
         "embedded_uslci": "v1.2026-06.1", "electricity": "US Electricity Baseline included"},
        {"name": "TianGong historical data", "release": "repository v0.2.0", "used_in_calculation": False,
         "commit": "c50cab7961e0b0ca11c26a600bd4c90fea6c6c32"}]
    template["assumptions"] = {
        "yield_and_losses": "PP molding dataset includes 1.034 kg virgin PP/kg molded output. Other losses unknown; no invented yield used.",
        "manufacturing_energy": "PP molding dataset includes 6.444 MJ electricity/kg molded output; assembly electricity unknown.",
        "allocation": "Source processes report NO_ALLOCATION; non-reference coproducts flagged unresolved.",
        "recycling": "Scrap generation/treatment and credits unknown; no separate credit included.",
        "other": "Five public US-modelled proxies; actual factory location unknown; finish-film and carton conversion unknown."}
    template["mapping_table"] = "data/processed/mapping-decisions.csv"
    template["prompts_record"] = "docs/prompts_and_runs.md"
    template["reproduction_command"] = "PYTHONPATH=src python -m lca_tool.cli --archive data/cache/Commons_Merged_v0.1.0-alpha.zip && PYTHONPATH=src python scripts/finalize_run.py"
    template["results"] = {"status": result["calculation_status"],
        "ghg_kg_co2e_per_packaged_kettle": None,
        "partial_characterized_kg_co2e": total,
        "contributions": [{"input": r["material"], "partial_kg_co2e": r["partial_characterized_kg_co2e"]} for r in calculated],
        "missing_inputs": checks["full_foreground_coverage"]["missing_bom_rows"] + ["assembly electricity", "inbound freight", "non-PP conversion", "scrap treatment"],
        "unresolved_providers": {"instances": provider_count, "distinct": len(distinct_gaps), "detail": "result.json process_models[*].provider_gaps"},
        "uncharacterized_flows": {"exchange_instances": unmatched_count, "detail": "result.json process_models[*].uncharacterized_flow_summary"}}
    template["uncertainty"] = {"performed": False, "distributions": [], "correlations": "not applicable",
        "seed": None, "draws": None, "p05_kg_co2e": None, "p95_kg_co2e": None,
        "reason": "No sourced parameter ranges; deterministic proxy sensitivity only",
        "proxy_sensitivity": result["sensitivity"]}
    template["checks"] = checks
    template["revision"] = {"prior_commit_sha": None, "one_choice_changed": "not applicable: classroom comparison unavailable",
                            "predicted_effect": "not applicable", "observed_effect": "not applicable"}
    (OUT / "run-manifest.json").write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"checks": {k:v["status"] for k,v in checks.items()},
                      "partial_kg_co2e": total, "full_kg_co2e": None}, indent=2))


if __name__ == "__main__":
    main()
