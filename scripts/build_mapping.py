"""Regenerate the candidate and decision tables from pinned public archives.

The TianGong input is its historical, public git checkout, not an authenticated
platform export. Matching is curated: a search hit is never selected by name alone.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from lca_tool.cli import PROCESSES, read_bom
from lca_tool.engine import Archive


QUERIES = {
    "Stainless steel": (r"stainless steel", "6fcb8304-d211-4c79-a9de-a1b07058ce02"),
    "Brass": (r"brass", None),
    "Copper": (r"copper", "affec622-8421-4bf1-8abf-3b38a85e24da"),
    "Polypropylene (PP)": (r"polypropylene", "91a5462f-3a1a-49e9-afec-07b60609dfaf"),
    "Polyvinyl chloride (PVC)": (r"polyvinyl chloride|\bPVC\b", "394548b3-e2f7-46bc-be9d-f43824d8d0c3"),
    "Nylon, grade unspecified": (r"nylon|polyamide", "e88dc78d-a163-4579-9ec7-b9cea7fea08e"),
    "Polyoxymethylene (POM)": (r"polyoxymethylene|polyacetal", None),
    "Polycarbonate (PC)": (r"polycarbonate", None),
    "Acrylonitrile-butadiene-styrene (ABS)": (r"\bABS\b|acrylonitrile.butadiene.styrene", None),
    "Silicone": (r"silicone", "a9323f4f-31bf-4282-9a03-2ee92ac355bd"),
    "LDPE packaging foil": (r"LDPE|low.density polyethylene", "218eaad4-dfc5-4a21-abd3-2e9dd0997fe3"),
    "Cardboard packaging": (r"cardboard|corrugated", "b0a8d882-9859-4069-b59b-90dd19dc98a0"),
    "Component forming and metalwork": (r"injection molding|metal forming|stamping", None),
    "Assembly electricity": (r"electricity", None),
    "Inbound freight": (r"transport|freight", None),
    "Scrap treatment": (r"recycl|scrap", None),
}


def tiangong_name(path):
    try:
        root = ET.parse(path).getroot()
        for node in root.iter():
            if node.tag.endswith("baseName") and node.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") == "en":
                return node.text or ""
    except ET.ParseError:
        pass
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--tiangong", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    archive = Archive(args.archive)
    tg_root = args.tiangong / "tiangong_lca_data" / "processes"
    us_names = {}
    for member in archive.zip.namelist():
        if member.startswith("processes/") and member.endswith(".json"):
            d = json.loads(archive.zip.read(member))
            us_names[d["@id"]] = d["name"]
    tg_names = {p.stem: tiangong_name(p) for p in tg_root.glob("*.xml")}
    bom = {r["material"]: r for r in read_bom(Path("data/source/classroom/kettle-bom.csv"))}
    now = datetime.now(timezone.utc).isoformat()
    fields = ["foreground_input", "quantity", "unit", "database", "release", "dataset_id",
              "dataset_version", "dataset_name", "geography", "reference_unit", "conversion_factor",
              "source_url", "retrieved_at_utc", "source_sha256", "alternatives_considered",
              "selection_reason", "proxy_or_exact", "unresolved_gap"]
    decisions, searches = [], []
    for item, (pattern, tg_candidate) in QUERIES.items():
        us_hits = [(uid, name) for uid, name in us_names.items() if re.search(pattern, name, re.I)]
        tg_hits = [(uid, name) for uid, name in tg_names.items() if re.search(pattern, name, re.I)]
        for database, hits in [("Commons Merged (USLCI/US Electricity)", us_hits),
                               ("TianGong historical public git", tg_hits)]:
            searches.append({"foreground_input": item, "database": database, "query_regex": pattern,
                             "hit_count": len(hits), "example_ids": ";".join(uid for uid, _ in hits[:5]),
                             "searched_at_utc": now})
        amount = float(bom[item]["finished_mass_g"]) / 1000 if item in bom else "unknown"
        uid = PROCESSES.get(item)
        p = archive.read("processes", uid) if uid else None
        decisions.append(dict(zip(fields, [item, amount, "kg" if item in bom else "unknown",
            "Commons Merged / USLCI", "Commons_Merged_v0.1.0-alpha; USLCI v1.2026-06.1" if p else "searched v0.1.0-alpha",
            uid or "not selected", p["version"] if p else "unknown", p["name"] if p else "unknown",
            p.get("location", {}).get("name", "unknown") if p else "unknown",
            "kg" if p else "unknown", "1 kg finished/kg reference" if p else "unknown",
            f"https://github.com/FLCAC-admin/commons_merged/releases/download/v0.1.0-alpha/Commons_Merged_v0.1.0-alpha.zip" if p else "https://github.com/FLCAC-admin/commons_merged/releases/tag/v0.1.0-alpha",
            now, archive.source_sha256("processes", uid) if p else "not applicable",
            ";".join(f"{i}:{n}" for i,n in us_hits[:5]) or "no name hits",
            ("molded PP part includes resin and molding; do not add resin separately" if item == "Polypropylene (PP)" else
             "closest public process; finished-film conversion absent" if item == "LDPE packaging foil" else
             "closest public corrugated product; box conversion uncertain" if item == "Cardboard packaging" else
             "resin supply only; component conversion absent" if p else "no suitable product flow/grade or unknown activity quantity"),
            "proxy" if p else "unresolved",
            ("provider and CF gaps; some foreground conversion/transport/assembly unknown" if p else
             "material supply or service activity not calculated")])))
        if tg_candidate:
            path = tg_root / f"{tg_candidate}.xml"
            if path.exists():
                name = tg_names[tg_candidate]
                decisions.append(dict(zip(fields, [item, amount, "kg" if item in bom else "unknown",
                    "TianGong historical public git", "repository v0.2.0; commit c50cab7961e0b0ca11c26a600bd4c90fea6c6c32",
                    tg_candidate, "unknown", name, "China/unknown", "unknown", "not applied",
                    f"https://github.com/tiangong-lca/data/blob/c50cab7961e0b0ca11c26a600bd4c90fea6c6c32/tiangong_lca_data/processes/{tg_candidate}.xml",
                    now, hashlib.sha256(path.read_bytes()).hexdigest(),
                    ";".join(f"{i}:{n}" for i,n in tg_hits[:3]),
                    "candidate only: region, product/flow mapping and complete LCIA compatibility not verified",
                    "candidate", "not included in US-modelled calculation"])))
    with (args.out / "mapping-decisions.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields); writer.writeheader(); writer.writerows(decisions)
    with (args.out / "search-log.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, searches[0]); writer.writeheader(); writer.writerows(searches)
    print(f"{len(decisions)} decisions; {len(searches)} searches")


if __name__ == "__main__":
    main()
