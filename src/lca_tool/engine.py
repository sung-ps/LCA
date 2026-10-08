"""Provider-specific unit-process matrix solver for openLCA JSON-LD archives.

Each row represents a process's own quantitative-reference product. The diagonal
is its positive reference output; linked inputs enter the supplying row with a
negative sign. Unlinked inputs are reported, never interpreted as zero burden.
"""
from __future__ import annotations

from collections import Counter, deque
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import spsolve


METHOD_ID = "a6206006-65bc-395c-8dc9-f12262f45a04"


class ModelError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def solve(A, B, C, f):
    """Return supply, elementary inventory and impact, with A s=f."""
    matrix = np.asarray(A, dtype=float)
    demand = np.asarray(f, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] != demand.size:
        raise ModelError("A must be square and match f")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(demand)):
        raise ModelError("nonfinite matrix or demand")
    try:
        supply = np.linalg.solve(matrix, demand)
    except np.linalg.LinAlgError as exc:
        raise ModelError("singular technology matrix") from exc
    inventory = np.asarray(B, dtype=float) @ supply
    impact = np.asarray(C, dtype=float) @ inventory
    return supply, inventory, impact


class Archive:
    def __init__(self, path: Path):
        self.path = path
        self.zip = ZipFile(path)
        self.members = set(self.zip.namelist())

    def read(self, kind: str, uid: str):
        name = f"{kind}/{uid}.json"
        if name not in self.members:
            return None
        return json.loads(self.zip.read(name))

    def source_sha256(self, kind: str, uid: str) -> str:
        return hashlib.sha256(self.zip.read(f"{kind}/{uid}.json")).hexdigest()


def reference(process):
    refs = [e for e in process.get("exchanges", []) if e.get("isQuantitativeReference")]
    if len(refs) != 1 or refs[0].get("isInput"):
        raise ModelError(f"process {process.get('@id')} has {len(refs)} valid references")
    return refs[0]


def unit_factor(source: str, target: str) -> float:
    if source == target:
        return 1.0
    factors = {("g", "kg"): 0.001, ("kg", "g"): 1000.0,
               ("kWh", "MJ"): 3.6, ("MJ", "kWh"): 1 / 3.6,
               ("t", "kg"): 1000.0, ("kg", "t"): 0.001,
               ("MJ", "MWh"): 1 / 3600, ("MWh", "MJ"): 3600,
               ("kWh", "MWh"): 0.001, ("MWh", "kWh"): 1000,
               ("lb av", "kg"): 0.45359237, ("kg", "lb av"): 1 / 0.45359237,
               ("m3", "l"): 1000, ("l", "m3"): 0.001}
    try:
        return factors[(source, target)]
    except KeyError as exc:
        raise ModelError(f"unit conversion missing: {source} -> {target}") from exc


def build_model(archive: Archive, demand: dict[str, float], method_id=METHOD_ID):
    """Build linked-process model and report every unlinked product and unmatched emission."""
    method = archive.read("lcia_categories", method_id)
    if method is None or method.get("refUnit") != "kg CO2 eq":
        raise ModelError("compatible GWP100 method not found")
    cf = {}
    for factor in method["impactFactors"]:
        key = factor["flow"]["@id"]
        cf[key] = (float(factor["value"]), factor["unit"]["name"])

    processes = {}
    queue = deque(demand)
    missing_processes = []
    while queue:
        uid = queue.popleft()
        if uid in processes:
            continue
        process = archive.read("processes", uid)
        if process is None:
            missing_processes.append(uid)
            continue
        processes[uid] = process
        for exc in process.get("exchanges", []):
            if exc.get("isInput") and exc["flow"].get("flowType") == "PRODUCT_FLOW":
                provider = exc.get("defaultProvider", {}).get("@id")
                if provider and provider not in processes:
                    queue.append(provider)
    ids = sorted(processes)
    index = {uid: i for i, uid in enumerate(ids)}
    n = len(ids)
    rows, cols, vals = [], [], []
    elementary_ids = sorted(cf)
    elementary_index = {uid: i for i, uid in enumerate(elementary_ids)}
    brow, bcol, bval = [], [], []
    unmatched = []
    gaps = []
    unit_errors = []
    by_flow = {}
    for uid in ids:
        j = index[uid]
        process = processes[uid]
        ref = reference(process)
        ref_flow = ref["flow"]["@id"]
        ref_unit = ref["unit"]["name"]
        by_flow[uid] = {"name": process["name"], "reference_flow": ref_flow,
                        "reference_unit": ref_unit, "reference_amount": ref["amount"],
                        "version": process.get("version"),
                        "geography": process.get("location", {}).get("name", "unknown"),
                        "tags": process.get("tags", [])}
        rows.append(j); cols.append(j); vals.append(float(ref["amount"]))
        for exc in process.get("exchanges", []):
            if exc is ref or exc.get("isQuantitativeReference"):
                continue
            flow = exc["flow"]
            flow_type = flow.get("flowType")
            name = flow.get("name", "unknown")
            amount = float(exc.get("amount", 0))
            unit = exc["unit"]["name"]
            if flow_type == "PRODUCT_FLOW" and exc.get("isInput"):
                provider = exc.get("defaultProvider", {}).get("@id")
                if not provider or provider not in index:
                    gaps.append({"process_id": uid, "process": process["name"], "flow": name,
                                 "amount": amount, "unit": unit, "provider_id": provider,
                                 "reason": "no linked provider"})
                    continue
                pref = reference(processes[provider])
                if flow["@id"] != pref["flow"]["@id"]:
                    gaps.append({"process_id": uid, "process": process["name"], "flow": name,
                                 "amount": amount, "unit": unit, "provider_id": provider,
                                 "reason": "provider reference-flow mismatch"})
                    continue
                try:
                    conversion = unit_factor(unit, pref["unit"]["name"])
                except ModelError as err:
                    gaps.append({"process_id": uid, "process": process["name"], "flow": name,
                                 "amount": amount, "unit": unit, "provider_id": provider,
                                 "reason": str(err)})
                    continue
                rows.append(index[provider]); cols.append(j); vals.append(-amount * conversion)
            elif flow_type == "ELEMENTARY_FLOW":
                if flow["@id"] in cf:
                    value, cf_unit = cf[flow["@id"]]
                    try:
                        brow.append(elementary_index[flow["@id"]]); bcol.append(j)
                        bval.append(amount * unit_factor(unit, cf_unit) * (1 if not exc.get("isInput") else -1))
                    except ModelError as err:
                        unmatched.append({"process_id": uid, "flow_id": flow["@id"],
                                          "flow": name, "amount": amount, "unit": unit,
                                          "is_input": bool(exc.get("isInput")), "reason": str(err)})
                elif amount != 0:
                    unmatched.append({"process_id": uid, "flow_id": flow["@id"],
                                      "flow": name, "amount": amount, "unit": unit,
                                      "is_input": bool(exc.get("isInput"))})
            elif flow_type == "PRODUCT_FLOW" and not exc.get("isInput") and amount != 0:
                # Co-products require allocation or system expansion; never credit silently.
                gaps.append({"process_id": uid, "process": process["name"], "flow": name,
                             "amount": amount, "unit": unit, "provider_id": None,
                             "reason": "non-reference product output/allocation unresolved"})

    A = csc_matrix((vals, (rows, cols)), shape=(n, n))
    B = csc_matrix((bval, (brow, bcol)), shape=(len(cf), n))
    C = np.array([cf[uid][0] for uid in elementary_ids])
    direct = np.asarray(C @ B).ravel()
    if unit_errors or missing_processes:
        raise ModelError(f"unit errors: {unit_errors[:5]}; absent processes: {missing_processes[:5]}")
    f = np.zeros(n)
    for uid, qty in demand.items():
        if uid not in index:
            raise ModelError(f"missing demanded process {uid}")
        f[index[uid]] += qty
    try:
        s = spsolve(A, f)
    except Exception as err:
        raise ModelError(f"technology solve failed: {err}") from err
    if not np.all(np.isfinite(s)) or np.max(np.abs(A @ s - f)) > 1e-7:
        raise ModelError("singular or inconsistent technology matrix")
    if np.min(s) < -1e-9:
        raise ModelError("negative supply from provider network")
    g = B @ s
    impact = float(C @ g)
    if not np.isclose(impact, direct @ s, rtol=1e-10, atol=1e-10):
        raise ModelError("contribution sum differs from C B s")
    active_gaps = [dict(g, process_scale=float(s[index[g["process_id"]]]))
                   for g in gaps if s[index[g["process_id"]]] > 1e-12]
    active_unmatched = [g for g in unmatched if s[index[g["process_id"]]] > 1e-12]
    unmatched_summary = Counter((g["flow_id"], g["flow"], g.get("reason", "no CF"))
                                for g in active_unmatched)
    return {"impact_characterized_linked_only_kg_co2e": impact,
            "process_count": n, "active_process_count": int(np.sum(s > 1e-12)),
            "provider_gaps": active_gaps,
            "uncharacterized_exchange_count": len(active_unmatched),
            "uncharacterized_flow_summary": [
                {"flow_id": k[0], "flow": k[1], "reason": k[2], "exchange_count": count}
                for k, count in sorted(unmatched_summary.items())],
            "per_process": [{"process_id": uid, **by_flow[uid], "scale": float(s[index[uid]]),
                             "direct_characterized_kg_co2e_per_process_unit": float(direct[index[uid]]),
                             "contribution_kg_co2e": float(direct[index[uid]] * s[index[uid]])}
                            for uid in ids if s[index[uid]] > 1e-12],
            "balance_residual": float(np.max(np.abs(A @ s - f))),
            "characterized_elementary_flow_count": int(np.sum(np.abs(g) > 0)),
            "method": {"id": method_id, "name": method["name"], "version": method["version"],
                       "unit": method["refUnit"], "factor_count": len(cf)}}
