# 게임 이용이 줄어도 Twitch 시청 관심은 유지될까?

## 분석 범위

Counter-Strike와 PUBG 두 게임의 Steam 플레이어 수와 Twitch 시청 관심을 분석한다. Google Trends는 두 게임의 검색 관심을 확인하는 보조 자료로 사용한다.

핵심 질문은 **게임의 평균 동시접속자 수가 감소하면 Twitch 평균 동시 시청자 수도 정말 감소하는가?** 이다. Steam × Twitch를 핵심 분석으로, Google Trends를 검색 관심의 보조 자료로 사용한다.

## 파일

모두 같은 폴더에 둔다.

- app.py: 앱 실행 파일
- trends_review.py: 원본 점검 및 월별 보조 축 비교
- requirements.txt: 실행 패키지
- steam_selected.csv: Kaggle Steam Monthly Average Players v2에서 추출한 두 게임의 Steam 자료
- select_steam_source.py: 원본 CSV에서 두 게임의 기간·열을 재추출하는 코드
- check_results.py: 주요 결과 재계산 코드
- twichview.csv: Twitch 원본
- Counter-Strike_googletrend.csv, PUBG_googletrend.csv: 두 게임의 Trends 원본
- processing_log.md 및 Log/: 처리 기준과 팀 활동 기록
- README.md: 설명·실행 안내

전체 Twitch 원본에 다른 게임의 행이 포함되어 있어도 파일 자체는 유지하고 앱 분석에서 두 게임만 선택한다. Twitch 입력 파일은 twichview.csv 하나를 사용한다.

## 선생님 피드백 반영

### 원본과 처리 후 선 그래프

'과거 데이터 점검' 목적의 **전처리 점검** 탭에서 전체 월별 기간을 그린다. 메인 화면의 2016년 이후 연도 필터와 독립적이어서 출시 전 구간도 확인할 수 있다. 원본 숫자 그래프와 처리 후 그래프를 나란히 표시한다.

- `<1`은 빈칸이 아니라 1 미만 표기다. 기본값은 비교에서 제외하고, 사용자가 선택할 때만 0.5로 근사한다.
- 원본 그래프의 빨간 삼각형은 `<1`의 날짜 위치만 y=0에 표시한 것이다. 실제 값을 0으로 바꾼 것이 아니다.
- PUBG 2017년 3월 이전 구간은 기본 비교에서 제외한다. 그 이전의 0을 실제 플레이어 0명으로 해석하지 않는다.
- 원본은 수정하지 않는다. 파일별 행·열 수, 자료형, 빈칸과 `<1` 개수, 세로형 처리 전후 유효 관측 수를 화면에 표시한다.

### 게임별 변화 모양 비교

현재 구현은 **게임마다 변화 모양을 비교하는 방식**이다. 여러 게임 검색어를 한 번에 넣어 재수집한 자료를 사용하지 않는다. 서로 다른 요청으로 정규화된 Trends 지수의 게임 간 높낮이를 직접 비교하지 않는다. 핵심 연도별 비교의 Z-score도 선택한 게임과 기간 안에서만 계산한다.

이 기록은 구현된 처리 방식을 설명하며, 팀원이 실제로 논의·합의했다는 증거를 대신하지 않는다. 팀원은 기준을 검토한 뒤 실제 의견을 각자 로그에 작성한다.

### Steam 월별 보조 축 그래프

같은 게임의 Steam 월별 기록과 Trends를 **월 날짜(Date, Month에서 변환)** 로 연결한다. 공통으로 유효한 월만 사용하며 왼쪽 축은 Trends 0~100, 오른쪽 축은 Steam 월평균 동시접속자 수다. 두 축의 단위가 다르므로 선의 교차나 겉보기 높이 차이 자체를 해석하지 않는다.

## 데이터와 기간

| 입력 | 범위 | 행·열 |
|---|---|---|
| steam_selected.csv | CS 2016-01~2025-09, PUBG 2017-03~2025-09 | 220행·5열 |
| twichview.csv 전체 원본 | 2016-01~2021-11 | 14,200행·12열 |
| Counter-Strike Trends | 2004-01~2026-10 | 274행·4열 |
| PUBG Trends | 2004-01~2026-10 | 274행·2열 |

Trends의 마지막 월은 파일을 받은 시점에는 진행 중이던 2026년 10월 값이다. 원본 점검 화면은 보존된 자료를 그대로 표시하며, 그 월을 완전한 월로 재수집한 결과라고 간주하지 않는다. Steam과의 보조 축 비교는 공통 관측 기간인 2025년 9월까지다. Twitch와의 비교는 2021년 11월까지다.

Twitch에서 두 게임 선택 후 132행, Steam 공통 월 결합 후 128행, 연도별 평균 시청자 비교 집계 후 11행이다. 12개월 공통 관측 연도만 선택하면 8행이다. 이 행 수는 Steam × Twitch의 기본 지표 Avg_viewers 기준이다.

Steam의 name·steam_appid·month·avg_players·peak_players를 읽고, Twitch는 Game·Year·Month·Avg_viewers·Peak_viewers·Hours_watched를 사용한다. Steam 앱 ID 730은 CS:GO~CS2의 연속 기록으로 다루며, 과거 값을 CS2 출시 후 기록으로 오해하지 않는다.

## 연도별 핵심 분석

### Counter-Strike 검색어 통합

CS·CS:GO·CS2는 하나의 Counter-Strike 항목으로 분석한다. Google Trends 보조 분석과 Steam 월별 비교에는 세 검색어를 합친 선 하나를 표시한다.

- 원본의 Counter-Strike, Counter-Strike Global Offensive, Counter-Strike 2 열을 각각 Z-score(ddof=0)로 표준화하고 같은 비중으로 평균한다.
- 표준화 기준은 파일의 2016년 이후 전체 월로 고정한다. 화면의 연도 선택에 따라 이 기준을 바꾸지 않는다.
- `<1`은 선택한 기준에 따라 제외하거나 0.5로 근사한다. 세 검색어 중 하나라도 유효하지 않은 달은 통합지수를 계산하지 않는다. 원본의 숫자 0은 유지한다.
- 통합지수 = [Z(CS) + Z(CS:GO) + Z(CS2)] / 3. 실제 검색량 합계나 Google 공식 0~100 지수가 아닌, 팀이 계산한 보조 지표다. 검색어 중복은 제거할 수 없으며 기준 기간·가중치에 따라 결과가 달라질 수 있다.
- 음수·0이 가능한 지수이므로 전년 대비 변화율 대신 지수 차이(SearchIndexChange)를 표시한다. 원본 점검 화면의 세 선은 계산 근거 확인용으로 보존한다.
- Steam 앱 ID 730은 기존과 같이 연속 기록 하나로 사용한다. 원본 Twitch의 CS:GO·CS2 이름은 Counter-Strike로 통일한다.

- Steam 평균 동시접속자: 공통 월의 avg_players 평균
- Twitch Avg_viewers: 공통 월의 월평균 동시 시청자 평균
- Twitch Peak_viewers: 공통 월 중 최댓값
- Twitch Hours_watched: 공통 월의 합계

관측 개월 수와 월 목록을 표시한다. 결측 월은 0이나 추정값으로 채우지 않는다. 관측 월 구성이 같은 연속 연도에만 Steam × Twitch 변화율을 계산한다. 큰 값은 오류로 확인되지 않았으므로 자동 삭제하지 않는다.

Z-score 선 그래프, 산점도, Pearson 상관계수, 단순 최소제곱 회귀선과 자료 내 R², 플레이어 감소·시청 관심 유지 구간을 제공한다. 회귀는 연도가 3개 이상이고 값에 변동이 있을 때만 계산한다. 표본이 작으므로 인과관계나 미래 예측 성능으로 해석하지 않는다.

## 출처와 이용 조건

- Twitch: [Kaggle Top games on Twitch 2016–2023, rankirsh](https://www.kaggle.com/datasets/rankirsh/evolution-of-top-games-on-twitch). 데이터셋 제목과 이번 파일의 실제 기간은 다르다.
- Steam: Victor Laputsky, [Steam Monthly Average Players](https://www.kaggle.com/datasets/lunthu/steam-monthly-average-players), 버전 2(2025년 10월 31일 업데이트), 원자료 steamcharts.csv. 2026년 11월 25일 다운로드하여 Steam 앱 ID 730·578080의 2016년 이후 기록과 필요한 5개 열을 선택했다. 제공자는 [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)으로 표시한다. 제공자 설명상 SteamCharts를 수집한 자료이며 [SteamCharts](https://steamcharts.com/)가 1차 표시 출처다. 수집 사이트 자체 이용 조건도 확인한다. 원본 612,265행·7열, 선택 후 220행·5열. 원본 CSV SHA-256: `07668e0ab970099a28cd83fea2ab34813867e209f255c6b156b3e28aeb3483cb`.
- Steam 대조 표: https://steamcharts.com/app/730 및 https://steamcharts.com/app/578080
- Google Trends: https://trends.google.com/trends/ . 지역·검색 유형·카테고리·주제 구분·다운로드 날짜는 원래 설정을 확인해야 한다.

각 배포처의 라이선스와 이용 조건을 확인한다. 공개라는 이유만으로 재배포 권한을 가정하지 않는다. Google Trends를 이용할 때 출처를 표시한다.

## 한계

Steam 밖의 플레이어·Twitch 밖의 시청자, 월별 상위 200개 목록에서 빠진 기록은 포함하지 않는다. 게임 선택·플랫폼·관측 기간에 편향이 있다. 2021년 Twitch와 PUBG 출시 초기 연도는 일부 월만 포함한다. Twitch 전체 게임 방송은 대회 방송만의 지표가 아니며, 검색·게임 이용·시청은 서로 다른 활동이다. 개인 이름·연락처·주소·학번을 분석하지 않는다.

## 다음 달 Twitch 시청자 예측

- 두 게임 모두 **직전 달 시청자 유지**를 최종 채택함. 직전 달 실제 평균 동시 시청자 수를 다음 달 예측값으로 사용함.
- 비교 목록: 학습 평균, 직전 달 시청자 유지, Twitch 릿지, Twitch+Steam 릿지.
- 릿지: 2019년까지 학습, 2020년 검증으로 alpha 선택, 2020년까지 재학습 후 2021년 1~11월 평가.
- 2021년 평가 MAE: 카스 직전 달 유지 **9,966.6명**, Twitch 릿지 18,675.4명, Twitch+Steam 릿지 12,648.0명. 배그 직전 달 유지 **3,841.5명**, Twitch 릿지 4,157.1명, Twitch+Steam 릿지 4,227.3명.
- 2021년 결과를 본 뒤 채택한 결정임. 이후 새 기간에서 다시 평가해야 함. 카스의 2020년 검증에서는 Twitch+Steam 릿지가 더 정확했음.
- 모든 후보는 같은 관측 월에서 비교함. 직전 두 달 Twitch와 직전 달 Steam이 있는 월만 남기는 기존 조건을 유지하며 누락 월을 건너뛰지 않음.
- MAE는 실제값과 예측값 차이의 절댓값 평균이며 단위는 명임.
- 학습 평균은 입력을 보지 않는 베이스라인임. 직전 달 유지는 이전 시청자 값을 사용하며 학습할 계수·alpha가 없음.
- 확인: `python check_results.py` / 실행: `streamlit run app.py`.

## 느낀 점


- 김단우 : 이번 활동을 통해 나의 생각과 아이디어를 어떻게 탐구해야 할지 기반을 다지는 시간이였다고 생각한다 특히 데이터 분석을 하기 위해 필요한 데이터를 모으는 과정에서 이 데이터를 모으기 어렵다 생각했을때 이를 어떻게 해결할지 방법을 탐색하는데 큰 공을 들였다. 
- 서지우 : 프로젝트를 통해서 팀원과 함께 과제를 탐구하고 분석하면서 내가 어느정도까지의 능력을 가지고 있는지 알 수 있었던 시간이었다.
- 한승민 : 이번 활동을 통해 팀원들과의 우정이 더 돈독해진 것 같다.
