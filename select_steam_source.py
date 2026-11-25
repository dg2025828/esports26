"""Extract the two project games from Kaggle Steam Monthly Average Players v2.

Usage: python select_steam_source.py /path/to/steamcharts.csv
The raw source stays untouched. Dates are reformatted for the existing app.
"""
from pathlib import Path
import sys
import pandas as pd

source_path = Path(sys.argv[1])
raw = pd.read_csv(source_path, dtype=str, encoding='utf-8-sig')
columns = ['name', 'steam_appid', 'month', 'avg_players', 'peak_players']
if not set(columns).issubset(raw.columns):
    raise ValueError('Source is missing required columns.')
subset = raw.loc[raw.steam_appid.isin(['730', '578080']), columns].copy()
dates = pd.to_datetime(subset.month, format='%b-%y', errors='raise')
subset = subset.loc[dates.ge('2016-01-01')].copy()
dates = dates.loc[subset.index]
subset['month'] = dates.dt.strftime('%y-%b')
subset['_sort_date'] = dates
subset['_sort_game'] = subset.steam_appid.astype(int)
subset = subset.sort_values(['_sort_game', '_sort_date']).drop(columns=['_sort_game', '_sort_date'])
if subset.duplicated(['steam_appid', 'month']).any():
    raise ValueError('Duplicate game-month rows in source.')
subset.to_csv(Path(__file__).resolve().parent / 'steam_selected.csv', index=False, encoding='utf-8-sig')
print(f'Selected {len(subset)} rows; source had {len(raw)} rows.')
