# BC1 전기주전자 공장 출하 LCA 도구

**[HTML 보고서 보기](results/independent/report.html)** · 브라우저에서 `results/independent/report.html` 파일을 열면 됩니다. 저장된 결과에서 다시 만들려면 `.venv/bin/python scripts/build_html_report.py`를 실행하세요.

## 1. 연구 식별 정보와 목적

공개 별칭 `sung-ps`; 저장소 `https://github.com/sung-ps/LCA`; 독립 실행 ID `bc1-independent-2026-10-08-01` (2026-10-08 UTC). 대표 1 L 플라스틱 전기주전자의 공장 출하 단계 GWP100을 재현 가능하게 계산하는 것이 목적이다. 수업의 다른 독립 결과와 비교할 수 있도록 입력과 누락을 보존했다. 최종 커밋 SHA는 커밋 뒤 확인하며 README에 미래 값을 넣지 않는다. 독립 버전 태그는 `independent-run`이다.

## 2. 제품, 기준단위, 경계

기준단위는 **공장 출하 시 제조·포장된 BC1 대표 주전자 1개**다. [수업 BOM](data/source/classroom/kettle-bom.csv)은 EU Electric Kettles preparatory study (2020), Task 4, Tables 4-3·4-4·4-8을 인용한다. 완제품 주전자 723.00 g + 포장 137.80 g = 860.80 g을 검증했다. [인용 원문](https://publica-rest.fraunhofer.de/server/api/core/bitstreams/3df3f4d6-3717-4261-99e3-a232323111d6/content)은 이 환경에서 접근되지 않아 원문 대조는 **unknown**이다. 첨부 수업 PDF 6쪽과 README 요구 문서는 읽었고, [수업 사이트 양식](data/source/classroom/readme-requirements.md)을 보존했다.

경계에는 원재료 공급, 부품 가공, 조립, 포장이 포함된다. 소비자 배송·사용·수명 종료는 제외하며 별도 확장 계산도 없다. 실제 공장 위치는 **unknown**이다. 계산 가능한 자료에 맞춰 미국 공정으로 모델링했으며 실제 미국 생산을 뜻하지 않는다. 2026은 모델 작성 연도이며 실제 생산 연도는 unknown이다. 수치에 대한 임의 절단 기준은 쓰지 않았다. [사전 결정과 흐름도](docs/decision_log.md)에 경계와 계산 전 PP 최대 기여 예측을 기록했다.

## 3. 전경 목록과 정량 가정

12개 재료별 g·kg와 계산 여부는 [기여도 표](results/independent/contributions.csv), 전체 매칭은 [매칭표](data/processed/mapping-decisions.csv)에 있다. 아래 질량은 모두 **완제품** 질량이다.

| 입력 | 값·단위 | 출처·상태 |
|---|---:|---|
| 주전자 10개 재료 | 723.00 g/개 | 수업 BOM, 출처 확인 |
| 포장 LDPE·판지 | 137.80 g/개 | 수업 BOM, 출처 확인 |
| PP 성형 | 완성 부품 0.35025 kg; 데이터셋 내부 PP 투입 1.034 kg/kg 성형품 및 전력 6.444 MJ/kg | USLCI 공정, 대체 가정 |
| 다른 부품 성형·손실률 | unknown | BOM에 없음; 미확보 |
| 조립 전력 | unknown kWh/개 | 미확보 |
| 공장까지 운송 | unknown t·km/개 | 생산지·거리 미확보 |
| 스크랩·재활용 | unknown kg/개 | 미확보; 추가 크레딧 없음 |
| 가격 | not applicable | 금액 기반 공정 미사용 |

완제품 g를 1000으로 나눠 kg로 환산했다. PP는 완성 1 kg을 출력하는 성형 공정에 0.35025 kg을 요구했으므로 구매 수지상 0.35025 × 1.034 = **0.3621585 kg PP 수지**가 내부 투입으로 모델링된다. 이 투입량을 별도 전경 수지 공정으로 다시 더하지 않았다. 다른 재료는 근거 있는 수율이 없어 구매량 환산이 **not calculated**이며 완제품 질량을 수지 공급 대체 공정의 기준수요로 사용한 부분 계산일 뿐이다.

## 4. 배경 데이터와 매칭

[공정별 UUID·버전·지리·기준단위·URL·조회일·SHA-256·검색 대안·선택 이유](data/processed/mapping-decisions.csv), [두 출처의 검색어와 0건 결과](data/processed/search-log.csv)를 보라. 독립 계산은 공개 [Commons Merged v0.1.0-alpha](https://github.com/FLCAC-admin/commons_merged/releases/tag/v0.1.0-alpha) JSON-LD를 사용했다. ZIP SHA-256은 `02f9986d1e2d9007395b48e710cc94577a7f87e46cdc225c59f7b2659b6eb29a`이다. 그 안의 USLCI 공정은 **v1.2026-06.1** 태그이며 최신 독립 USLCI v1.2026-09.0과 다르다. 9월 독립 패키지는 외부 전력 공급자가 필요하다. Commons Merged는 alpha이고 미국 전력 공정을 포함하지만, 공급자 연결이 모두 완전하지 않다.

선택 공정은 PP 사출 성형, PVC 수지, ABS 수지, LDPE 수지, 평균 골판지 생산 5개다. PP 이외에는 필름·상자·부품 가공이 확정되지 않은 **대체 공정**이다. 스테인리스강·황동·구리·나일론 등 7개 BOM 항목은 적절한 연결 공정이나 등급이 없어 계산하지 않았다. 공개 과거 TianGong `data` 저장소 v0.2.0 / 커밋 `c50cab7961e0b0ca11c26a600bd4c90fea6c6c32`을 검색했지만 중국 공정의 제품·배출 흐름을 미국 FEDEFL 체계와 연결하지 않았다. 공식 CLI `0.1.27`의 브라우저 OAuth는 클라우드 콜백 시간 초과였고 현재 플랫폼 공정 조회는 미완료다. LCA Commons API 자동 조회용 개인 data.gov 키도 미확보다. 누적 배출계수와 금액 기반 계수는 사용하지 않았다.

## 5. 계산·영향평가 방법

Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0으로 작성했다. [계산 코드](src/lca_tool/engine.py)는 공급자별 기준 제품 행을 둔 기술행렬 **A**(산출 +, 투입 −), 기준수요 **f**, FEDEFL 기본 흐름 행렬 **B**, IPCC 특성화 벡터 **C**를 구성하고 `spsolve(A,f)`로 **A·s=f**, **g=B·s**, **h=C·g**를 계산한다. 직접 배출만 전체 발자국으로 간주하지 않는다. 서로 다른 공정의 제품 흐름 UUID와 단위가 맞는 경우에만 연결한다. 불일치·미연결 공급자는 [결과 JSON](results/independent/result.json)에 누락으로 기록한다.

LCIA는 Commons Merged의 **IPCC AR6 / AR6-100 v01.01.004**, 범주 UUID `a6206006-65bc-395c-8dc9-f12262f45a04`, 100년, kg CO₂-eq이다. 흐름 UUID와 단위를 비교한다. 생물기원 탄소의 별도 규칙은 자료에서 검증되지 않아 **unknown**이며 임의 보정하지 않았다. 출처 공정의 `NO_ALLOCATION`을 따르되 비기준 산출물은 미해결로 표시한다. 스크랩 처리와 재활용 크레딧은 unknown, 별도 가산 없음이다. 특성화되지 않은 흐름은 0으로 확정하지 않고 건수·이름을 보고한다.

## 6. 재현 방법

Linux/ Python 3.12 환경에서 아래를 실행한다. 공개 원자료 ZIP은 `.gitignore`된 `data/cache`에 두며 원자료를 재배포하지 않는다. 다운로드 URL과 해시를 고정했다.

```bash
cd /workspace/LCA
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
mkdir -p data/cache
curl -L --fail --output data/cache/Commons_Merged_v0.1.0-alpha.zip https://github.com/FLCAC-admin/commons_merged/releases/download/v0.1.0-alpha/Commons_Merged_v0.1.0-alpha.zip
sha256sum data/cache/Commons_Merged_v0.1.0-alpha.zip
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/kettle-lca --archive data/cache/Commons_Merged_v0.1.0-alpha.zip
.venv/bin/python scripts/finalize_run.py
.venv/bin/python scripts/build_html_report.py
```

해시는 위 값과 일치해야 하며 계산기도 불일치를 거부한다. 입력은 `data/source/classroom/`, 처리 자료는 `data/processed/`, 코드·테스트는 `src/`, `tests/`, 결과는 `results/independent/`, 판단과 프롬프트는 `docs/`에 있다. [SVG 그림](results/independent/partial_contributions.svg)은 브라우저로 연다. 수업 양식과 계산은 계정 없이 재현된다. TianGong 최신 플랫폼 재검색에는 사용자의 공식 브라우저 로그인이 필요하며 비밀번호를 채팅에 보내지 않는다. LCA Commons API를 새로 쓰려면 개인 data.gov 키를 환경 설정에서만 제공해야 한다. 난수 시드는 not applicable이다.

## 7. 결과·검증·해석

**전체 GWP100: not calculated.** 연결된 공정·특성화 흐름에 한정한 합계는 **1.611660 kg CO₂-eq/포장 주전자**다. 이는 전체의 하한이라고도 단정하지 않는다. 다섯 계산 항목의 완제품 질량은 561.55 g이고, 299.25 g의 재료 및 제조·조립·운송 부담이 빠졌다.

| 부분 기여원 | kg CO₂-eq/개 |
|---|---:|
| PP 성형품 | 1.126073 |
| 골판지 제품 | 0.270588 |
| PVC 수지 | 0.118507 |
| ABS 수지 | 0.080776 |
| LDPE 수지 | 0.015717 |

상위 3개는 PP, 골판지, PVC다. 계산 전 PP 최대 기여 예측은 **이 부분 모델 안에서** 맞았다. [검증표](results/independent/checks.json): 12개 BOM·질량·행렬 잔차·기여도 합계 및 명시적 PP 이중계산 방지는 통과; 공급자 연결 2,863건(중복 제거 684건), 특성화되지 않은 기본 흐름 교환 1,350,837건, 전경 7개 미계산으로 전체성 검사는 실패했다. 특성화되지 않은 건수에는 이 영향범주와 무관한 흐름도 포함된다. 따라서 순위 또한 전체 주전자의 확정 순위가 아니다.

## 8. 불확실성·민감도

근거 있는 수율, 나일론 등급, 조립 전력, 실제 전력 지역, 운송 거리가 없어 확률 분포·Monte Carlo·P05/P95는 **not calculated**이다. 임의 범위를 만들지 않았다. [결과 JSON의 결정론적 민감도](results/independent/result.json)는 PP 성형 대체 공정을 같은 0.35025 kg의 수지 공급 공정으로 바꾸면 PP 부분값 1.126073 → 0.751494 kg CO₂-eq, −0.374578 kg (−33.26%)가 된다고 보인다. 성형을 생략한 시나리오이므로 같은 시스템 경계의 완전한 비교는 아니다. 공급자·방법 시나리오와 반복 AI 실행 변동은 not calculated이다.

## 9. Codex와 사람의 결정

표시된 모델은 Codex GPT-6, 실행일 2026-10-08; 기타 설정은 **unknown**이다. 사람은 연구 목표·BOM·GitHub 반영을 지정했고, 실제 공장·제조 자료는 없다고 답했다. 개별 공정 매칭에 대한 사람의 승인·거절은 **not applicable**이다. [프롬프트·오류 수정·실행 기록](docs/prompts_and_runs.md)과 [사전 판단](docs/decision_log.md)에 Codex의 결정과 독립 확인을 기록했다. 실명, 이메일, 수업 코드는 저장소에 넣지 않았다.

## 10. 독립 실행과 수정 실행

[독립 실행 매니페스트](results/independent/run-manifest.json)와 입력·코드·표·[그림](results/independent/partial_contributions.svg)을 `independent-run` 태그로 보존한다. 학급 결과를 보지 않았으므로 수정 실행·변경 전 예상·전후 총량·차이·두 번째 커밋은 **not applicable**이다. 위 PP 비교는 독립 실행 내부 민감도이며 수정 실행이 아니다. 저장소 공개 설정과 수업 비공개 양식 제출은 사용자가 확인·진행해야 한다.
