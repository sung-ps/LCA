"""Run the reproducible independent classroom calculation."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

import numpy
import scipy

from .engine import Archive, build_model, sha256


EXPECTED_ARCHIVE_SHA = "02f9986d1e2d9007395b48e710cc94577a7f87e46cdc225c59f7b2659b6eb29a"
PROCESSES = {
    "Polypropylene (PP)": "89a2b59a-1ca2-34f5-acc8-a8eaaa6fa870",
    "Polyvinyl chloride (PVC)": "3dbccdda-2014-4239-ad1f-4e15c034942b",
    "Acrylonitrile-butadiene-styrene (ABS)": "0e42a306-ee2d-362e-8bc3-580000096459",
    "LDPE packaging foil": "6a12cba1-889d-4515-90f8-89feb8d662f2",
    "Cardboard packaging": "226ed3c2-e020-4c95-b1fc-4559fc2d18ac",
}


def read_bom(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 12 or len({r["material"] for r in rows}) != 12:
        raise ValueError("BOM must contain 12 unique rows")
    kettle = sum(float(r["finished_mass_g"]) for r in rows if r["scope"] == "Kettle")
    packaging = sum(float(r["finished_mass_g"]) for r in rows if r["scope"] == "Packaging")
    if abs(kettle - 723) > 1e-8 or abs(packaging - 137.8) > 1e-8:
        raise ValueError(f"BOM mass mismatch: kettle={kettle}, packaging={packaging}")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--bom", default="data/source/classroom/kettle-bom.csv", type=Path)
    parser.add_argument("--output", default="results/independent", type=Path)
    parser.add_argument("--skip-hash-check", action="store_true", help="For diagnostic development only")
    args = parser.parse_args(argv)
    actual_sha = sha256(args.archive)
    if not args.skip_hash_check and actual_sha != EXPECTED_ARCHIVE_SHA:
        parser.error("archive SHA-256 differs from pinned v0.1.0-alpha package")
    rows = read_bom(args.bom)
    archive = Archive(args.archive)
    results = {}
    for row in rows:
        name = row["material"]
        if name not in PROCESSES:
            continue
        qty_kg = float(row["finished_mass_g"]) / 1000
        results[name] = build_model(archive, {PROCESSES[name]: qty_kg})
    pp_resin = build_model(archive, {"2e8facf6-46aa-4ddb-95de-a4e2a00eb2bb": 0.35025})
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    part_sum = sum(v["impact_characterized_linked_only_kg_co2e"] for v in results.values())
    summary = {
        "run_id": "bc1-independent-2026-10-08-01",
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "declared_unit": "one packaged BC1 kettle at factory gate",
        "calculation_status": "partial characterized linked-process inventory; not full GWP100",
        "full_gwp100_kg_co2e": None,
        "partial_characterized_kg_co2e": part_sum,
        "archive_sha256": actual_sha,
        "bom_sha256": sha256(args.bom),
        "runtime": {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__},
        "rows": [{"material": r["material"], "scope": r["scope"],
                  "finished_mass_g": float(r["finished_mass_g"]),
                  "finished_mass_kg": float(r["finished_mass_g"]) / 1000,
                  "calculated": r["material"] in results,
                  "partial_characterized_kg_co2e": results[r["material"]]["impact_characterized_linked_only_kg_co2e"] if r["material"] in results else None}
                 for r in rows],
        "process_models": results,
        "sensitivity": {"choice": "PP molded part replaced with virgin resin at equal finished mass",
                        "predicted_direction": "decrease",
                        "base_pp_partial_kg_co2e": results["Polypropylene (PP)"]["impact_characterized_linked_only_kg_co2e"],
                        "resin_only_pp_partial_kg_co2e": pp_resin["impact_characterized_linked_only_kg_co2e"],
                        "base_partial_sum_kg_co2e": part_sum,
                        "resin_only_partial_sum_kg_co2e": part_sum - results["Polypropylene (PP)"]["impact_characterized_linked_only_kg_co2e"] + pp_resin["impact_characterized_linked_only_kg_co2e"],
                        "limitation": "resin-only omits molding and both models have provider/CF gaps; neither is full GWP100"},
    }
    (output / "result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    with (output / "contributions.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["material", "finished_mass_kg", "partial_characterized_kg_co2e", "status"])
        for row in summary["rows"]:
            writer.writerow([row["material"], row["finished_mass_kg"],
                             row["partial_characterized_kg_co2e"] if row["calculated"] else "",
                             "partial" if row["calculated"] else "not calculated"])
    print(json.dumps({"status": summary["calculation_status"], "partial_kg_co2e": part_sum,
                      "full_kg_co2e": None,
                      "provider_gaps": sum(len(r["provider_gaps"]) for r in results.values()),
                      "uncharacterized_exchanges": sum(r["uncharacterized_exchange_count"] for r in results.values())}, indent=2))


if __name__ == "__main__":
    main()
