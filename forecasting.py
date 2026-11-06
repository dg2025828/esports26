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

    st.subheader(f'{game} · 다음 달 Twitch 평균 동시 시청자 예측')
    st.caption('이전 달까지 공개된 월별 수치로 다음 달을 한 달씩 예측합니다. 위의 연도·Twitch 지표 선택과 별개로 고정된 평가 기간과 평균 시청자 수를 사용합니다.')
    try:
        scores, forecasts, chosen, counts = evaluate(monthly_samples(steam, twitch, game))
    except ValueError as exc:
        st.info(str(exc))
        return
    st.write(f'학습: 2019년까지 {counts[0]}개월 · 검증: 2020년 {counts[1]}개월 · 최종 평가: 2021년 1–11월 {counts[2]}개월')
    st.dataframe(scores.round({'alpha': 2, '2020 검증 MAE': 1, '2021 평가 MAE': 1}), use_container_width=True)
    st.caption('MAE: 월별 실제값과 예측값의 절대 오차를 평균한 값(명). 작을수록 좋습니다. 2020년으로 모델과 alpha를 정한 뒤 2020년까지 다시 학습하고 2021년을 평가합니다.')
    st.markdown(f'**2020년 검증에서 선택한 모델: {chosen}**')
    delta = scores.at[RIDGE, '2021 평가 MAE'] - scores.at[FULL, '2021 평가 MAE']
    direction = '줄었습니다' if delta > 0 else '늘었습니다' if delta < 0 else '같았습니다'
    st.write(f'Steam 입력을 추가한 릿지 모델의 2021년 MAE는 Twitch만 사용한 릿지 모델보다 {abs(delta):,.0f}명만큼 {direction}.')
    left, right = st.columns(2)
    for panel, title, models in [
        (left, '단순 선형회귀', [LINEAR]),
        (right, '시차 릿지 회귀', [RIDGE, FULL]),
    ]:
        with panel:
            st.markdown(f'**{title} · 2021년 실제값과 예측값**')
            chart = forecasts[['actual', *models]].rename(columns={'actual': '실제 시청자 수'})
            st.line_chart(chart, x_label='예측 대상 월', y_label='평균 동시 시청자 수(명)')
            st.caption(' · '.join(f"{m} MAE {scores.at[m, '2021 평가 MAE']:,.0f}명" for m in models))
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
