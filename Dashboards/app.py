import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ODI Cricket Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background-color: #0a0f1e; }
    .stApp { background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 100%); }

    .metric-card {
        background: linear-gradient(135deg, #1a2744 0%, #0f1f3d 100%);
        border: 1px solid #2d4a7a;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 5px 0;
    }
    .metric-card h2 { color: #00d4ff; font-size: 2rem; margin: 0; }
    .metric-card p  { color: #8899bb; font-size: 0.85rem; margin: 4px 0 0; }

    .section-header {
        background: linear-gradient(90deg, #00d4ff22, transparent);
        border-left: 4px solid #00d4ff;
        padding: 10px 16px;
        border-radius: 0 8px 8px 0;
        margin: 20px 0 12px;
        color: #e0eaff;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    .stSelectbox > div > div { background: #1a2744 !important; color: #e0eaff !important; }
    .stMultiSelect > div { background: #1a2744 !important; }
    .stSlider > div { color: #e0eaff; }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #0a0f1e 100%) !important;
        border-right: 1px solid #2d4a7a;
    }
    div[data-testid="stSidebar"] * { color: #c8d8f0 !important; }

    .tab-content { padding: 10px 0; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ─── Data Loading ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        match_data = pd.read_csv("ODI_Match_Data.csv")
        match_info = pd.read_csv("ODI_Match_info.csv")
    except FileNotFoundError:
        st.error("❌ CSV files not found! Please place 'ODI_Match_Data.csv' and 'ODI_Match_info.csv' in the same folder as app.py")
        st.stop()

    # ── Clean match_info ──
    match_info.columns = match_info.columns.str.strip().str.lower().str.replace(' ', '_')
    match_info['date'] = pd.to_datetime(match_info['date'], errors='coerce')
    match_info['year'] = match_info['date'].dt.year
    match_info.drop_duplicates(inplace=True)

    # ── Clean match_data ──
    match_data.columns = match_data.columns.str.strip().str.lower().str.replace(' ', '_')
    match_data.drop_duplicates(inplace=True)

    # ── Numeric fixes ──
    for col in ['runs_batter', 'runs_extras', 'runs_total']:
        if col in match_data.columns:
            match_data[col] = pd.to_numeric(match_data[col], errors='coerce').fillna(0)

    return match_data, match_info


match_data, match_info = load_data()

# ─── Sidebar Filters ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏏 ODI Analytics")
    st.markdown("---")

    all_teams = sorted(set(
        match_info.get('team1', pd.Series()).dropna().tolist() +
        match_info.get('team2', pd.Series()).dropna().tolist()
    ))

    selected_teams = st.multiselect(
        "🌍 Select Teams",
        options=all_teams,
        default=["Pakistan", "India", "Australia"] if all(t in all_teams for t in ["Pakistan", "India", "Australia"]) else all_teams[:3]
    )

    min_year = int(match_info['year'].min()) if 'year' in match_info.columns else 2002
    max_year = int(match_info['year'].max()) if 'year' in match_info.columns else 2023
    year_range = st.slider("📅 Year Range", min_year, max_year, (min_year, max_year))

    venues = ["All Venues"] + sorted(match_info['venue'].dropna().unique().tolist()) if 'venue' in match_info.columns else ["All Venues"]
    selected_venue = st.selectbox("🏟️ Venue", venues)

    st.markdown("---")
    st.markdown("**Dataset Info**")
    st.markdown(f"📊 Matches: **{len(match_info):,}**")
    st.markdown(f"🎯 Balls: **{len(match_data):,}**")
    st.markdown(f"📅 Period: **{min_year}–{max_year}**")
    st.markdown("---")
    st.markdown("*Built with ❤️ using Python + Streamlit*")

# ─── Filter Data ────────────────────────────────────────────────────────────────
def filter_matches(df):
    mask = pd.Series([True] * len(df), index=df.index)
    if 'year' in df.columns:
        mask &= df['year'].between(year_range[0], year_range[1])
    if selected_venue != "All Venues" and 'venue' in df.columns:
        mask &= df['venue'] == selected_venue
    if selected_teams:
        team_mask = pd.Series([False] * len(df), index=df.index)
        for t in selected_teams:
            for col in ['team1', 'team2', 'winner']:
                if col in df.columns:
                    team_mask |= df[col] == t
        mask &= team_mask
    return df[mask]

filtered_info = filter_matches(match_info)

# Merge ball data with filtered match ids
filtered_ids = set(filtered_info['match_id'].tolist()) if 'match_id' in filtered_info.columns else set()
filtered_balls = match_data[match_data['match_id'].isin(filtered_ids)] if 'match_id' in match_data.columns else match_data

# ─── Helper Colors ───────────────────────────────────────────────────────────────
COLORS = px.colors.qualitative.Bold
TEMPLATE = "plotly_dark"
BG = "#0d1b2a"
PAPER = "#0a0f1e"


def styled_fig(fig, title=""):
    fig.update_layout(
        template=TEMPLATE,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        font=dict(family="Inter", color="#c8d8f0"),
        title=dict(text=title, font=dict(size=14, color="#00d4ff")) if title else None,
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style='text-align:center; padding: 20px 0 10px;'>
    <h1 style='color:#00d4ff; font-size:2.4rem; margin:0; letter-spacing:1px;'>🏏 ODI Cricket Analytics</h1>
    <p style='color:#556688; font-size:1rem; margin:4px 0 0;'>Men's ODI Match Data • 2002–2023</p>
</div>
""", unsafe_allow_html=True)

# ─── KPI Cards ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
total_matches = len(filtered_info)
total_teams   = len(all_teams)
total_runs    = int(filtered_balls['runs_total'].sum()) if 'runs_total' in filtered_balls.columns else 0
total_wickets = int(filtered_balls['wicket_kind'].notna().sum()) if 'wicket_kind' in filtered_balls.columns else 0
avg_match_runs = int(total_runs / total_matches) if total_matches else 0

for col, val, label in zip(
    [k1, k2, k3, k4, k5],
    [f"{total_matches:,}", str(total_teams), f"{total_runs:,}", f"{total_wickets:,}", f"{avg_match_runs}"],
    ["Total Matches", "Teams", "Total Runs", "Wickets", "Avg Runs/Match"]
):
    col.markdown(f"""
    <div class='metric-card'>
        <h2>{val}</h2>
        <p>{label}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Team Analytics", "🎯 Batting Analytics",
    "🎳 Bowling Analytics", "📈 Trend Analysis", "🇵🇰 Pakistan Focus"
])


# ══════════════════════════════════════════════════════════════════════
# TAB 1: TEAM ANALYTICS
# ══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>📊 Team Win Analysis</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    # Win % bar chart
    with c1:
        if 'winner' in filtered_info.columns and 'team1' in filtered_info.columns:
            wins = filtered_info['winner'].value_counts().head(15).reset_index()
            wins.columns = ['Team', 'Wins']
            total_played = {}
            for t in wins['Team']:
                played = ((filtered_info['team1'] == t) | (filtered_info['team2'] == t)).sum()
                total_played[t] = played
            wins['Played'] = wins['Team'].map(total_played)
            wins['Win%'] = (wins['Wins'] / wins['Played'] * 100).round(1)
            wins = wins.sort_values('Win%', ascending=True)
            fig = px.bar(wins, x='Win%', y='Team', orientation='h',
                         color='Win%', color_continuous_scale='Blues',
                         text='Win%')
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(styled_fig(fig, "Win % by Team"), use_container_width=True)

    # Toss impact
    with c2:
        if 'toss_winner' in filtered_info.columns and 'winner' in filtered_info.columns:
            filtered_info['toss_won_match'] = filtered_info['toss_winner'] == filtered_info['winner']
            toss_impact = filtered_info['toss_won_match'].value_counts()
            fig = px.pie(
                values=toss_impact.values,
                names=["Toss Winner Lost", "Toss Winner Won"],
                color_discrete_sequence=['#ff6b6b', '#00d4ff'],
                hole=0.5
            )
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(styled_fig(fig, "Toss Impact on Match Result"), use_container_width=True)

    # Toss Decision
    c3, c4 = st.columns(2)
    with c3:
        if 'toss_decision' in filtered_info.columns:
            td = filtered_info['toss_decision'].value_counts().reset_index()
            td.columns = ['Decision', 'Count']
            fig = px.bar(td, x='Decision', y='Count',
                         color='Decision', color_discrete_sequence=['#00d4ff', '#ff9f43'],
                         text='Count')
            fig.update_traces(textposition='outside')
            st.plotly_chart(styled_fig(fig, "Toss Decisions: Bat vs Field"), use_container_width=True)

    # Result type
    with c4:
        if 'result' in filtered_info.columns:
            res = filtered_info['result'].value_counts().reset_index()
            res.columns = ['Result', 'Count']
            fig = px.pie(res, names='Result', values='Count',
                         color_discrete_sequence=COLORS, hole=0.4)
            st.plotly_chart(styled_fig(fig, "Match Result Types"), use_container_width=True)

    # Head to Head heatmap
    st.markdown("<div class='section-header'>🔥 Head-to-Head Wins Heatmap</div>", unsafe_allow_html=True)
    if 'winner' in filtered_info.columns and 'team1' in filtered_info.columns:
        top_teams = filtered_info['winner'].value_counts().head(10).index.tolist()
        h2h = pd.DataFrame(0, index=top_teams, columns=top_teams)
        for _, row in filtered_info.iterrows():
            t1, t2, w = row.get('team1'), row.get('team2'), row.get('winner')
            if t1 in top_teams and t2 in top_teams and pd.notna(w):
                if w in top_teams:
                    loser = t2 if w == t1 else t1
                    if loser in top_teams:
                        h2h.loc[w, loser] += 1
        fig = px.imshow(h2h, color_continuous_scale='Blues',
                        labels=dict(x="Lost To", y="Winner", color="Wins"))
        fig.update_layout(paper_bgcolor=PAPER, plot_bgcolor=BG,
                          font=dict(color="#c8d8f0"), template=TEMPLATE)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 2: BATTING ANALYTICS
# ══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>🏏 Top Run Scorers</div>", unsafe_allow_html=True)

    if 'batter' in filtered_balls.columns and 'runs_batter' in filtered_balls.columns:
        bat = filtered_balls.groupby('batter').agg(
            Runs=('runs_batter', 'sum'),
            Balls=('runs_batter', 'count'),
            Innings=('match_id', 'nunique')
        ).reset_index()
        bat['Strike_Rate'] = (bat['Runs'] / bat['Balls'] * 100).round(1)
        bat['Average'] = (bat['Runs'] / bat['Innings']).round(1)

        top_n = st.slider("Show Top N Batters", 5, 30, 15)
        top_bat = bat.nlargest(top_n, 'Runs')

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(top_bat.sort_values('Runs', ascending=True),
                         x='Runs', y='batter', orientation='h',
                         color='Runs', color_continuous_scale='Teal',
                         text='Runs')
            fig.update_traces(textposition='outside')
            st.plotly_chart(styled_fig(fig, f"Top {top_n} Run Scorers"), use_container_width=True)

        with c2:
            fig = px.scatter(top_bat, x='Strike_Rate', y='Average',
                             size='Runs', color='Runs',
                             hover_name='batter',
                             color_continuous_scale='Plasma',
                             size_max=40)
            fig.update_layout(paper_bgcolor=PAPER, plot_bgcolor=BG,
                               font=dict(color="#c8d8f0"), template=TEMPLATE,
                               title=dict(text="Strike Rate vs Average (bubble = total runs)",
                                          font=dict(size=13, color="#00d4ff")))
            st.plotly_chart(fig, use_container_width=True)

        # Milestones (50s, 100s estimation from innings avg)
        st.markdown("<div class='section-header'>🏅 Batter Performance Table</div>", unsafe_allow_html=True)
        display_cols = ['batter', 'Runs', 'Balls', 'Innings', 'Strike_Rate', 'Average']
        st.dataframe(
            top_bat[display_cols].rename(columns={'batter': 'Player'}).reset_index(drop=True),
            use_container_width=True,
            height=300
        )

    # Runs distribution by innings
    if 'inning' in filtered_balls.columns and 'runs_total' in filtered_balls.columns:
        st.markdown("<div class='section-header'>📊 Runs Distribution per Over</div>", unsafe_allow_html=True)
        over_runs = filtered_balls.groupby(['inning', 'over'])['runs_total'].mean().reset_index()
        over_runs.columns = ['Inning', 'Over', 'Avg_Runs']
        fig = px.line(over_runs, x='Over', y='Avg_Runs', color='Inning',
                      color_discrete_sequence=['#00d4ff', '#ff6b6b'],
                      markers=True)
        st.plotly_chart(styled_fig(fig, "Average Runs per Over (1st vs 2nd Innings)"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 3: BOWLING ANALYTICS
# ══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>🎳 Bowling Performance</div>", unsafe_allow_html=True)

    if 'bowler' in filtered_balls.columns:
        bowl = filtered_balls.groupby('bowler').agg(
            Wickets=('wicket_kind', lambda x: x.notna().sum()),
            Runs_Given=('runs_total', 'sum'),
            Balls_Bowled=('runs_total', 'count')
        ).reset_index()
        bowl['Economy'] = (bowl['Runs_Given'] / (bowl['Balls_Bowled'] / 6)).round(2)
        bowl['Bowling_Avg'] = (bowl['Runs_Given'] / bowl['Wickets'].replace(0, np.nan)).round(1)
        bowl = bowl[bowl['Wickets'] > 5]  # filter meaningful bowlers

        top_n_bowl = st.slider("Show Top N Bowlers", 5, 30, 15, key='bowl_slider')
        top_bowl = bowl.nlargest(top_n_bowl, 'Wickets')

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(top_bowl.sort_values('Wickets', ascending=True),
                         x='Wickets', y='bowler', orientation='h',
                         color='Wickets', color_continuous_scale='Reds',
                         text='Wickets')
            fig.update_traces(textposition='outside')
            st.plotly_chart(styled_fig(fig, f"Top {top_n_bowl} Wicket Takers"), use_container_width=True)

        with c2:
            fig = px.scatter(top_bowl, x='Economy', y='Bowling_Avg',
                             size='Wickets', hover_name='bowler',
                             color='Wickets', color_continuous_scale='Hot',
                             size_max=40)
            fig.update_layout(paper_bgcolor=PAPER, plot_bgcolor=BG,
                               font=dict(color="#c8d8f0"), template=TEMPLATE,
                               title=dict(text="Economy vs Bowling Avg (bubble = wickets)",
                                          font=dict(size=13, color="#00d4ff")))
            st.plotly_chart(fig, use_container_width=True)

        # Wicket types
        st.markdown("<div class='section-header'>🏏 Dismissal Types</div>", unsafe_allow_html=True)
        if 'wicket_kind' in filtered_balls.columns:
            dismissals = filtered_balls['wicket_kind'].value_counts().reset_index()
            dismissals.columns = ['Type', 'Count']
            dismissals = dismissals.dropna()
            fig = px.bar(dismissals, x='Type', y='Count',
                         color='Type', color_discrete_sequence=COLORS,
                         text='Count')
            fig.update_traces(textposition='outside')
            st.plotly_chart(styled_fig(fig, "Wicket Types Distribution"), use_container_width=True)

        st.markdown("<div class='section-header'>📋 Bowler Stats Table</div>", unsafe_allow_html=True)
        st.dataframe(
            top_bowl[['bowler', 'Wickets', 'Runs_Given', 'Economy', 'Bowling_Avg']]
            .rename(columns={'bowler': 'Bowler'}).reset_index(drop=True),
            use_container_width=True,
            height=300
        )


# ══════════════════════════════════════════════════════════════════════
# TAB 4: TREND ANALYSIS
# ══════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>📈 Yearly Match Trends</div>", unsafe_allow_html=True)

    if 'year' in filtered_info.columns:
        c1, c2 = st.columns(2)

        # Matches per year
        with c1:
            matches_yr = filtered_info.groupby('year').size().reset_index(name='Matches')
            fig = px.line(matches_yr, x='year', y='Matches',
                          markers=True, color_discrete_sequence=['#00d4ff'],
                          line_shape='spline')
            fig.update_traces(fill='tozeroy', fillcolor='rgba(0,212,255,0.08)')
            st.plotly_chart(styled_fig(fig, "Matches Played Per Year"), use_container_width=True)

        # Team wins per year
        with c2:
            if 'winner' in filtered_info.columns and selected_teams:
                wins_yr = filtered_info[filtered_info['winner'].isin(selected_teams)]
                wins_yr = wins_yr.groupby(['year', 'winner']).size().reset_index(name='Wins')
                fig = px.line(wins_yr, x='year', y='Wins', color='winner',
                              markers=True, line_shape='spline',
                              color_discrete_sequence=COLORS)
                st.plotly_chart(styled_fig(fig, "Team Wins Per Year"), use_container_width=True)

    # Avg score trend
    st.markdown("<div class='section-header'>📊 Average Team Score Trend</div>", unsafe_allow_html=True)
    if 'match_id' in filtered_balls.columns and 'year' in filtered_info.columns:
        merged = filtered_balls.merge(
            filtered_info[['match_id', 'year']].drop_duplicates(), on='match_id', how='left'
        )
        score_trend = merged.groupby(['match_id', 'year', 'inning'])['runs_total'].sum().reset_index()
        score_trend = score_trend.groupby(['year', 'inning'])['runs_total'].mean().reset_index()
        score_trend.columns = ['Year', 'Inning', 'Avg_Score']
        fig = px.line(score_trend, x='Year', y='Avg_Score', color='Inning',
                      markers=True, line_shape='spline',
                      color_discrete_sequence=['#00d4ff', '#ff6b6b'])
        fig.update_traces(fill='tozeroy')
        st.plotly_chart(styled_fig(fig, "Average Innings Score Over Years"), use_container_width=True)

    # Venue Analysis
    if 'venue' in filtered_info.columns:
        st.markdown("<div class='section-header'>🏟️ Top Venues by Matches Hosted</div>", unsafe_allow_html=True)
        venue_data = filtered_info['venue'].value_counts().head(15).reset_index()
        venue_data.columns = ['Venue', 'Matches']
        fig = px.bar(venue_data, x='Matches', y='Venue', orientation='h',
                     color='Matches', color_continuous_scale='Viridis', text='Matches')
        fig.update_traces(textposition='outside')
        st.plotly_chart(styled_fig(fig, "Most Active Venues"), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 5: PAKISTAN FOCUS
# ══════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("""
    <div style='text-align:center; padding: 10px 0 20px;'>
        <h2 style='color:#00d4ff;'>🇵🇰 Pakistan ODI Performance (2002–2023)</h2>
    </div>""", unsafe_allow_html=True)

    pak_matches = match_info[
        (match_info.get('team1', pd.Series('')) == 'Pakistan') |
        (match_info.get('team2', pd.Series('')) == 'Pakistan')
    ].copy()
    pak_matches = pak_matches[pak_matches['year'].between(year_range[0], year_range[1])]

    if len(pak_matches) == 0:
        st.warning("No Pakistan matches found in current filter. Please check team filters.")
    else:
        # KPIs
        pak_wins   = (pak_matches['winner'] == 'Pakistan').sum() if 'winner' in pak_matches.columns else 0
        pak_losses = len(pak_matches) - pak_wins
        pak_win_pct = round(pak_wins / len(pak_matches) * 100, 1) if len(pak_matches) else 0

        k1, k2, k3, k4 = st.columns(4)
        for col, v, l in zip([k1, k2, k3, k4],
                              [len(pak_matches), pak_wins, pak_losses, f"{pak_win_pct}%"],
                              ["Matches Played", "Wins", "Losses/NR", "Win Rate"]):
            col.markdown(f"<div class='metric-card'><h2>{v}</h2><p>{l}</p></div>",
                         unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        # Win/Loss per year
        with c1:
            if 'year' in pak_matches.columns and 'winner' in pak_matches.columns:
                pak_yr = pak_matches.copy()
                pak_yr['Result'] = pak_yr['winner'].apply(
                    lambda w: 'Win' if w == 'Pakistan' else 'Loss/NR'
                )
                pak_trend = pak_yr.groupby(['year', 'Result']).size().reset_index(name='Count')
                fig = px.bar(pak_trend, x='year', y='Count', color='Result',
                             color_discrete_map={'Win': '#00d4ff', 'Loss/NR': '#ff6b6b'},
                             barmode='group')
                st.plotly_chart(styled_fig(fig, "Pakistan Wins vs Losses Per Year"), use_container_width=True)

        # Opponents
        with c2:
            if 'team1' in pak_matches.columns:
                pak_matches['Opponent'] = pak_matches.apply(
                    lambda r: r['team2'] if r['team1'] == 'Pakistan' else r['team1'], axis=1
                )
                opp_stats = pak_matches.groupby('Opponent').agg(
                    Played=('match_id', 'count'),
                    Won=('winner', lambda x: (x == 'Pakistan').sum())
                ).reset_index()
                opp_stats['Win%'] = (opp_stats['Won'] / opp_stats['Played'] * 100).round(1)
                opp_stats = opp_stats[opp_stats['Played'] >= 3].sort_values('Win%', ascending=True)
                fig = px.bar(opp_stats, x='Win%', y='Opponent', orientation='h',
                             color='Win%', color_continuous_scale='RdYlGn',
                             text='Win%')
                fig.update_traces(texttemplate='%{text}%', textposition='outside')
                st.plotly_chart(styled_fig(fig, "Pakistan Win % vs Each Opponent"), use_container_width=True)

        # Pakistan top batters
        st.markdown("<div class='section-header'>🏏 Pakistan Top Batters</div>", unsafe_allow_html=True)
        pak_ids = set(pak_matches['match_id'].tolist()) if 'match_id' in pak_matches.columns else set()
        pak_balls = match_data[
            (match_data['match_id'].isin(pak_ids)) &
            (match_data.get('batting_team', pd.Series('')) == 'Pakistan')
        ] if 'batting_team' in match_data.columns else pd.DataFrame()

        if len(pak_balls) > 0 and 'batter' in pak_balls.columns:
            pak_bat = pak_balls.groupby('batter').agg(
                Runs=('runs_batter', 'sum'),
                Balls=('runs_batter', 'count')
            ).reset_index()
            pak_bat['SR'] = (pak_bat['Runs'] / pak_bat['Balls'] * 100).round(1)
            top_pak = pak_bat.nlargest(12, 'Runs')
            fig = px.bar(top_pak.sort_values('Runs', ascending=True),
                         x='Runs', y='batter', orientation='h',
                         color='Runs', color_continuous_scale='Blues',
                         text='Runs')
            fig.update_traces(textposition='outside')
            st.plotly_chart(styled_fig(fig, "Pakistan Top Run Scorers (2002–2023)"), use_container_width=True)

        # Pakistan top bowlers
        st.markdown("<div class='section-header'>🎳 Pakistan Top Bowlers</div>", unsafe_allow_html=True)
        pak_bowl_balls = match_data[
            (match_data['match_id'].isin(pak_ids)) &
            (match_data.get('bowling_team', pd.Series('')) == 'Pakistan')
        ] if 'bowling_team' in match_data.columns else pd.DataFrame()

        if len(pak_bowl_balls) > 0 and 'bowler' in pak_bowl_balls.columns:
            pak_bowl = pak_bowl_balls.groupby('bowler').agg(
                Wickets=('wicket_kind', lambda x: x.notna().sum()),
                Runs_Given=('runs_total', 'sum'),
                Balls=('runs_total', 'count')
            ).reset_index()
            pak_bowl['Economy'] = (pak_bowl['Runs_Given'] / (pak_bowl['Balls'] / 6)).round(2)
            pak_bowl = pak_bowl[pak_bowl['Wickets'] > 3]
            top_pak_bowl = pak_bowl.nlargest(12, 'Wickets')
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(top_pak_bowl.sort_values('Wickets', ascending=True),
                             x='Wickets', y='bowler', orientation='h',
                             color='Wickets', color_continuous_scale='Reds', text='Wickets')
                fig.update_traces(textposition='outside')
                st.plotly_chart(styled_fig(fig, "Pakistan Top Wicket Takers"), use_container_width=True)
            with c2:
                fig = px.scatter(top_pak_bowl, x='Economy', y='Wickets',
                                 size='Wickets', hover_name='bowler',
                                 color='Economy', color_continuous_scale='RdYlGn_r',
                                 size_max=35)
                fig.update_layout(paper_bgcolor=PAPER, plot_bgcolor=BG,
                                   font=dict(color="#c8d8f0"), template=TEMPLATE,
                                   title=dict(text="Economy vs Wickets",
                                              font=dict(size=13, color="#00d4ff")))
                st.plotly_chart(fig, use_container_width=True)

# ─── Footer ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; padding:30px 0 10px; color:#334466; font-size:0.8rem;'>
    ODI Cricket Analytics Dashboard • Data: Cricsheet.org via Kaggle • Built with Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
