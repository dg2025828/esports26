"""교사 피드백: Google Trends 원본 점검과 월별 Steam 보조 축 비교."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

GAMES = ['Counter-Strike', 'PUBG']
# 정식 출시일이 아니라 기존 앱과 일치하는 초기 관심 분석 시작 기준이다.
STARTS = {'PUBG': pd.Timestamp('2017-03-01')}
PREFERRED = {'Counter-Strike': 'Counter-Strike Global Offensive', 'PUBG': 'PUBG Battlegrounds'}
CS_TERMS = ['Counter-Strike', 'Counter-Strike Global Offensive', 'Counter-Strike 2']
CS_METHOD = ('CS·CS:GO·CS2 세 검색어를 각각 Z-score(ddof=0)로 바꾼 뒤 같은 비중으로 평균했습니다. '
             '기준 기간은 파일에 있는 2016년 이후 전체 월로 고정합니다. 세 검색어가 모두 유효한 달만 사용합니다. '
             '이는 팀이 계산한 통합 검색 관심지수이며 검색량 합계나 Google 공식 0~100 지수가 아닙니다. '
             '기준 기간과 검색어별 가중치에 따라 결과가 달라질 수 있습니다.')


def combined_search(long, game):
    """Keep raw observations; construct one explicit composite for CS."""
    if game != 'Counter-Strike':
        return long[long.Series.eq(PREFERRED[game])][['Date', 'Processed']].copy()
    wide = long.pivot(index='Date', columns='Series', values='Processed').reindex(columns=CS_TERMS)
    baseline = wide.loc[wide.index >= pd.Timestamp('2016-01-01')]
    std = baseline.std(ddof=0).replace(0, float('nan'))
    scaled = (wide - baseline.mean()) / std
    # Require all three terms: never change weights when a component is missing.
    score = scaled.mean(axis=1).where(scaled.notna().all(axis=1))
    score = score.where(score.index >= pd.Timestamp('2016-01-01'))
    return score.rename('Processed').reset_index()


def load_search(wide, game, treatment='결측으로 제외'):
    return combined_search(prepare_review(wide, game, treatment, True), game).rename(columns={'Processed': 'GoogleTrends'})


def prepare_review(wide, game, treatment='결측으로 제외', hide_early=True):
    long = wide.melt(id_vars='Month', var_name='Series', value_name='RawValue')
    long['Date'] = pd.to_datetime(long.Month, errors='coerce')
    long['RawValue'] = long.RawValue.astype('string').str.strip()
    numeric = pd.to_numeric(long.RawValue, errors='coerce').astype(float)
    long['OriginalNumeric'] = numeric
    long['IsBelowOne'] = long.RawValue.eq('<1').fillna(False)
    long['Processed'] = numeric
    if treatment == '0.5로 근사':
        long.loc[long.IsBelowOne, 'Processed'] = 0.5
    long['ExcludedEarly'] = False
    if hide_early and game in STARTS:
        mask = long.Date.lt(STARTS[game])
        long.loc[mask, 'Processed'] = float('nan')
        long.loc[mask, 'ExcludedEarly'] = True
    return long


def load_review_files(root):
    return {g: pd.read_csv(root / f'{g}_googletrend.csv', encoding='utf-8-sig', dtype=str)
            for g in GAMES if (root / f'{g}_googletrend.csv').exists()}


def render_trends_review(root, steam):
    files = load_review_files(root)
    st.subheader('Google Trends 원본과 처리 후 그래프 · CS·PUBG')
    st.write('전체 월별 원본을 살펴봅니다. 이 화면은 메인 화면의 연도 필터와 독립적이므로 2016년 이전 구간도 보입니다. 원본 CSV는 수정하지 않습니다.')
    treatment = st.radio('점검 화면의 <1 처리', ['결측으로 제외', '0.5로 근사'], horizontal=True, key='review_under')
    hide_early = st.checkbox('PUBG 2017년 3월 이전 구간 제외', value=True, key='review_early')
    st.caption('PUBG는 2017-03 이전 구간을 비교에서 제외합니다. 해당 구간의 0이나 <1은 실제 이용자가 0명이라는 뜻이 아닙니다.')
    summaries = []
    for game in GAMES:
        if game not in files:
            st.warning(f'{game} CSV가 없어 원본 점검을 할 수 없습니다.')
            continue
        wide = files[game]
        long = prepare_review(wide, game, treatment, hide_early)
        count_early = int(long.ExcludedEarly.sum())
        valid = long.Processed.notna()
        summaries.append({'Game': game, 'SourceRows': len(wide), 'SourceColumns': len(wide.columns),
                          'EmptyCells': int(wide.isna().sum().sum()), 'BelowOneCells': int(long.IsBelowOne.sum()),
                          'LongRowsBefore': len(long), 'ValidObservationsAfter': int(valid.sum()),
                          'ExcludedEarlyObservations': count_early})
        with st.expander(f'{game} · {len(wide)}개월 · <1 {int(long.IsBelowOne.sum())}개', expanded=True):
            fig, axes = plt.subplots(1, 2, figsize=(12, 3.4))
            for series, part in long.groupby('Series', sort=False):
                part = part.sort_values('Date')
                axes[0].plot(part.Date, part.OriginalNumeric, label=series, lw=1.3)
                if game != 'Counter-Strike':
                    axes[1].plot(part.Date, part.Processed, label=series, lw=1.3)
            if game == 'Counter-Strike':
                merged = combined_search(long, game)
                axes[1].plot(merged.Date, merged.Processed, label='Counter-Strike (CS + CS:GO + CS2)', lw=1.5)
            censored = long[long.IsBelowOne]
            if not censored.empty:
                # y=0은 표기 위치다. <1의 실제 측정값을 0으로 간주하지 않는다.
                axes[0].scatter(censored.Date, [0]*len(censored), color='#d45050', marker='v', s=16, label='<1 (marker only)')
            for ax, title in zip(axes, ['Original numeric values', 'After selected processing']):
                ax.set(title=f'{game}: {title}', xlabel='Month', ylabel='Google Trends index (0–100)', ylim=(-3, 103))
                ax.grid(alpha=.2)
                ax.legend(fontsize=6, frameon=False)
            if game in STARTS:
                for ax in axes:
                    ax.axvline(STARTS[game], color='#777', ls='--', lw=1)
            if game == 'Counter-Strike':
                axes[1].set_ylabel('Combined search interest (mean Z-score)')
                axes[1].set_ylim(auto=True)
                axes[1].relim()
                axes[1].autoscale_view(scalex=False, scaley=True)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.caption('왼쪽 빨간 삼각형은 <1의 위치만 y=0에 표시한 것입니다. 실제 값을 0으로 바꾼 것이 아닙니다. 오른쪽은 선택한 처리 방식의 결과입니다.')
            if game == 'Counter-Strike':
                st.caption(CS_METHOD)
                st.write(f'통합 후 유효 월: {int(merged.Processed.notna().sum())}개. 왼쪽은 원본 세 검색어 확인용이며 오른쪽과 아래 비교 그래프는 통합된 한 선입니다.')
            st.write(f'원본 {len(wide)}행·{len(wide.columns)}열, 빈칸 {int(wide.isna().sum().sum())}개, <1 표기 {int(long.IsBelowOne.sum())}개. 숫자로 해석하고 초기 구간을 처리한 뒤 사용 가능한 검색어·월 관측은 {int(valid.sum())}개입니다.')
            st.dataframe(pd.DataFrame({'Column': wide.columns, 'Type': [str(wide[c].dtype) for c in wide], 'EmptyCells': [int(wide[c].isna().sum()) for c in wide]}), hide_index=True, use_container_width=True)
            if not censored.empty:
                st.dataframe(censored[['Month', 'Series', 'RawValue', 'Processed']].head(8), hide_index=True, use_container_width=True)
    st.subheader('처리 전후 개수')
    st.dataframe(pd.DataFrame(summaries), hide_index=True, use_container_width=True)
    st.caption('SourceRows는 원본 월 행, LongRowsBefore와 ValidObservationsAfter는 검색어×월 관측 수입니다. 원본을 세로형으로 바꾸면 단위가 달라지므로 같은 행 수처럼 비교하지 않습니다. LongRowsBefore−ValidObservationsAfter가 선택 처리로 사용하지 않는 관측 수입니다.')
    st.info('현재 구현 방식은 게임별 변화 모양 비교입니다. 별도 요청으로 정규화된 0~100 지수의 높낮이를 게임끼리 직접 비교하지 않습니다. 여러 게임 검색어를 한 요청으로 다시 수집하지 않았습니다.')

    st.subheader('Month로 연결한 Steam × Google Trends 보조 축 선 그래프')
    selected = st.selectbox('월별 보조 축 그래프로 볼 게임', ['Counter-Strike', 'PUBG'], key='review_game')
    if selected not in files:
        st.info('해당 Trends 파일이 없습니다.')
        return
    wide = files[selected]
    long = prepare_review(wide, selected, treatment, hide_early)
    search = combined_search(long, selected)
    if selected == 'Counter-Strike':
        st.caption(CS_METHOD)
    players = steam[steam.Game.eq(selected)][['Date', 'avg_players']]
    if players.empty:
        st.warning(f'{selected} Steam 자료가 없어 비교할 수 없습니다. 원본에 없는 값을 만들지 않습니다.')
        return
    paired = players.merge(search, on='Date', how='inner', validate='one_to_one').dropna().sort_values('Date')
    if paired.empty:
        st.info('공통으로 관측된 월이 없습니다.')
        return
    fig, ax1 = plt.subplots(figsize=(11, 4))
    l1, = ax1.plot(paired.Date, paired.Processed, color='#287cb4', label='Google Trends')
    ax1.set(xlabel='Month', ylabel='Google Trends index (0–100)', ylim=(0, 100), title=f'{selected}: monthly search and Steam players')
    if selected == 'Counter-Strike':
        l1.set_label('Counter-Strike combined search interest')
        ax1.set_ylabel('Combined search interest (mean Z-score)')
        ax1.set_ylim(auto=True)
        ax1.relim()
        ax1.autoscale_view(scalex=False, scaley=True)
    ax2 = ax1.twinx()
    l2, = ax2.plot(paired.Date, paired.avg_players, color='#188878', label='Steam average concurrent players')
    ax2.set_ylabel('Steam average concurrent players')
    ax1.legend([l1,l2], [l1.get_label(),l2.get_label()], frameon=False, fontsize=8)
    ax1.grid(alpha=.2)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    st.write(f'공통 월 {len(paired)}개: {paired.Date.min():%Y-%m}~{paired.Date.max():%Y-%m}. 두 축은 서로 다른 단위이며 선의 높이나 교차 자체에 의미를 부여하지 않습니다.')
    st.dataframe(paired.rename(columns={'Processed':'GoogleTrends'}), hide_index=True, use_container_width=True)

