from pathlib import Path
import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).resolve().parent
GAMES = ['League of Legends', 'Counter-Strike', 'Dota 2', 'PUBG', 'Valorant']
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
st.title('게임 관심도 × Twitch')
st.markdown('### 게임 검색 관심이 줄어도 Twitch 시청 관심은 유지될까?')
st.caption('원본은 월별 기록입니다. 연도별 그래프는 앱이 계산한 집계이며, 원본 파일을 수정하거나 누락 값을 채우지 않습니다.')
try:
    raw, raw_bytes, twitch, trends = load_data()
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
view, compare, records = st.tabs(['연도별 시청 추이', '게임 관심도와 비교', '데이터·집계 기준'])
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
