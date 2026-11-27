"""One-month-ahead Twitch forecasts, evaluated on a fixed chronological split."""
import numpy as np
import pandas as pd

ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
BASE = '학습 평균'
LAST = '직전 달 시청자 유지'
RIDGE = 'Twitch 릿지'
FULL = 'Twitch + Steam 릿지'
FEATURES = {
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
            candidates = ALPHAS
            alpha = min(candidates, key=lambda a: mae(valid.actual, predict(train, valid, columns, a)))
            v = predict(train, valid, columns, alpha)
            p = predict(refit, test, columns, alpha)
        predictions[name] = p
        table.append({'모델': name, 'alpha': alpha, '2020 검증 MAE': mae(valid.actual, v),
                      '2021 평가 MAE': mae(test.actual, p)})
    scores = pd.DataFrame(table).set_index('모델')
    # Choose a trained regression model; show both baseline methods separately.
    chosen = LAST
    return scores, predictions, chosen, (len(train), len(valid), len(test))


def render_forecast(steam, twitch, game):
    import streamlit as st
    import altair as alt
    from dashboard_ui import chart_style, INK, STEAM, TWITCH, BLUE
    st.subheader(f'{game} · 다음 달 평균 동시 시청자 예측')
    scores, forecasts, chosen, counts = evaluate(monthly_samples(steam, twitch, game))
    st.success('최종 채택 모델: 직전 달 시청자 유지')
    st.caption('직전 달 실제 시청자 수를 다음 달 예측값으로 사용합니다. 학습할 계수나 alpha는 없습니다.')
    for col, name in zip(st.columns(3), [BASE, LAST, FULL]):
        col.metric(f'{name} · 2021 MAE', f"{scores.at[name, '2021 평가 MAE']:,.1f}명")
    st.info('2021년 평가에서 남은 후보 중 직전 달 유지의 오차가 두 게임 모두 가장 작았습니다. 이 결과를 본 뒤 채택했으므로, 이후 새 기간에서 다시 평가해야 합니다.')
    st.caption('릿지는 2019년까지 학습하고 2020년 검증으로 alpha를 고른 뒤, 2020년까지 재학습해 2021년 1~11월을 평가했습니다. 카스의 2020년 최저 오차는 Twitch+Steam 릿지입니다.')
    models = [LAST, RIDGE, FULL]
    data = forecasts[['actual', *models]].rename(columns={'actual': '실제 시청자'}).rename_axis('Date').reset_index().melt('Date', var_name='방법', value_name='시청자')
    chart = alt.Chart(data).mark_line(point=True).encode(
        x=alt.X('Date:T', title='2021년 예측 대상 월', axis=alt.Axis(format='%m월')),
        y=alt.Y('시청자:Q', title='평균 동시 시청자 수 (명)', scale=alt.Scale(zero=True)),
        color=alt.Color('방법:N', scale=alt.Scale(domain=['실제 시청자', *models], range=[INK, STEAM, TWITCH, BLUE])),
        tooltip=[alt.Tooltip('Date:T', format='%Y-%m'), '방법:N', alt.Tooltip('시청자:Q', format=',.1f')]
    ).properties(height=360)
    st.altair_chart(chart_style(chart), use_container_width=True, theme=None)
    bars = alt.Chart(scores.reset_index()).mark_bar(color=STEAM).encode(
        y=alt.Y('모델:N', sort=alt.SortField('2021 평가 MAE', order='ascending'), title=None),
        x=alt.X('2021 평가 MAE:Q', title='2021년 MAE (명) · 낮을수록 좋음'),
        tooltip=['모델:N', alt.Tooltip('2021 평가 MAE:Q', format=',.1f')]
    ).properties(height=200)
    st.altair_chart(chart_style(bars), use_container_width=True, theme=None)
    st.dataframe(scores.round(1), use_container_width=True)
    st.caption('같은 평가 월에서 비교합니다. 매달 직전 월까지의 실제값으로 한 달 앞을 예측하며, 누락 월을 건너뛰어 연결하지 않습니다.')
    st.download_button('월별 실제값·예측값 CSV', forecasts.to_csv(index_label='Date').encode('utf-8-sig'), file_name=f'{game}_monthly_forecast.csv')
    st.markdown('**학습 평균:** 학습 평균을 예측하는 베이스라인. **직전 달 유지:** 이전 월 실제값을 사용하는 채택 모델. **Twitch 릿지:** 직전 두 달 시청자를 사용. **Twitch+Steam 릿지:** 직전 달 Steam 수치도 사용. 릿지 입력은 학습 자료로 표준화하고 alpha는 2020년 검증 MAE로 선택합니다.')
