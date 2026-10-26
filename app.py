from pathlib import Path
import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).resolve().parent
GAMES = ['Counter-Strike', 'PUBG', 'Dota 2', 'League of Legends', 'Valorant']
FILES = {g: ROOT / f'{g}_googletrend.csv' for g in GAMES}
DEFAULT_SERIES = {'League of Legends': 'League of Legends - Topic 1', 'Counter-Strike': 'Counter-Strike Global Offensive', 'Dota 2': 'Dota 2', 'PUBG': 'PUBG Battlegrounds', 'Valorant': 'Valorant - Topic 1'}
ALIASES = {'VALORANT': 'Valorant', 'Counter-Strike: Global Offensive': 'Counter-Strike', 'Counter-Strike 2': 'Counter-Strike', "PLAYERUNKNOWN'S BATTLEGROUNDS": 'PUBG', 'PUBG: BATTLEGROUNDS': 'PUBG'}
METRICS = {'Avg_viewers': '평균 동시 시청자 수 (월평균의 평균)', 'Peak_viewers': '최고 동시 시청자 수 (관측 월 중 최고값)', 'Hours_watched': '총 시청 시간 (관측 월 합계, 시간)'}

@st.cache_data
def load_data():
    raw_bytes = (ROOT / 'twichview.csv').read_bytes()
    try:
        raw = pd.read_csv(io.BytesIO(raw_bytes), encoding='utf-8-sig')
    except UnicodeDecodeError:
        raw = pd.read_csv(io.BytesIO(raw_bytes), encoding='latin-1')
    required = {'Game', 'Year', 'Month', *METRICS}
    if not required.issubset(raw.columns):
        raise ValueError(f'Twitch 필수 열 누락: {required - set(raw.columns)}')
    twitch = raw.copy()
    for col in ['Year', 'Month', *METRICS]:
        twitch[col] = pd.to_numeric(twitch[col], errors='coerce')
    twitch['Date'] = pd.to_datetime(dict(year=twitch.Year, month=twitch.Month, day=1), errors='coerce')
    twitch['Game'] = twitch.Game.replace(ALIASES)
    twitch = twitch[twitch.Game.isin(GAMES)].dropna(subset=['Date'])
    if twitch.duplicated(['Game', 'Date']).any():
        raise ValueError('동일 게임·월의 Twitch 중복 행이 있습니다. 중복을 확인하세요.')
    frames = []
    for game, path in FILES.items():
        if not path.exists():
            continue
        wide = pd.read_csv(path, encoding='utf-8-sig', dtype=str)
        long = wide.melt(id_vars='Month', var_name='Series', value_name='RawValue')
        long['Date'] = pd.to_datetime(long.Month, errors='coerce')
        long['Game'] = game
        frames.append(long)
    trends = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['Game', 'Series', 'Date', 'RawValue'])
    return raw, raw_bytes, twitch, trends

def aggregate(df):
    data = df.copy()
    data['Year'] = data.Date.dt.year
    return data.groupby(['Game', 'Year'], as_index=False).agg(
        Avg_viewers=('Avg_viewers', 'mean'), Peak_viewers=('Peak_viewers', 'max'),
        Hours_watched=('Hours_watched', lambda s: s.sum(min_count=1)),
        MonthsObserved=('Date', 'nunique'))

def zscore(series):
    std = series.std(ddof=0)
    return (series - series.mean()) / std if pd.notna(std) and std > 0 else series * float('nan')

@st.cache_data
def load_steam():
    source_bytes = (ROOT / 'steam_selected.csv').read_bytes()
    source = pd.read_csv(io.BytesIO(source_bytes), encoding='utf-8-sig')
    needed = {'name', 'steam_appid', 'month', 'avg_players', 'peak_players'}
    if not needed.issubset(source.columns):
        raise ValueError(f'Steam 필수 열 누락: {needed - set(source.columns)}')
    data = source.copy()
    data['steam_appid'] = pd.to_numeric(data.steam_appid, errors='coerce')
    data['Game'] = data.steam_appid.map({730: 'Counter-Strike', 578080: 'PUBG', 570: 'Dota 2'})
    data['Date'] = pd.to_datetime(data.month, format='%y-%b', errors='coerce')
    for column in ['avg_players', 'peak_players']:
        data[column] = pd.to_numeric(data[column], errors='coerce')
    data = data.dropna(subset=['Game', 'Date'])
    data['Year'] = data.Date.dt.year
    if data.duplicated(['Game', 'Date']).any():
        raise ValueError('Steam에 같은 게임·월의 중복 기록이 있습니다.')
    return source, source_bytes, data

def steam_pairs(steam, twitch, game, metric, years, full_only):
    players = steam[steam.Game.eq(game)][['Date', 'avg_players']]
    paired = twitch[twitch.Game.eq(game)].merge(players, on='Date', how='inner', validate='one_to_one')
    paired = paired[paired.Year.between(*years)].dropna(subset=['avg_players', metric])
    result = paired.groupby('Year', as_index=False).agg(
        SteamPlayers=('avg_players', 'mean'),
        Twitch=(metric, 'max' if metric == 'Peak_viewers' else 'sum' if metric == 'Hours_watched' else 'mean'),
        MatchedMonths=('Date', 'nunique'),
        ObservedMonths=('Month', lambda s: ', '.join(str(int(v)) for v in sorted(s.unique()))))
    if full_only:
        result = result[result.MatchedMonths.eq(12)]
    return result.sort_values('Year').reset_index(drop=True)

def yearly_changes(frame, column):
    previous = frame[column].shift()
    # 관측 월 구성이 같은 연속 연도만 변화율을 계산한다.
    valid = frame.Year.diff().eq(1) & previous.gt(0)
    if 'ObservedMonths' in frame.columns:
        valid &= frame.ObservedMonths.eq(frame.ObservedMonths.shift())
    return ((frame[column] / previous - 1) * 100).where(valid)

def line_chart(frame, columns, ylabel, title):
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for column, label, color in columns:
        ax.plot(frame.Year, frame[column], marker='o', lw=2, label=label, color=color)
    ax.set(title=title, xlabel='Year', ylabel=ylabel)
    ax.set_xticks(sorted(frame.Year.unique()))
    ax.grid(alpha=.2)
    ax.spines[['top', 'right']].set_visible(False)
    if len(columns) > 1:
        ax.legend(frameon=False)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

st.set_page_config(page_title='게임 관심도 × Twitch', page_icon='📊', layout='wide')
st.title('게임 이용과 Twitch 시청의 관계')
st.markdown('### 게임의 동시접속자 수가 줄어도 Twitch 시청 관심은 유지될까?')
st.caption('원본은 월별 기록입니다. 연도별 그래프는 앱이 계산한 집계이며, 원본 파일을 수정하거나 누락 값을 채우지 않습니다.')
try:
    raw, raw_bytes, twitch, trends = load_data()
    steam_raw, steam_bytes, steam = load_steam()
except (OSError, ValueError, KeyError) as exc:
    st.error(f'데이터를 읽지 못했습니다: {exc}')
    st.stop()

st.sidebar.header('분석 조건')
game = st.sidebar.selectbox('게임', GAMES)
metric = st.sidebar.selectbox('Twitch 지표', list(METRICS), format_func=METRICS.get)
lo, hi = int(twitch.Year.min()), int(max(twitch.Year.max(), trends.Date.dt.year.max() if not trends.empty else twitch.Year.max()))
years = st.sidebar.slider('연도 범위', lo, hi, (lo, hi))
full_only = st.sidebar.checkbox('Twitch 12개월 관측 연도만', value=False)
annual = aggregate(twitch)
annual = annual[annual.Game.eq(game) & annual.Year.between(*years)]
if full_only:
    annual = annual[annual.MonthsObserved.eq(12)]
a, b, c = st.columns(3)
a.metric('Twitch 원본 행 수', f'{len(raw):,}')
b.metric('Twitch 원본 기간', f'{twitch.Date.min():%Y.%m}–{twitch.Date.max():%Y.%m}')
c.metric('현재 게임의 표시 연도', f'{len(annual)}개')
steam_tab, view, compare, records = st.tabs(['Steam × Twitch 분석', 'Twitch 시청 추이', 'Google Trends 보조 분석', '원본·집계 기준'])
with steam_tab:
    st.subheader('Steam 플레이어 수와 Twitch 시청 지표')
    st.caption('월평균 동시접속자 수는 연간 이용자 총인원이 아닙니다. 기본 지표 Avg_viewers를 선택하면 평균 동시접속자와 평균 동시 시청자를 비교합니다.')
    if game not in steam.Game.unique():
        st.info(f'{game}의 Steam 기록이 현재 파일에 없습니다. Steam 비교는 Counter-Strike와 PUBG에서 사용할 수 있습니다. 다른 게임은 Twitch·Google Trends 탭에서 확인하세요.')
    else:
        solo = steam[steam.Game.eq(game) & steam.Year.between(*years)].groupby('Year', as_index=False).agg(
            SteamPlayers=('avg_players', 'mean'), SteamPeak=('peak_players', 'max'), MonthsObserved=('Date', 'nunique'))
        if full_only:
            solo = solo[solo.MonthsObserved.eq(12)]
        with st.expander('Steam 자체의 장기 추이 (Twitch가 없는 기간 포함)', expanded=False):
            if solo.empty:
                st.info('선택 조건에 해당하는 Steam 기록이 없습니다.')
            else:
                line_chart(solo, [('SteamPlayers', 'Steam average concurrent players', '#188878')], 'Concurrent players', game)
                st.dataframe(solo.round(2), hide_index=True, use_container_width=True)
        result = steam_pairs(steam, twitch, game, metric, years, full_only)
        if result.empty:
            st.info('같은 달로 연결할 수 있는 기록이 없습니다. 기간 또는 12개월 조건을 조정하세요.')
        else:
            st.write(f'공통 비교 기간: {int(result.Year.min())}–{int(result.Year.max())} · {len(result)}개 연도')
            result['SteamZ'] = zscore(result.SteamPlayers)
            result['TwitchZ'] = zscore(result.Twitch)
            line_chart(result, [('SteamZ', 'Steam (Z)', '#188878'), ('TwitchZ', 'Twitch (Z)', '#7753c8')], 'Z-score within selected years', game)
            st.caption('각 지표를 선택 기간의 평균·표준편차(ddof=0)로 표준화했습니다. 연도가 하나이거나 값이 일정하면 표준화 선을 계산할 수 없습니다.')
            x, y = result.SteamPlayers, result.Twitch
            valid_fit = len(result) >= 3 and x.nunique() > 1 and y.nunique() > 1
            left, right = st.columns(2)
            with left:
                fig, ax = plt.subplots(figsize=(5, 3.5))
                ax.scatter(x, y, color='#7753c8')
                for row in result.itertuples():
                    ax.annotate(str(row.Year), (row.SteamPlayers, row.Twitch), fontsize=9)
                if valid_fit:
                    slope = x.cov(y) / x.var()
                    intercept = y.mean() - slope * x.mean()
                    ordered = x.sort_values()
                    ax.plot(ordered, intercept + slope * ordered, color='#188878', label='OLS fit')
                    ax.legend(frameon=False)
                ax.set(xlabel='Steam average concurrent players', ylabel=metric)
                ax.grid(alpha=.2)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
            with right:
                r = x.corr(y) if valid_fit else float('nan')
                st.metric('Pearson 상관계수', f'{r:.3f}' if pd.notna(r) else '계산 불가')
                st.metric('단순 선형회귀 R² (학습 자료 내)', f'{r*r:.3f}' if pd.notna(r) else '계산 불가')
                if valid_fit:
                    st.caption(f'설명변수 x: Steam 평균 동시접속자 / 종속변수 y: 선택한 Twitch 지표. y = {slope:.4f}x + ({intercept:.2f})')
                st.write('관측 연도가 적고 시간 추세가 섞여 있습니다. 회귀선과 R²는 선택한 기록에 대한 설명이며, 미래 예측 정확도나 인과관계를 뜻하지 않습니다.')
            result['PlayersChangePct'] = yearly_changes(result, 'SteamPlayers')
            result['TwitchChangePct'] = yearly_changes(result, 'Twitch')
            result['PlayersDownTwitchMaintained'] = (result.PlayersChangePct.lt(0) & result.TwitchChangePct.ge(0)).where(result.PlayersChangePct.notna() & result.TwitchChangePct.notna())
            if metric == 'Avg_viewers':
                result['ViewerPlayerRatio'] = (result.Twitch / result.SteamPlayers).where(result.SteamPlayers.gt(0))
                st.caption('ViewerPlayerRatio = 평균 동시 시청자 ÷ 평균 동시접속자. 두 집단이 동일한 사람이라는 뜻이 아니며 시청 전환율도 아닙니다.')
            st.subheader('플레이어 감소·시청 관심 유지 구간')
            st.caption('원본에 공통으로 존재하는 달만 집계합니다. 변화율은 관측 월 구성이 동일한 연속 연도에만 계산합니다. MatchedMonths와 ObservedMonths를 확인하세요.')
            st.dataframe(result.round(3), hide_index=True, use_container_width=True)
            hits = result[result.PlayersDownTwitchMaintained.eq(True)]
            if not hits.empty:
                st.write('현재 조건에서 해당하는 연도: ' + ', '.join(hits.Year.astype(str)))
            else:
                st.info('현재 조건에서 조건을 만족하는 연도가 없거나, 비교 가능한 변화율이 부족합니다. 이것만으로 두 관심도가 반드시 함께 움직인다고 결론 내릴 수는 없습니다.')
            st.download_button('Steam × Twitch 비교 CSV (앱 계산)', result.to_csv(index=False).encode('utf-8-sig'), f'{game}_steam_twitch_annual.csv')
        st.warning('Twitch는 2021년 11월까지 있어 두 자료의 공통 비교도 그 시점까지입니다. Steam 최신 기록만으로 Twitch의 이후 값을 추정하거나 채우지 않습니다. 2021년은 11개월, PUBG의 2017년은 출시 초기의 일부 달만 포함합니다.')
    st.subheader('게임별 관계 요약')
    comparisons = []
    for name in ['Counter-Strike', 'PUBG']:
        part = steam_pairs(steam, twitch, name, metric, years, full_only)
        n = len(part)
        r = part.SteamPlayers.corr(part.Twitch) if n >= 3 and part.SteamPlayers.nunique() > 1 and part.Twitch.nunique() > 1 else float('nan')
        comparisons.append({'Game': name, 'Years': n, 'Pearson': r, 'R_squared_in_sample': r*r})
    st.dataframe(pd.DataFrame(comparisons).round(3), hide_index=True, use_container_width=True)
    st.caption('게임별 자료 기간과 관측 월 구성이 달라 상관계수의 크기만으로 순위를 매기지 않습니다. 현재 Steam 파일에는 Dota 2가 없습니다.')

with view:
    st.subheader(f'{game} · 연도별 Twitch 시청')
    if annual.empty:
        st.info('현재 조건에 해당하는 연도별 기록이 없습니다.')
    else:
        line_chart(annual, [(metric, metric, '#7753c8')], metric, game)
        st.dataframe(annual.round(1), hide_index=True, use_container_width=True)
    st.info('Avg_viewers는 서로 다른 사람의 총인원이 아닌 평균 동시 시청자 수입니다. 관측 개월 수가 다른 해의 합계·최고값은 같은 조건의 연간 값으로 비교하기 어렵습니다. 2021년 자료는 11월까지입니다.')
with compare:
    st.subheader('같은 게임·같은 달을 연결한 연도별 비교')
    options = trends.loc[trends.Game.eq(game), 'Series'].dropna().unique().tolist()
    if not options:
        st.info('해당 게임의 Google Trends 파일이 없습니다.')
    else:
        series = st.selectbox('비교할 검색어·주제', options, index=options.index(DEFAULT_SERIES[game]) if DEFAULT_SERIES[game] in options else 0)
        under = st.radio('Google Trends <1 처리', ['결측으로 제외', '0.5로 근사'], horizontal=True)
        search = trends[trends.Game.eq(game) & trends.Series.eq(series)].copy()
        search['GoogleTrends'] = pd.to_numeric(search.RawValue.replace('<1', '0.5' if under == '0.5로 근사' else None), errors='coerce')
        # 출시 이전 데이터도 원본 표에서는 보존한다. 비교에서는 명시한 구간만 사용한다.
        cutoff = {'PUBG': '2017-03-01', 'Valorant': '2020-03-01'}.get(game, '1900-01-01')
        search = search[search.Date.ge(pd.Timestamp(cutoff))]
        paired = twitch[twitch.Game.eq(game)].merge(search[['Date', 'GoogleTrends']], on='Date', how='inner').dropna(subset=['GoogleTrends', metric])
        paired = paired[paired.Year.between(*years)]
        summary = paired.groupby('Year', as_index=False).agg(
            GoogleTrends=('GoogleTrends', 'mean'),
            Twitch=(metric, 'max' if metric == 'Peak_viewers' else 'sum' if metric == 'Hours_watched' else 'mean'),
            MatchedMonths=('Date', 'nunique'))
        if full_only:
            summary = summary[summary.MatchedMonths.eq(12)]
        if summary.empty:
            st.info('겹치는 기록이 없습니다. 연도 범위 또는 12개월 조건을 조정하세요.')
        else:
            summary['SearchZ'] = zscore(summary.GoogleTrends)
            summary['TwitchZ'] = zscore(summary.Twitch)
            line_chart(summary, [('SearchZ', 'Google Trends (Z)', '#287cb4'), ('TwitchZ', 'Twitch (Z)', '#7753c8')], 'Within-game Z-score', game)
            st.caption('선택 기간에서 게임별로 계산한 Z-score입니다. 값이 일정하거나 연도가 하나면 표준화할 수 없습니다.')
            left, right = st.columns(2)
            with left:
                fig, ax = plt.subplots(figsize=(5, 3.5))
                ax.scatter(summary.GoogleTrends, summary.Twitch, c='#7753c8')
                for row in summary.itertuples():
                    ax.annotate(str(row.Year), (row.GoogleTrends, row.Twitch), fontsize=9)
                ax.set(xlabel='Google Trends annual mean', ylabel=metric)
                ax.grid(alpha=.2)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
            with right:
                n = len(summary)
                r = summary.GoogleTrends.corr(summary.Twitch) if n >= 3 and summary.GoogleTrends.nunique() > 1 and summary.Twitch.nunique() > 1 else float('nan')
                st.metric('연도별 Pearson 상관계수', f'{r:.3f}' if pd.notna(r) else '계산 불가')
                st.write(f'비교 연도 수: {n}개. 연도 수가 적고 장기 추세가 섞여 있으므로 인과관계로 해석하지 않습니다.')
            summary = summary.sort_values('Year')
            summary['SearchChangePct'] = summary.GoogleTrends.pct_change(fill_method=None).where(summary.Year.diff().eq(1)) * 100
            summary['TwitchChangePct'] = summary.Twitch.pct_change(fill_method=None).where(summary.Year.diff().eq(1)) * 100
            summary['SearchDownTwitchMaintained'] = (summary.SearchChangePct.lt(0) & summary.TwitchChangePct.ge(0)).where(summary.SearchChangePct.notna() & summary.TwitchChangePct.notna())
            st.subheader('검색 관심 감소·시청 관심 유지 구간 찾기')
            st.caption('연속된 두 해의 관측 개월 구성이 다를 수 있으므로 변화율과 함께 MatchedMonths를 확인하세요.')
            st.dataframe(summary.round(3), hide_index=True, use_container_width=True)
            st.download_button('비교 결과 CSV 받기 (앱 집계)', summary.to_csv(index=False).encode('utf-8-sig'), f'{game}_annual_comparison.csv')
        st.caption('Twitch와 Trends는 공통으로 관측된 달만 연결합니다. PUBG는 2017년 3월, Valorant는 2020년 3월부터 비교합니다. 별도 요청으로 받은 Trends 값의 게임 간 크기는 직접 비교하지 않습니다.')
with records:
    st.subheader('Steam 필터링 자료 (값 유지)')
    st.download_button('steam_selected.csv 그대로 받기', steam_bytes, 'steam_selected.csv', 'text/csv')
    st.dataframe(steam_raw, hide_index=True, use_container_width=True)
    st.caption('이 파일은 업로드된 steam.csv에서 필요한 게임·기간·열을 남긴 자료입니다. 신규 값을 생성하지 않았으며 날짜 해석과 이름 통일은 앱 내부에서만 수행합니다.')
    st.subheader('원본 Twitch 기록')
    st.download_button('twichview.csv 원본 그대로 받기', raw_bytes, 'twichview.csv', 'text/csv')
    st.dataframe(raw, hide_index=True, use_container_width=True)
    st.markdown('''**집계 기준**

- 원본 파일의 모든 값과 파일 바이트를 보존합니다. 그래프는 별도로 계산한 값입니다.
- Avg_viewers: 관측된 월평균의 평균. Peak_viewers: 관측 월 최고값. Hours_watched: 관측 월 합계.
- MonthsObserved / MatchedMonths는 실제 관측한 서로 다른 월의 수입니다. 누락된 달은 0으로 채우지 않습니다.
- 이 파일은 Twitch 게임 카테고리 전체 지표입니다. 대회 중계만의 시청 지표는 아닙니다.
- PUBG·Counter-Strike 등의 명칭은 비교를 위해 앱 내부에서만 통일합니다.

[저장소와 데이터](https://github.com/dg2025828/esports26) · [Kaggle 데이터 설명](https://www.kaggle.com/datasets/rankirsh/evolution-of-top-games-on-twitch)
''')
