from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
TWITCH_FILE = ROOT / "Twitch_game_data.csv"
TREND_FILES = {
    "League of Legends": ROOT / "League of Legends_googletrend.csv",
    "Counter-Strike": ROOT / "Counter-Strike_googletrend.csv",
    "Dota 2": ROOT / "Dota 2_googletrend.csv",
    "PUBG": ROOT / "PUBG_googletrend.csv",
    "Valorant": ROOT / "Valorant_googletrend.csv",
}

GAME_ORDER = ["League of Legends", "Counter-Strike", "Dota 2", "PUBG", "Valorant"]
SERIES_COLORS = {
    "Counter-Strike Global Offensive": "#3568a8",
    "Counter-Strike 2": "#e07a28",
    "Dota 2": "#a8443a",
    "League of Legends - Topic 1": "#497b50",
    "PUBG Battlegrounds": "#865fa5",
    "Valorant - Topic 1": "#c74f68",
}
LAUNCH_MONTH = {
    "PUBG Battlegrounds": pd.Timestamp("2017-03-01"),
    "Valorant - Topic 1": pd.Timestamp("2020-03-01"),  # first nonzero beta-era interest in this file
    "Counter-Strike 2": pd.Timestamp("2023-09-01"),
}


@st.cache_data
def load_trends():
    frames = []
    missing = []
    for game, path in TREND_FILES.items():
        if not path.exists():
            missing.append(path.name)
            continue

        wide = pd.read_csv(path, encoding="utf-8-sig")
        if "Month" not in wide.columns:
            raise ValueError(f"{path.name}에 Month 열이 없습니다.")

        long = wide.melt(id_vars="Month", var_name="Series", value_name="RawValue")
        long["Game"] = game
        long["Month"] = pd.to_datetime(long["Month"].astype(str) + "-01", errors="coerce")
        long["RawValue"] = long["RawValue"].astype(str).str.strip()
        long["GoogleTrends"] = pd.to_numeric(
            long["RawValue"].replace({"<1": "0.5", "": None, "nan": None}),
            errors="coerce",
        )
        frames.append(long)

    if missing:
        raise FileNotFoundError("필요한 Google Trends CSV: " + ", ".join(missing))
    return pd.concat(frames, ignore_index=True).dropna(subset=["Month"])


@st.cache_data
def load_twitch():
    df = pd.read_csv(TWITCH_FILE, encoding="latin-1")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Month"] = pd.to_numeric(df["Month"], errors="coerce")
    for col in ["Avg_viewers", "Peak_viewers", "Hours_watched"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Date"] = pd.to_datetime(
        dict(year=df["Year"], month=df["Month"], day=1), errors="coerce"
    )
    aliases = {
        "VALORANT": "Valorant",
        "Counter-Strike: Global Offensive": "Counter-Strike",
        "Counter-Strike": "Counter-Strike",
        "Counter-Strike 2": "Counter-Strike",
        "PLAYERUNKNOWN'S BATTLEGROUNDS": "PUBG",
        "PUBG: BATTLEGROUNDS": "PUBG",
    }
    df["Game_clean"] = df["Game"].replace(aliases)
    return df.dropna(subset=["Date", "Avg_viewers"])


def prepare_trends(df, games, first_year, last_year, below_one, hide_prelaunch):
    out = df[df["Game"].isin(games)].copy()
    out = out[out["Month"].between(pd.Timestamp(f"{first_year}-01-01"),
                                    pd.Timestamp(f"{last_year}-12-31"))]
    if below_one == "결측으로 표시":
        out.loc[out["RawValue"] == "<1", "GoogleTrends"] = float("nan")
    if hide_prelaunch:
        for series, cutoff in LAUNCH_MONTH.items():
            mask = out["Series"].eq(series) & out["Month"].lt(cutoff)
            out.loc[mask, "GoogleTrends"] = float("nan")
    return out


def draw_game_trends(df, game):
    part = df[df["Game"] == game]
    fig, ax = plt.subplots(figsize=(11, 3.3))
    for series, rows in part.groupby("Series", sort=False):
        ax.plot(rows["Month"], rows["GoogleTrends"], lw=1.8,
                label=series, color=SERIES_COLORS.get(series))
    ax.set_title(game, loc="left", weight="bold")
    ax.set_ylabel("Google Trends index")
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.grid(axis="y", color="#d9dde3", lw=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    if game == "PUBG":
        ax.axvline(pd.Timestamp("2017-03-01"), color="#555", ls="--", lw=1)
    if game == "Valorant":
        ax.axvline(pd.Timestamp("2020-03-01"), color="#555", ls="--", lw=1)
    if game == "Counter-Strike":
        ax.axvline(pd.Timestamp("2023-09-01"), color="#777", ls=":", lw=1)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    return fig


def draw_twitch_overlay(trend_df, twitch_df, game, metric, year_start, year_end):
    selected_series = {
        "League of Legends": "League of Legends - Topic 1",
        "Counter-Strike": "Counter-Strike Global Offensive",
        "Dota 2": "Dota 2",
        "PUBG": "PUBG Battlegrounds",
        "Valorant": "Valorant - Topic 1",
    }[game]
    start_date = max(pd.Timestamp(f"{year_start}-01-01"), pd.Timestamp("2016-01-01"))
    end_date = min(pd.Timestamp(f"{year_end}-12-31"), pd.Timestamp("2021-11-30"))
    search = trend_df[
        (trend_df["Game"] == game)
        & (trend_df["Series"] == selected_series)
        & trend_df["Month"].between(start_date, end_date)
    ]
    viewers = twitch_df[
        (twitch_df["Game_clean"] == game)
        & twitch_df["Date"].between(start_date, end_date)
    ].sort_values("Date")

    fig, ax1 = plt.subplots(figsize=(11, 4))
    l1, = ax1.plot(search["Month"], search["GoogleTrends"], color="#3568a8",
                   lw=1.8, label="Google Trends")
    ax1.set_ylabel("Search interest index (0–100)", color="#3568a8")
    ax1.set_ylim(0, 100)
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.grid(axis="y", color="#d9dde3", lw=0.7)
    ax1.spines[["top", "right"]].set_visible(False)

    ax2 = ax1.twinx()
    l2, = ax2.plot(viewers["Date"], viewers[metric], color="#e07a28",
                   lw=1.5, label=metric)
    ax2.set_ylabel(metric, color="#e07a28")
    ax2.spines["top"].set_visible(False)
    ax1.legend([l1, l2], [l1.get_label(), l2.get_label()], frameon=False, loc="upper right")
    ax1.set_title(f"{game}: search interest and Twitch viewing", loc="left", weight="bold")
    ax1.set_xlim(start_date, end_date)
    fig.tight_layout()
    return fig


st.set_page_config(page_title="게임 관심도와 e스포츠", page_icon="🎮", layout="wide")
st.title("게임 관심도와 Twitch 시청 관심")
st.caption("Google Trends와 Twitch 게임 카테고리 자료를 월별로 비교합니다.")
st.markdown("**연구 질문:** 게임 검색 관심도가 감소할 때 Twitch에서 해당 게임을 시청하는 관심도도 함께 감소하는가?")

try:
    trends = load_trends()
    twitch = load_twitch()
except FileNotFoundError as exc:
    st.error(f"필요한 데이터 파일을 찾지 못했습니다: {exc.filename}")
    st.stop()

max_complete_month = pd.Timestamp("2026-09-01")
st.sidebar.header("표시 설정")
games = st.sidebar.multiselect("게임 선택", GAME_ORDER, default=GAME_ORDER)
year_range = st.sidebar.slider("연도 범위", 2016, 2026, (2016, 2026))
below_one = st.sidebar.radio("Google Trends의 `<1` 값", ["0.5로 표시", "결측으로 표시"])
hide_prelaunch = st.sidebar.checkbox("출시 전 구간의 0은 결측 처리", value=True)

shown = prepare_trends(trends, games, year_range[0], year_range[1], below_one, hide_prelaunch)
shown = shown[shown["Month"] <= max_complete_month]

tab_trends, tab_twitch, tab_data = st.tabs(["게임별 검색 관심", "Twitch 시청 비교", "데이터 확인"])
with tab_trends:
    st.info("각 Google Trends 파일은 독립적으로 0–100 정규화되어 있습니다. 게임 간 지수의 높낮이는 직접 비교하지 않고, 게임별 변화 모양을 비교하세요.")
    if not games:
        st.warning("게임을 하나 이상 선택하세요.")
    else:
        for game in games:
            st.pyplot(draw_game_trends(shown, game), clear_figure=True)
    st.caption("`<1`은 1 미만 값입니다. 기본값 0.5는 그래프 표시를 위한 근사치이며, 민감도 확인을 위해 결측 처리도 선택할 수 있습니다. 2026년 10월은 월이 끝나지 않아 제외했습니다.")

with tab_twitch:
    available = [g for g in GAME_ORDER if g in games]
    if not available:
        st.warning("게임을 하나 이상 선택하세요.")
    else:
        metric_labels = {
            "Avg_viewers": "월평균 시청자 수",
            "Peak_viewers": "월간 최고 동시 시청자 수",
            "Hours_watched": "월간 총 시청 시간",
        }
        metric = st.selectbox("Twitch 지표", list(metric_labels), format_func=metric_labels.get)
        paired_results = []
        for game_name in available:
            selected_series = {
                "League of Legends": "League of Legends - Topic 1",
                "Counter-Strike": "Counter-Strike Global Offensive",
                "Dota 2": "Dota 2",
                "PUBG": "PUBG Battlegrounds",
                "Valorant": "Valorant - Topic 1",
            }[game_name]
            search = shown[(shown.Game == game_name) & (shown.Series == selected_series)][["Month", "GoogleTrends"]]
            twitch_part = twitch[twitch.Game_clean == game_name][["Date", metric]].rename(columns={"Date":"Month"})
            paired = search.merge(twitch_part, on="Month", how="inner").dropna()
            paired_results.append({
                "Game": game_name,
                "Matched months": len(paired),
                "Pearson r": paired["GoogleTrends"].corr(paired[metric]) if len(paired) > 1 else float("nan"),
                "Spearman ρ": paired["GoogleTrends"].corr(paired[metric], method="spearman") if len(paired) > 1 else float("nan"),
            })
        st.dataframe(pd.DataFrame(paired_results).round(3), use_container_width=True, hide_index=True)
        game = st.selectbox("그래프로 볼 게임", available)
        if year_range[0] > 2021:
            st.warning("Twitch 월별 자료가 있는 기간(2016–2021년 11월)과 겹치는 연도를 선택하세요.")
        else:
            st.pyplot(draw_twitch_overlay(shown, twitch, game, metric, year_range[0], year_range[1]), clear_figure=True)
    st.warning("보조 축은 Twitch 게임 카테고리 전체 지표입니다. Steam 플레이어 수나 대회 전용 시청자 수가 아니며, 상관은 인과를 뜻하지 않습니다. Twitch 원자료는 2021년 11월까지이고, 상위 200위에서 빠진 달은 0이 아니라 결측입니다.")

with tab_data:
    st.subheader("월별 Google Trends 데이터")
    st.dataframe(shown.sort_values(["Game", "Month", "Series"]), use_container_width=True)
    st.download_button(
        "현재 선택 데이터 CSV 다운로드",
        data=shown.to_csv(index=False).encode("utf-8-sig"),
        file_name="selected_google_trends.csv",
        mime="text/csv",
    )
    st.subheader("자료 범위")
    if shown.empty:
        st.info("현재 선택 조건에 해당하는 Google Trends 행이 없습니다.")
    else:
        st.write(f"Google Trends: {shown['Month'].min():%Y-%m} – {shown['Month'].max():%Y-%m} (월별)")
    st.write(f"Twitch 카테고리 자료: {twitch['Date'].min():%Y-%m} – {twitch['Date'].max():%Y-%m} (월별)")
