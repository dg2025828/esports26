# 게임 관심도와 Twitch 시청 관심은 정말 함께 움직이는가?

## 프로젝트 질문

게임 자체에 대한 Google 검색 관심도가 낮아질 때, Twitch에서 해당 게임을 시청하는 관심도도 함께 낮아지는가?

이 프로젝트는 **Google Trends 검색 관심도**와 **Twitch 게임 카테고리의 월별 시청 지표**를 비교한다. Twitch 자료는 대회 중계만 따로 집계한 값이 아니라 해당 게임 카테고리 전체의 방송을 포함한다.

## 데이터 출처와 받는 곳

### 1. Twitch 게임 카테고리 월별 지표

| 항목 | 내용 |
|---|---|
| 데이터 이름 | Top games on Twitch 2016–2023, `Twitch_game_data.csv` |
| 게시자 | Kaggle 사용자 `rankirsh` |
| Kaggle 데이터셋 페이지 | [Top games on Twitch 2016–2023](https://www.kaggle.com/datasets/rankirsh/evolution-of-top-games-on-twitch?select=Twitch_game_data.csv) |
| 바로 받는 공개 사본 | [GitHub raw CSV](https://raw.githubusercontent.com/kgndnc/datasets/main/Twitch_game_data.csv) |
| 원본의 설명 | Twitch에서 월별 상위 200개 게임/카테고리 지표 |
| 이번 프로젝트 폴더 파일의 실제 범위 | 2016-01~2021-11, 14,200행 (월별 상위 200개 행 기준) |

Kaggle 페이지에 소개된 전체 기간은 2016–2023이지만, 현재 프로젝트에서 사용 중인 GitHub 사본의 실제 마지막 월은 **2021년 11월**이다. 따라서 분석 기간은 Google Trends 전체 기간이 아니라 두 자료가 겹치는 기간에 맞춘다. Kaggle 페이지에서 최신 CSV를 내려받을 경우에는 다운로드 후 마지막 `Year`·`Month`를 다시 확인한다.

파일에 포함된 열:

`Rank`, `Game`, `Month`, `Year`, `Hours_watched`, `Hours_Streamed`, `Peak_viewers`, `Peak_channels`, `Streamers`, `Avg_viewers`, `Avg_channels`, `Avg_viewer_ratio`

여기서 `Avg_viewers`는 월평균 동시 시청자 수이며, `Hours_watched`는 월간 총 시청 시간이다. 앱에서 `Avg_viewers`, `Peak_viewers`, `Hours_watched` 중 비교할 Twitch 지표를 선택할 수 있다.

### 2. Google Trends 월별 검색 관심도

| 항목 | 내용 |
|---|---|
| 데이터 이름 | Google Trends 관심도 시간 그래프 CSV 내보내기 |
| 1차 출처 | [Google Trends](https://trends.google.com/trends/) |
| 내려받는 방법 | 게임 검색어/주제를 검색 → 기간·지역·카테고리·검색 유형 설정 → 시간 그래프 오른쪽 위 다운로드 아이콘에서 CSV 저장 |
| 현재 프로젝트 파일 | [esports26 저장소의 Google Trends CSV 5개](https://github.com/dg2025828/esports26) |
| 현재 분석용 범위 | 2016-01~2026-09, 월별 129개월 |

Google Trends에서는 검색어를 비교 화면에 추가한 뒤 그래프를 CSV로 내보낼 수 있다. 자세한 내보내기와 인용 방법은 [Google Trends 공식 안내](https://support.google.com/trends/answer/4365538?hl=en)를 참고한다. 검색 관심도는 시간·지역 등의 조건으로 정규화되어 0–100 범위로 표시된다. 따라서 서로 다른 요청에서 내려받은 게임 파일의 수치 높낮이는 직접 비교하지 않고, **게임별 시간 변화 모양**을 비교한다. 이 정규화 방식과 작은 검색량의 0 표시는 [Google 공식 설명](https://support.google.com/trends/answer/4365533?hl=en)에 정리되어 있다.

현재 프로젝트에 저장된 파일의 링크:

- [League of Legends](https://github.com/dg2025828/esports26/blob/main/League%20of%20Legends_googletrend.csv)
- [Counter-Strike](https://github.com/dg2025828/esports26/blob/main/Counter-Strike_googletrend.csv)
- [Dota 2](https://github.com/dg2025828/esports26/blob/main/Dota%202_googletrend.csv)
- [PUBG](https://github.com/dg2025828/esports26/blob/main/PUBG_googletrend.csv)
- [Valorant](https://github.com/dg2025828/esports26/blob/main/Valorant_googletrend.csv)

**재수집할 때 기록할 조건:** 지역(예: 전 세계), 기간, 카테고리, 검색 유형(Web Search 등), 검색어가 ‘검색어’인지 ‘주제’인지, 다운로드 날짜. 현재 CSV 본문에는 이 조건이 모두 기록되어 있지 않으므로 원래 설정이 확인되지 않으면 README나 분석 로그에 임의로 채워 넣지 않는다.

## 데이터 처리와 결합

1. 앱은 저장소의 게임별 Trends CSV 5개를 읽어 `Month`와 검색어 열을 세로형(`Game`, `Month`, `Series`, `RawValue`, `GoogleTrends`)으로 변환한다. `Year`와 `Month`로 만든 월 날짜를 기준으로 Twitch 행과 결합한다.
2. Twitch의 이름 변형을 정리한다. 예를 들어 `PLAYERUNKNOWN'S BATTLEGROUNDS`와 `PUBG: BATTLEGROUNDS`는 PUBG로 묶고, `Counter-Strike: Global Offensive`는 Counter-Strike로 연결한다. PUBG Mobile은 별도 게임이므로 합치지 않는다.
3. 현재 Twitch CSV의 마지막 월인 2021-11까지만 두 자료의 결합 분석에 사용한다. Google Trends만 단독으로 보는 화면은 2026-09까지 표시한다. 2026-10은 진행 중인 월이라 제외한다.
4. `<1`은 원자료에 표시된 1 미만 값이다. 원문 표기는 `RawValue`에 보존하고, 기본 그래프에서는 0.5로 근사한다. 앱에서 결측으로 바꾼 결과와 비교할 수 있다.
5. PUBG(2017-03 이전), Valorant(2020-03 이전), CS2(2023-09 이전)의 출시 전 구간은 0으로 해석하지 않고 기본 화면에서 결측 처리한다. Valorant의 2020-03 이후 초기 검색은 베타 시기의 관심일 수 있어 정식 출시 후와 구분한다.
6. Twitch 자료는 매월 상위 200개 카테고리를 담는다. 어떤 게임 행이 그 달 파일에 없으면 시청자 수 0이 아니라 **상위 200개 밖이거나 관측되지 않은 결측**으로 둔다.

## 분석 방법

- Streamlit에서 게임과 연도 범위를 선택해 월별 Google Trends와 Twitch 관심 지표를 시각화한다.
- 게임별 Trends와 Twitch 지표의 시계열, 상관관계, 월별 변화율을 비교한다.
- Twitch 지표는 `Avg_viewers`를 주 지표로 삼고, `Hours_watched`와 `Peak_viewers`는 추가 분석에 활용할 수 있다.
- 서로 다른 단위의 값을 한 그래프의 크기로 직접 비교하지 않는다. 필요하면 게임별 표준화 지수로 변환하고, 표준화 기준 기간을 명시한다.

## 한계와 이용 조건

- Twitch 자료는 대회 생중계만 분리하지 않는다. 이 데이터로 답할 수 있는 질문은 **게임 검색 관심과 해당 게임 카테고리의 Twitch 시청 관심이 함께 움직이는지**이며, e스포츠 팬덤의 독립성을 직접 증명하지는 않는다.
- 상위 200개 목록에 없는 달을 0으로 채우면 하락을 과장할 수 있다. 해당 달은 결측으로 처리한다.
- Google Trends는 검색량 절대치가 아닌 정규화된 상대 지수다. Google Trends 데이터를 재사용할 때는 Google을 출처로 표시하고 Google 이용약관을 따른다.
- Kaggle 데이터의 라이선스는 Kaggle 데이터셋 페이지에서 확인한다. 공개 GitHub 사본이 있다는 이유만으로 재배포 권한이 있다고 가정하지 않는다. 출처 표기는 유지한다.
- 현재 사용한 집계 자료에는 개인 이름·연락처·주소·학번 등 개인 식별 정보가 포함되어 있지 않다.

## Streamlit 앱 실행

저장소를 내려받은 뒤 다음 파일들이 같은 폴더에 있는지 확인한다: `app.py`, `requirements.txt`, `Twitch_game_data.csv`, 그리고 `League of Legends_googletrend.csv`, `Counter-Strike_googletrend.csv`, `Dota 2_googletrend.csv`, `PUBG_googletrend.csv`, `Valorant_googletrend.csv`. 앱이 게임별 Trends 원본 CSV를 직접 읽으므로 별도의 통합 CSV를 만들 필요가 없다.

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

