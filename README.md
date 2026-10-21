# esports26
# e스포츠 관심도 데이터 프로젝트

## 프로젝트 주제

게임 자체의 관심도가 감소해도 해당 게임의 e스포츠 관심도는 유지될 수 있는가?

## 연구 질문

> 게임 자체의 관심도가 감소해도 e스포츠 관심도는 정말 유지되는가?

게임의 검색 관심도나 플레이어 수가 감소하는 시기에도 대회 시청 관심도가 유지되거나 증가하는 게임이 있는지 분석한다.

## 주제 선정 이유

게임 자체의 관심도가 감소해도 해당 게임의 e스포츠 관심도는 정말 유지되는가?

**주 분석 방법: 회귀분석**

월별 게임 관심도와 e스포츠 관심도는 연속형 수치이므로 회귀분석으로 두 변수의 관계를 살펴본다. 게임별 결과를 비교하고, 게임 관심도가 감소하는 기간에도 e스포츠 관심도가 유지되는 사례가 있는지 확인한다.

이 분석은 변수 사이의 관계를 살펴보는 것이며, 게임 관심도가 e스포츠 관심도를 일으킨다고 단정하지 않는다.

### 관심도 지수

- `GameInterest = [Z(Google Trends) + Z(Avg Players)] / 2`
- 월평균 플레이어 수가 없는 게임은 `GameInterest = Z(Google Trends)`
- `EsportsInterest = [Z(Peak Viewers) + Z(Hours Watched)] / 2`
- `EsportsIndependence = EsportsInterest - GameInterest`

양의 `EsportsIndependence` 값은 표준화된 게임 관심도보다 e스포츠 관심도가 상대적으로 강한 시기를 의미한다. 이 지수 하나만으로 독립성을 확정하지 않고 시계열 그래프, 변화율, 회귀분석 결과와 함께 해석한다.

Google Trends 점수는 실제 검색량이 아니라 선택한 기간과 조건 안에서 정규화된 상대 지수다. 게임별로 따로 내려받은 점수는 서로 다른 기준으로 정규화됐을 수 있으므로 원점수를 게임 간에 바로 비교하지 않는다. 자료를 다시 수집할 때는 검색어, 지역, 기간, 카테고리, 검색 유형을 기록하고 비교 조건을 맞춘다.

## 필요한 데이터와 통합 단위

최종 분석표의 기본 단위는 게임별 월별 관측치 1행이다.

| 열 이름 | 의미 | 진행 상태 |
|---|---|---|
| Game | 게임명 | Trends 파일명으로 구분 가능 |
| Year | 연도 | Month에서 생성 |
| Month | 월 또는 YYYY-MM | Trends CSV에 포함 |
| GoogleTrends | 게임 검색 관심도 | 열 이름 및 검색 조건 확인 필요 |
| AvgPlayers | 월평균 플레이어 수 | 미수집 |
| PeakViewers | 해당 월 대회의 최고 시청자 수 | 미수집; 월별 최댓값으로 집계 |
| HoursWatched | 해당 월 대회 시청 시간 합계 | 미수집; 대회별 자료를 월 단위로 합산 |
| AverageViewers | 평균 시청자 수 | 자료 확보 시 추가 |
| PrizePool | 대회 상금 | 대회별 보조 자료로 수집 |
| TournamentCount | 해당 월 주요 대회 수 | 대회 자료에서 집계 |
| ProMatchCount | 해당 월 프로 경기 수 | 자료 확보 가능 여부 확인 |
| TournamentName | 대회명 | 대회 원자료에 기록 |
| TournamentDate | 대회 날짜 | 대회 원자료에 기록 |
| SourceURL | 데이터 출처 주소 | 자료별로 기록 |
| RetrievedAt | 확인 또는 다운로드 날짜 | 자료 수집 시 기록 |

대회 원자료는 대회별 행으로 보관하고, 날짜를 기준으로 게임별 월 자료에 결합한다. 같은 달에 대회가 여러 개 있으면 시청 시간은 합계, 최고 시청자 수는 최댓값으로 집계한다. 평균 시청자 수는 대회별 단순 평균 대신 방송 시간 가중 평균을 우선 검토한다.

## 데이터 출처

### Google Trends

- 기관·서비스: Google, Google Trends
- 자료명: 게임별 월간 검색 관심도 CSV
- 현재 파일의 기간: 2004년 1월~2026년 10월, 게임별 274개월 행
- 연구에 사용할 기간: 기본적으로 2016년 이후. 게임 출시 전 기간은 제외한다.
- 주소: https://trends.google.com/trends/
- 검색어 또는 Topic: [확인 후 기록]
- 지역: [확인 후 기록]
- 카테고리 및 검색 유형: [확인 후 기록]
- 다운로드 날짜: [확인 후 기록]
- 이용 조건: Google Trends의 최신 이용 조건과 인용·재사용 기준을 확인한 뒤 기록한다. 현재 저장소에는 확인 기록이 없다.

주의 사항:

- 2026년 10월은 월이 끝나기 전에 내려받은 값일 수 있으므로 완결된 달과 구분하거나 분석에서 제외한다.
- `<1` 표시는 숫자 0으로 단정하지 않고 원자료 상태를 보존한 뒤 처리 기준을 정한다.
- 게임 출시 전의 0 또는 낮은 값은 실제 게임 관심도 관측치로 보지 않는다.
- 별도로 내려받은 게임별 점수를 그대로 비교하지 않는다. 비교 조건을 맞춰 데이터를 다시 수집한다.

### 현재 저장소의 Google Trends 파일

| 파일 | 포함 열 | 확인할 내용 |
|---|---|---|
| Counter-Strike_googletrend.csv | Month, Counter-Strike, Counter-Strike Global Offensive, Counter-Strike 2 | 연구 기간에 맞춰 시리즈·CS:GO·CS2 열을 구분 |
| Dota 2_googletrend.csv | Month, Dota 2, Dota 2 Korean | 글로벌 검색과 한국어 검색을 모두 사용할지 결정 |
| League of Legends_googletrend.csv | Month, League of Legends - Topic 1, League of Legends - Topic 2 | 두 Topic의 정확한 의미와 중복 여부 확인 |
| PUBG_googletrend.csv | Month, PUBG Battlegrounds | 검색 조건이 PUBG PC를 나타내는지 확인 |
| Valorant_googletrend.csv | Month, Valorant - Topic 1, Valorant - Topic 2 | 두 Topic의 정확한 의미와 중복 여부 확인 |

### 대회별 시청 데이터 후보

- Esports Charts 대회 목록: https://escharts.com/tournaments  
  대회 기본 정보와 일부 공개 시청 지표 확인에 사용한다.

- Esports Charts Events Dashboard: https://escharts.com/pricing/events  
  대회별 상세 시청 자료와 CSV 내보내기 후보이다. 기본 구매는 단일 대회 기준이며, 여러 대회 자료는 별도 견적이 필요하다. PRO 구독에는 Dashboard가 포함되지 않는다.

- Liquipedia: https://liquipedia.net/  
  대회명, 날짜, 참가 팀, 상금 등 대회 기본 정보를 보완하는 후보이다. 시청자 수를 동일한 기준으로 일괄 제공하는 자료인지는 별도로 확인한다.

- SteamCharts: https://steamcharts.com/  
  Steam 게임의 월평균 플레이어 수 후보이다. Steam에서 제공되지 않는 LoL·Valorant와는 자료 범위가 다르다.

자료를 실제로 사용하기 전에 각 서비스의 최신 이용 조건과 무료 다운로드 범위를 확인하고, 접속 날짜와 함께 기록한다.

## 다른 데이터 후보와 제외 이유

| 후보 | 고려한 내용 | 현재 선택하지 않은 이유 |
|---|---|---|
| SteamCharts 및 Steam 플레이어 자료 | CS2, Dota 2, PUBG의 플레이어 추세 보완 | Steam 게임에 한정되어 LoL·Valorant와 자료 범위가 다름 |
| Esports Charts 유료 Dashboard | 대회별 Peak Viewers, Hours Watched, Average Viewers 등의 상세 자료 | 대회별 구매 또는 다중 대회 견적이 필요해 예산이 확정되지 않음 |
| Liquipedia | 대회 날짜, 상금, 참가 팀 등 기본 정보 | 대회 시청자 수를 동일 기준으로 제공하는 자료가 아님 |
| Twitch 게임 카테고리 통계 | 플랫폼 내 게임 시청 추세 | 대회 방송과 일반 스트리머 방송을 분리하기 어렵고 다른 플랫폼 시청이 포함되지 않음 |

후보 자료를 최종 제외하기 전에 실제 기간, 열, 이용 조건을 확인하고 판단 근거를 보완한다.

## 개인정보 점검

현재 저장된 Google Trends CSV는 월별 검색 관심도와 게임 관련 열로 구성되어 있다. 이름, 연락처, 주소, 학번 등 개인 단위 식별 정보는 포함되어 있지 않다. 이후 추가하는 자료도 개인 식별 정보 포함 여부를 확인한다.

## 평가 기준 진행 상황

| 번호 | 평가 기준 | 현재 상태 |
|---|---|---|
| 1 | 팀원마다 자기 경험으로 주제 선택 이유 설명 | 팀원별 실제 경험 작성 필요 |
| 2 | 연구 질문을 한 문장으로 표현 | 초안 작성 완료 |
| 3 | 회귀·분류·군집 중 방법 선택 및 이유 설명 | 회귀분석 선택 및 이유 기록 |
| 4 | 질문에 필요한 열 이름 설명 | 필요 열 목록 기록; 데이터 수집은 미완료 |
| 5 | 1차 출처·자료명·기간·주소·이용 조건 확인 | Google Trends 후보 기록; 검색 조건과 이용 조건 확인 필요 |
| 6 | 다른 데이터 후보와 제외 이유 설명 | 후보와 현재 판단 기록; 실제 자료 검토 후 보완 필요 |
| 7 | 개인 식별 정보 포함 여부 확인 | 현재 CSV 기준 확인 완료 |
| 8 | 질문·선정 이유·데이터 출처를 GitHub에 정리 | README 초안 정리; 팀원별 경험과 출처 세부정보 보완 필요 |
