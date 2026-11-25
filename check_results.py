"""Recalculate figures using the project CSVs and forecasting.py.

Run from the repository root: python check_results.py
Only twelve-month paired years are used for annual correlation.
"""
from pathlib import Path
import pandas as pd
import numpy as np
from forecasting import monthly_samples, evaluate, FEATURES

ROOT = Path(__file__).resolve().parent
GAMES = ['Counter-Strike', 'PUBG']
ALIASES = {'Counter-Strike: Global Offensive': 'Counter-Strike',
           'Counter-Strike Global Offensive': 'Counter-Strike',
           'CS:GO': 'Counter-Strike', 'CS2': 'Counter-Strike',
           'Counter-Strike 2': 'Counter-Strike',
           "PLAYERUNKNOWN'S BATTLEGROUNDS": 'PUBG',
           'PUBG: BATTLEGROUNDS': 'PUBG'}

def load():
    t = pd.read_csv(ROOT / 'twichview.csv', encoding='utf-8-sig')
    t['Game'] = t.Game.replace(ALIASES)
    for col in ['Year', 'Month', 'Avg_viewers']:
        t[col] = pd.to_numeric(t[col], errors='coerce')
    t['Date'] = pd.to_datetime(dict(year=t.Year, month=t.Month, day=1), errors='coerce')
    t = t[t.Game.isin(GAMES)].dropna(subset=['Date'])
    s = pd.read_csv(ROOT / 'steam_selected.csv', encoding='utf-8-sig')
    s['Game'] = pd.to_numeric(s.steam_appid, errors='coerce').map({730: GAMES[0], 578080: GAMES[1]})
    s['Date'] = pd.to_datetime(s.month, format='%y-%b', errors='coerce')
    s['avg_players'] = pd.to_numeric(s.avg_players, errors='coerce')
    s = s.dropna(subset=['Game', 'Date'])
    assert not t.duplicated(['Game', 'Date']).any()
    assert not s.duplicated(['Game', 'Date']).any()
    return s, t

def main():
    s, t = load()
    for game in GAMES:
        paired = t[t.Game.eq(game)].merge(
            s[s.Game.eq(game)][['Date', 'avg_players']], on='Date', validate='one_to_one')
        paired = paired.dropna(subset=['avg_players', 'Avg_viewers']).copy()
        paired['year'] = paired.Date.dt.year
        annual = paired.groupby('year').agg(
            months=('Date', 'nunique'), players=('avg_players', 'mean'),
            viewers=('Avg_viewers', 'mean'))
        full = annual[annual.months.eq(12)]
        samples = monthly_samples(s, t, game)
        scores, preds, selected, counts = evaluate(samples)
        overall = scores['2020 검증 MAE'].idxmin()
        reg = scores.loc[list(FEATURES), '2020 검증 MAE'].idxmin()
        print('\n###', game)
        print('annual paired observations:\n', annual.round(1).to_string())
        print('12-month years:', list(full.index), 'n=', len(full))
        if len(full) >= 3:
            corr = full.players.corr(full.viewers)
            print('12-month annual Pearson r =', round(corr, 4), 'R² =', round(corr*corr, 4))
        print('forecast train/validation/test sample counts:', counts)
        print(scores.round(2).to_string())
        print('best among all:', overall, '| best trained regression:', reg)
        for name in scores.index:
            delta = (preds[name] - preds.actual).abs()
            print('test largest absolute error:', name, delta.idxmax().strftime('%Y-%m'),
                  'error', round(delta.max(), 1),
                  'actual', round(preds.loc[delta.idxmax(), 'actual'], 1),
                  'predicted', round(preds.loc[delta.idxmax(), name], 1))
        print('test months:', ', '.join(preds.index.strftime('%Y-%m')))

if __name__ == '__main__':
    main()
