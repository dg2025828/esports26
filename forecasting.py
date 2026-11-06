"""One-month-ahead Twitch forecasts, evaluated on a fixed chronological split."""
import numpy as np
import pandas as pd

ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
BASE = '학습 평균'
LAST = '직전 달 시청자 유지'
LINEAR = 'Steam 선형회귀'
RIDGE = 'Twitch 릿지'
FULL = 'Twitch + Steam 릿지'
FEATURES = {
    LINEAR: ['steam_t'],
    RIDGE: ['twitch_t', 'twitch_t1'],
    FULL: ['twitch_t', 'twitch_t1', 'steam_t'],
}


def monthly_samples(steam, twitch, game):
    s = steam.loc[steam.Game.eq(game), ['Date', 'avg_players']].set_index('Date')
    t = twitch.loc[twitch.Game.eq(game), ['Date', 'Avg_viewers']].set_index('Date')
    monthly = t.join(s, how='left', validate='one_to_one').sort_index().asfreq('MS')
    # Index is the target month. A missing calendar month remains missing.
    return pd.DataFrame({
        'actual': monthly.Avg_viewers,
        'twitch_t': monthly.Avg_viewers.shift(1),
        'twitch_t1': monthly.Avg_viewers.shift(2),
        'steam_t': monthly.avg_players.shift(1),
    }).dropna()


def predict(train, future, columns, alpha):
    x = train[columns].to_numpy(dtype=float)
    z = future[columns].to_numpy(dtype=float)
    y = train.actual.to_numpy(dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale = np.where(scale == 0, 1, scale)
    x = (x - mean) / scale
    z = (z - mean) / scale
    if alpha:
        x = np.vstack([x, np.sqrt(alpha) * np.eye(len(columns))])
        target = np.r_[y - y.mean(), np.zeros(len(columns))]
    else:
        target = y - y.mean()
    coefficients = np.linalg.lstsq(x, target, rcond=None)[0]
    return np.maximum(0, y.mean() + z @ coefficients)


def mae(actual, predicted):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def evaluate(samples):
    train = samples.loc[:'2019-12']
    valid = samples.loc['2020-01':'2020-12']
    test = samples.loc['2021-01':'2021-11']
    if len(train) < 6 or len(valid) < 3 or len(test) < 3:
        raise ValueError('학습·검증·최종 평가에 사용할 월별 관측이 부족합니다.')
    refit = pd.concat([train, valid])
    table = []
    predictions = test[['actual']].copy()
    for name in [BASE, LAST, *FEATURES]:
        alpha = None
        if name == BASE:
            v = np.repeat(train.actual.mean(), len(valid))
            p = np.repeat(refit.actual.mean(), len(test))
        elif name == LAST:
            v, p = valid.twitch_t, test.twitch_t
        else:
            columns = FEATURES[name]
            candidates = (0,) if name == LINEAR else ALPHAS
            alpha = min(candidates, key=lambda a: mae(valid.actual, predict(train, valid, columns, a)))
            v = predict(train, valid, columns, alpha)
            p = predict(refit, test, columns, alpha)
        predictions[name] = p
        table.append({'모델': name, 'alpha': alpha, '2020 검증 MAE': mae(valid.actual, v),
                      '2021 평가 MAE': mae(test.actual, p)})
    scores = pd.DataFrame(table).set_index('모델')
    chosen = scores['2020 검증 MAE'].idxmin()
    return scores, predictions, chosen, (len(train), len(valid), len(test))


def render_forecast(steam, twitch, game):
    import streamlit as st
    import altair as alt
    from dashboard_ui import chart_style, insight, INK, STEAM, TWITCH, BLUE

    st.subheader(f'{game} · 다음 달 시청자를 예측할 수 있을까?')
    st.caption('직전 달까지의 기록으로 다음 달 평균 동시 시청자 수를 예측합니다. 사이드바의 연도·지표 필터와 별개로, 2021년 1–11월의 실제 기록과 비교합니다.')
    try:
        scores, forecasts, chosen, counts = evaluate(monthly_samples(steam, twitch, game))
    except ValueError as exc:
        st.info(str(exc))
        return
    for col, number, title, period, count in zip(st.columns(3), ['01', '02', '03'],
            ['학습', '검증·모델 선택', '최종 평가'], ['2019년까지', '2020년', '2021년 1–11월'], counts):
        col.markdown(f'<div class="split-step">{number} / {title}<b>{period}</b>{count}개월의 기록</div>', unsafe_allow_html=True)
    for col, model, label in zip(st.columns(3), [BASE, LINEAR, FULL],
            ['평균으로 예측 · 기준 오차', '단순 회귀 · 예측 오차', 'Twitch + Steam 릿지 · 예측 오차']):
        col.metric(label, f"{scores.at[model, '2021 평가 MAE']:,.0f}명")
    st.caption('세 카드 모두 2021년 평가 MAE입니다. 실제 시청자 수와 평균적으로 몇 명 차이가 났는지 나타내며, 작을수록 좋습니다.')
    delta = scores.at[RIDGE, '2021 평가 MAE'] - scores.at[FULL, '2021 평가 MAE']
    direction = '줄었습니다' if delta > 0 else '늘었습니다' if delta < 0 else '같았습니다'
    insight(f'2020년 검증에서 선택한 모델은 {chosen}입니다. Steam을 추가한 릿지는 Twitch만 쓴 릿지보다 2021년 오차가 {abs(delta):,.0f}명만큼 {direction}.', '모델 비교에서 발견한 점')
    st.subheader('실제 기록과 예측을 나란히 비교')
    st.caption('실제값은 남색 실선, 예측값은 색깔 점선입니다. 두 그래프의 세로축 범위는 같습니다. 선 위에 마우스를 올리면 월별 수치를 확인할 수 있습니다.')
    ymax = float(forecasts[['actual', LINEAR, RIDGE, FULL]].max().max()) * 1.08
    left, right = st.columns(2)
    for panel, title, models in [
        (left, '단순 선형회귀', [LINEAR]),
        (right, '시차 릿지 회귀', [RIDGE, FULL]),
    ]:
        with panel:
            st.markdown(f'**{title}**')
            chart_data = forecasts[['actual', *models]].rename(columns={'actual': '실제 시청자 수'}).rename_axis('Date').reset_index().melt('Date', var_name='모델', value_name='시청자')
            labels = ['실제 시청자 수', *models]
            colors = {'실제 시청자 수': INK, LINEAR: STEAM, RIDGE: TWITCH, FULL: BLUE}
            chart = alt.Chart(chart_data).mark_line(point=True, strokeWidth=2.5).encode(
                x=alt.X('Date:T', title='예측 대상 월 · 2021년', axis=alt.Axis(format='%m월', tickCount=6, labelAngle=0)),
                y=alt.Y('시청자:Q', title='평균 동시 시청자 수 (명)', scale=alt.Scale(domain=[0, ymax]), axis=alt.Axis(format='~s')),
                color=alt.Color('모델:N', scale=alt.Scale(domain=labels, range=[colors[k] for k in labels])),
                strokeDash=alt.StrokeDash('모델:N', scale=alt.Scale(domain=labels, range=[[1, 0]] + [[6, 3]] * len(models)), legend=None),
                tooltip=[alt.Tooltip('Date:T', title='월', format='%Y-%m'), '모델:N', alt.Tooltip('시청자:Q', format=',.0f')],
            ).properties(height=290)
            st.altair_chart(chart_style(chart), use_container_width=True, theme=None)
            st.caption(' · '.join(f"{m} MAE {scores.at[m, '2021 평가 MAE']:,.0f}명" for m in models))
    st.subheader('어느 모델의 오차가 작을까?')
    score_data = scores.reset_index()
    bars = alt.Chart(score_data).mark_bar(cornerRadiusEnd=4, color=STEAM, size=22).encode(
        y=alt.Y('모델:N', sort=alt.SortField('2021 평가 MAE', order='ascending'), title=None),
        x=alt.X('2021 평가 MAE:Q', title='2021년 평균 절대 오차 MAE (명) · 낮을수록 좋음'),
        tooltip=['모델:N', alt.Tooltip('2021 평가 MAE:Q', format=',.1f')],
    ).properties(height=200)
    st.altair_chart(chart_style(bars), use_container_width=True, theme=None)
    st.caption('막대는 2021년 평가 결과입니다. 최종 모델 선택은 이 순위가 아니라 2020년 검증 결과로 했습니다.')
    with st.expander('전체 모델의 검증·평가 수치와 alpha'):
        st.dataframe(scores.round({'alpha': 2, '2020 검증 MAE': 1, '2021 평가 MAE': 1}), use_container_width=True)
        st.caption('2020년 검증으로 모델과 alpha를 정한 뒤, 2020년까지 다시 학습하고 2021년을 평가했습니다.')
    st.download_button('월별 실제값·예측값 CSV', forecasts.to_csv(index_label='Date').encode('utf-8-sig'),
                       file_name=f'{game}_monthly_forecast.csv')
    with st.expander('모델과 비교 기준'):
        st.markdown(
            '- **학습 평균:** 학습 기간 평균 시청자 수를 모든 평가 월에 사용합니다.\n'
            '- **직전 달 시청자 유지:** 가장 최근에 관측한 시청자 수가 다음 달에도 같다고 가정합니다.\n'
            '- **Steam 선형회귀:** 직전 달 Steam 평균 동시접속자 수로 예측합니다.\n'
            '- **릿지:** 직전 두 달 Twitch 시청자 수를 입력합니다. Steam 추가 버전은 직전 달 Steam 수치도 넣습니다. '
            '입력 표준화에는 학습 자료만 쓰고, alpha가 클수록 회귀계수를 더 줄입니다. '
            '0.01·0.1·1·10·100 중 검증 MAE가 가장 낮은 값을 고릅니다.'
        )
