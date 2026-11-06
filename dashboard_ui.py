"""Shared presentation for the Streamlit research dashboard."""
from html import escape
import matplotlib.pyplot as plt
import streamlit as st

STEAM = '#16816a'
TWITCH = '#8057cf'
INK = '#182a39'
BLUE = '#377fb6'


def apply_design():
    st.markdown('''<style>
    .stApp {background:#f6f8fa; color:#182a39;}
    [data-testid="stHeader"] {background:rgba(246,248,250,.96);}
    .block-container {max-width:1440px; padding-top:2.4rem; padding-bottom:4rem;}
    [data-testid="stSidebar"] {background:#edf2f4; border-right:1px solid #dbe3e9;}
    h1,h2,h3 {letter-spacing:-.035em; color:#182a39;}
    h3 {font-size:1.25rem !important;}
    [data-testid="stCaptionContainer"] {color:#596a78; line-height:1.7;}
    [data-testid="stMetric"] {background:#fff; border:1px solid #dfe6ec;
      border-radius:12px; padding:18px 20px; min-height:108px;}
    [data-testid="stMetricValue"] {font-size:clamp(1.25rem,2.2vw,1.9rem); color:#182a39;}
    [data-testid="stMetricLabel"] {color:#596a78;}
    [role="tablist"] {gap:8px; margin:14px 0 16px; overflow-x:auto;}
    [role="tab"] {border-radius:7px; padding:10px 15px; white-space:nowrap;}
    [role="tab"][aria-selected="true"] {background:#182a39; color:#fff !important;}
    [data-testid="stExpander"] {background:#fff; border-radius:10px;}
    [data-testid="stDataFrame"] {border-radius:10px; overflow:hidden;}
    [data-testid="stVegaLiteChart"], [data-testid="stImage"] {
      background:#fff; border:1px solid #e1e8ed; border-radius:12px; padding:10px;}
    [data-testid="stDownloadButton"] button {border-color:#cbd8df; border-radius:8px;}
    button:focus-visible, [role="tab"]:focus-visible {outline:3px solid #377fb6 !important; outline-offset:3px;}
    .eyebrow {font-size:11px; font-weight:750; letter-spacing:.16em; color:#16816a; margin:0 0 12px;}
    .hero {padding:8px 0 22px; border-bottom:1px solid #dbe3e9; margin-bottom:22px;}
    .hero h1 {font-size:clamp(1.8rem,3.2vw,2.8rem); line-height:1.25; padding:0; margin:0 0 12px;}
    .hero p {font-size:16px; color:#596a78; margin:0; line-height:1.7;}
    .brand {font-size:24px; font-weight:800; letter-spacing:-.04em; margin-bottom:4px;}
    .brand span {color:#16816a;}
    .side-note {margin-top:28px; padding-top:18px; border-top:1px solid #ced9e0;
      font-size:12px; line-height:1.9; color:#596a78;}
    .insight {border-left:3px solid #16816a; background:#eaf4f0; padding:15px 18px;
      border-radius:0 9px 9px 0; margin:12px 0 20px; color:#203e35; line-height:1.8;}
    .insight strong {display:block; font-size:12px; color:#16816a; margin-bottom:3px;}
    .split-step {border-top:2px solid #cbd8df; padding:12px 0; color:#596a78; font-size:13px;}
    .split-step b {display:block; color:#182a39; font-size:17px; margin:5px 0;}
    @media(max-width:700px) {
      .block-container {padding:1.5rem 1rem 3rem;}
      [role="tab"] {padding:8px 10px;}
      .hero p {font-size:14px;}
      [data-testid="stMetric"] {padding:14px; min-height:90px;}
    }
    </style>''', unsafe_allow_html=True)
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'axes.edgecolor': '#dce4ea', 'axes.labelcolor': '#596a78',
        'text.color': INK, 'xtick.color': '#596a78', 'ytick.color': '#596a78',
        'grid.color': '#dce4ea', 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.titleweight': 'bold', 'axes.titlepad': 18,
        'font.size': 10, 'lines.linewidth': 2.4, 'figure.dpi': 130,
    })


def hero():
    st.markdown('''<section class="hero">
    <div class="eyebrow">GAME & VIEWERS / DATA PROJECT</div>
    <h1>플레이하는 사람, 보는 사람.</h1>
    <p>게임의 동시접속자 수가 줄어도 Twitch 시청 관심은 유지될까?<br>
    Counter-Strike와 PUBG의 이용·시청·검색 기록으로 살펴봅니다.</p>
    </section>''', unsafe_allow_html=True)


def insight(text, title='그래프에서 읽을 점'):
    st.markdown(f'<div class="insight"><strong>{escape(title)}</strong>{escape(text)}</div>', unsafe_allow_html=True)


def chart_style(chart):
    return (chart.configure_view(strokeWidth=0)
            .configure(background='#ffffff', font='sans-serif')
            .configure_axis(labelColor='#596a78', titleColor='#596a78', gridColor='#edf1f4',
                            domain=False, labelFontSize=11, titleFontSize=12, titlePadding=12)
            .configure_legend(orient='top', title=None, labelColor=INK, labelFontSize=12,
                              padding=12, symbolStrokeWidth=3))


def annual_chart(frame, columns, ylabel, title):
    import altair as alt
    labels = {column: label for column, label, _ in columns}
    long = frame[['Year', *labels]].melt('Year', var_name='지표', value_name='값')
    long['지표'] = long['지표'].map(labels)
    chart = alt.Chart(long).mark_line(point=True, strokeWidth=2.8).encode(
        x=alt.X('Year:O', title='연도', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('값:Q', title=ylabel, scale=alt.Scale(zero=False)),
        color=alt.Color('지표:N', scale=alt.Scale(domain=list(labels.values()),
                                                range=[c for _, _, c in columns])),
        tooltip=[alt.Tooltip('Year:O', title='연도'), '지표:N', alt.Tooltip('값:Q', format=',.2f')],
    ).properties(height=310, title=title)
    st.altair_chart(chart_style(chart), use_container_width=True, theme=None)
