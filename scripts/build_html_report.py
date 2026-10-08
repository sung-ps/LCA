"""Render the saved independent LCA run as a self-contained HTML report."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "independent"


def fmt(value: float, places: int = 3) -> str:
    return f"{value:,.{places}f}"


def render() -> Path:
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    checks = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
    manifest = json.loads((OUT / "run-manifest.json").read_text(encoding="utf-8"))
    rows = result["rows"]
    calculated = sorted((row for row in rows if row["calculated"]),
                        key=lambda row: row["partial_characterized_kg_co2e"], reverse=True)
    missing = [row for row in rows if not row["calculated"]]
    subtotal = result["partial_characterized_kg_co2e"]
    covered_mass = sum(row["finished_mass_g"] for row in calculated)
    missing_mass = sum(row["finished_mass_g"] for row in missing)
    sens = result["sensitivity"]
    pp_diff = sens["resin_only_pp_partial_kg_co2e"] - sens["base_pp_partial_kg_co2e"]
    pp_pct = pp_diff / sens["base_pp_partial_kg_co2e"] * 100
    max_value = calculated[0]["partial_characterized_kg_co2e"]
    bar_rows = "\n".join(
        f'<div class="barrow"><span>{escape(row["material"])}</span>'
        f'<div class="track"><div class="bar" style="width:{row["partial_characterized_kg_co2e"] / max_value * 100:.2f}%"></div></div>'
        f'<strong>{fmt(row["partial_characterized_kg_co2e"], 4)}</strong></div>'
        for row in calculated)
    bom_rows = "\n".join(
        f'<tr><td>{escape(row["material"])}</td><td>{escape(row["scope"])}</td>'
        f'<td class="num">{fmt(row["finished_mass_g"], 2)}</td>'
        f'<td class="num">{fmt(row["partial_characterized_kg_co2e"], 4) if row["calculated"] else "미계산"}</td>'
        f'<td><span class="pill {"ok" if row["calculated"] else "missing"}">{"부분 계산" if row["calculated"] else "자료 미확보"}</span></td></tr>'
        for row in rows)
    check_labels = {
        "bom_rows": "BOM 12개 항목", "kettle_mass_g": "주전자 질량 723 g",
        "packaging_mass_g": "포장 질량 137.8 g", "contribution_sum": "기여도 합계",
        "matrix_balance": "행렬 수지", "provider_closure": "상류 공급자 연결",
        "characterization_coverage": "특성화 범위", "full_foreground_coverage": "전경 범위",
        "double_counting": "PP 수지 이중 계산 방지",
    }
    checks_html = "\n".join(
        f'<li><span>{label}</span><span class="pill {"ok" if str(checks[key]["status"]).startswith("pass") else "missing"}">'
        f'{"통과" if str(checks[key]["status"]).startswith("pass") else "미완료"}</span></li>'
        for key, label in check_labels.items())
    run_date = escape(result["run_date_utc"][:10])
    report = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BC1 전기주전자 LCA | 독립 실행 보고서</title>
<style>
:root{{--ink:#173149;--muted:#526877;--navy:#102d42;--teal:#117b75;--soft:#eff6f5;--line:#d8e3e7;--warn:#8b4a15;--warnbg:#fff3e4}}
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7f8;color:var(--ink);font:16px/1.62 system-ui,-apple-system,"Noto Sans KR",sans-serif}}
.wrap{{max-width:1050px;margin:auto;padding:34px 20px 80px}}header{{background:linear-gradient(130deg,#102d42,#155a67);color:white;padding:42px;border-radius:20px}}
header p{{color:#d7eded;max-width:760px}}h1{{font-size:clamp(2rem,4vw,3rem);line-height:1.2;margin:9px 0 16px}}h2{{font-size:1.4rem;margin:0 0 15px}}h3{{font-size:1.05rem;margin:24px 0 8px}}
.eyebrow{{letter-spacing:.13em;text-transform:uppercase;font-size:.8rem;font-weight:700}}.meta{{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}}.meta span{{border:1px solid #77a5aa;border-radius:99px;padding:5px 12px;font-size:.84rem}}
nav{{display:flex;flex-wrap:wrap;gap:8px;margin:24px 0}}nav a{{color:var(--navy);background:white;border:1px solid var(--line);border-radius:99px;padding:7px 13px;text-decoration:none;font-size:.88rem}}
section{{background:white;border:1px solid var(--line);border-radius:17px;padding:27px;margin:18px 0;box-shadow:0 5px 24px #17314908}}
.alert{{background:var(--warnbg);border-left:5px solid #c98034;padding:16px 19px;border-radius:8px;color:#663809;margin:24px 0}}
.metricgrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}}.metric{{background:var(--soft);padding:20px;border-radius:12px}}.metric small{{display:block;color:var(--muted)}}.metric strong{{display:block;font-size:1.75rem;line-height:1.25;margin-top:5px}}.metric .unit{{font-size:.83rem;color:var(--muted)}}
.barrow{{display:grid;grid-template-columns:245px 1fr 85px;align-items:center;gap:12px;margin:13px 0;font-size:.89rem}}.barrow strong{{text-align:right;font-variant-numeric:tabular-nums}}.track{{height:18px;background:#e8f0f2;border-radius:99px;overflow:hidden}}.bar{{height:100%;background:linear-gradient(90deg,#177f83,#56b7a8);border-radius:99px}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}th,td{{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left}}th{{background:#f2f6f7}}.num{{text-align:right;font-variant-numeric:tabular-nums}}.scroll{{overflow-x:auto}}
.pill{{display:inline-block;border-radius:99px;padding:2px 9px;font-size:.76rem;white-space:nowrap}}.pill.ok{{background:#dbf2e9;color:#11634d}}.pill.missing{{background:#fff0db;color:#85500e}}
.checks{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(2,1fr);gap:8px}}.checks li{{display:flex;justify-content:space-between;gap:12px;background:#f5f8f8;border-radius:8px;padding:9px 12px}}
.flow{{display:flex;flex-wrap:wrap;align-items:center;gap:7px}}.flow span{{background:#e8f2f1;border:1px solid #bed8d5;border-radius:8px;padding:10px 13px}}.flow b{{color:var(--teal)}}
a{{color:#087671}}.links{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}}.links a{{background:#eef6f5;padding:10px 13px;border-radius:8px;text-decoration:none}}
footer{{color:var(--muted);font-size:.85rem;margin-top:26px}}@media(max-width:700px){{.metricgrid,.checks,.links{{grid-template-columns:1fr}}.barrow{{grid-template-columns:115px 1fr 62px;font-size:.75rem}}header{{padding:28px}}section{{padding:19px}}}}
@media print{{body{{background:white}}.wrap{{padding:0;max-width:none}}section{{break-inside:avoid;box-shadow:none}}nav{{display:none}}header{{print-color-adjust:exact}}}}
</style></head><body><main class="wrap">
<header><div class="eyebrow">Life Cycle Assessment · Independent run</div><h1>BC1 전기주전자 LCA 보고서</h1>
<p>공장 출하 시점의 1 L 플라스틱 전기주전자 1개와 포장재를 대상으로 한 독립 실행입니다. 실제 자료로 계산한 범위와 아직 확보하지 못한 범위를 함께 제시합니다.</p>
<div class="meta"><span>실행 {escape(result["run_id"])}</span><span>UTC {run_date}</span><span>미국 공정 모델링 · 실제 제조지 미상</span></div></header>
<nav><a href="#summary">요약</a><a href="#boundary">연구 범위</a><a href="#contrib">부분 기여도</a><a href="#bom">BOM</a><a href="#quality">검증·한계</a><a href="#methods">방법·재현</a></nav>
<section id="summary"><h2>핵심 결과</h2><div class="alert"><strong>전체 GWP100은 미계산입니다.</strong> 아래 값은 연결된 다섯 배경 공정에서 특성화된 배출의 부분 합계입니다. 누락된 재료·가공·조립·운송 부담이 있으므로 전체값이나 하한으로 해석할 수 없습니다.</div>
<div class="metricgrid"><div class="metric"><small>부분 특성화 합계</small><strong>{fmt(subtotal, 4)}</strong><span class="unit">kg CO₂-eq / 포장 주전자</span></div>
<div class="metric"><small>계산에 포함된 완제품 질량</small><strong>{fmt(covered_mass, 2)} g</strong><span class="unit">전체 860.80 g 중 5개 BOM 항목</span></div>
<div class="metric"><small>재료 계산 누락</small><strong>{fmt(missing_mass, 2)} g</strong><span class="unit">7개 BOM 항목 · 조립/운송 별도 미확보</span></div></div></section>
<section id="boundary"><h2>제품과 시스템 경계</h2><p>기준단위는 <strong>공장 출하 시 제조·포장된 BC1 대표 전기주전자 1개</strong>입니다. 완제품 주전자 723.00 g, 포장 137.80 g, 합계 860.80 g입니다. 소비자 배송, 사용 단계, 수명 종료는 제외합니다.</p>
<div class="flow" aria-label="시스템 경계 흐름도"><span>원재료 공급</span><b>→</b><span>부품 제조</span><b>→</b><span>조립</span><b>→</b><span>포장</span><b>→</b><span>공장 출하</span></div>
<p>수업 BOM은 EU Electric Kettles preparatory study (2020), Task 4의 표를 인용합니다. 인용 원문에 대한 직접 대조는 접근 제한으로 미완료입니다. 실제 공장 위치와 생산 연도는 알려지지 않았으며 미국 공정은 모델링 가정입니다.</p></section>
<section id="contrib"><h2>계산된 다섯 항목의 부분 기여도</h2><p>단위: kg CO₂-eq/포장 주전자. 이 그래프의 합계는 전체 제품 발자국이 아닙니다.</p>{bar_rows}
<p>계산 전 가장 큰 기여원으로 예측한 PP 성형품이 <strong>이 부분 모델에서는 1위</strong>였습니다. 다음은 골판지 제품과 PVC 수지입니다.</p></section>
<section id="bom"><h2>전경 BOM과 계산 상태</h2><div class="scroll"><table><thead><tr><th>재료</th><th>범위</th><th class="num">완제품 질량 (g)</th><th class="num">부분 기여도 (kg CO₂-eq)</th><th>상태</th></tr></thead><tbody>{bom_rows}</tbody></table></div>
<p>PP 성형 공정은 완성 부품 1 kg당 PP 수지 1.034 kg과 전력 6.444 MJ를 이미 포함합니다. 다른 재료의 제조 수율과 성형 공정, 조립 전력, 공장 유입 운송, 스크랩 처리는 자료가 없어 계산하지 않았습니다.</p></section>
<section id="quality"><h2>검증과 해석 한계</h2><ul class="checks">{checks_html}</ul>
<p>공급자 미연결 <strong>{checks["provider_closure"]["gap_instances"]:,}건</strong>(중복 제거 {checks["provider_closure"]["distinct_gaps"]:,}건), 특성화되지 않은 기본 흐름 교환 <strong>{checks["characterization_coverage"]["uncharacterized_exchange_instances"]:,}건</strong>입니다. 마지막 건수에는 GWP와 무관한 흐름도 포함됩니다. 미계산 항목을 배출량 0으로 처리하지 않았습니다.</p>
<h3>대체 공정 민감도</h3><p>PP 성형품을 같은 질량의 PP 수지 공정으로 교체하면 해당 부분값은 {fmt(sens["base_pp_partial_kg_co2e"], 4)}에서 {fmt(sens["resin_only_pp_partial_kg_co2e"], 4)} kg CO₂-eq로 바뀝니다 ({fmt(pp_diff, 4)}, {fmt(pp_pct, 2)}%). 수지 공정은 성형을 포함하지 않아 동일 경계의 완전한 대안은 아닙니다. 확률 분포와 P05/P95는 근거 자료 부족으로 계산하지 않았습니다.</p></section>
<section id="methods"><h2>데이터·방법·재현</h2><p>배경 데이터는 공개 Commons Merged <strong>v0.1.0-alpha</strong>의 USLCI v1.2026-06.1 및 미국 전력 공급 공정입니다. 특성화 방법은 <strong>IPCC AR6-100 v01.01.004</strong>, 100년 지평입니다. TianGong 역사 자료는 후보 검색에 사용했으나 흐름 체계가 검증되지 않아 계산에 합치지 않았습니다.</p>
<p>계산기는 공급자별 기술행렬 A, 기본 흐름 B, 특성화 C로 <code>A·s=f, g=B·s, h=C·g</code>를 풉니다. PP 수지와 성형 부담은 중복 합산하지 않았습니다. 생물기원 탄소 처리, 미연결 공급자, 미특성화 흐름은 상세 결과를 참조하십시오.</p>
<p>재현 방법과 설치 명령은 저장소 README에 있습니다. 이 HTML은 저장된 JSON 결과에서 생성되며 브라우저에서 파일을 열면 됩니다.</p>
<div class="links"><a href="../../README.md">README · 전체 방법</a><a href="run-manifest.json">실행 매니페스트</a><a href="../../data/processed/mapping-decisions.csv">데이터 매칭 결정</a><a href="../../data/processed/search-log.csv">데이터 검색 기록</a><a href="checks.json">검증 결과</a><a href="contributions.csv">기여도 CSV</a><a href="result.json">상세 계산 JSON</a><a href="../../docs/decision_log.md">사전 판단 기록</a></div></section>
<footer>공개 별칭 {escape(manifest["student_alias"])} · 독립 실행 결과 보존 · 원자료 ZIP은 재배포하지 않음 · 이 보고서는 전체 GWP100 결과가 아님</footer>
</main></body></html>'''
    path = OUT / "report.html"
    path.write_text(report, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(render())
