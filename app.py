import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(
    page_title="Funnel Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)
st.markdown("""
<style>

.main{
    background-color:#F8F9FA;
}

div[data-testid="metric-container"]{
    background:white;
    border-radius:12px;
    padding:15px;
    box-shadow:0px 2px 8px rgba(0,0,0,0.1);
    border-left:5px solid #4CAF50;
}

h1,h2,h3{
    color:#1E3A8A;
}

.stDataFrame{
    border-radius:10px;
}

</style>
""", unsafe_allow_html=True)

st.title("📊 User Funnel Analysis Dashboard")

st.caption(
    "Interactive Funnel Analytics | Streamlit + Plotly"
)

st.markdown("---")

st.markdown("---")

st.caption(
"""
Created by **Madhan**

Assessment Dashboard using
Python • Pandas • Streamlit • Plotly
"""
)


st.title("📊 User Funnel Analysis Dashboard")
st.markdown("---")

# ------------------------------
# LOAD DATA
# ------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("data/funnel_events_sample.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

df = load_data()

# ------------------------------
# SIDEBAR
# ------------------------------
st.sidebar.header("Filters")

start_date = st.sidebar.date_input(
    "Start Date",
    df["timestamp"].min().date()
)

end_date = st.sidebar.date_input(
    "End Date",
    df["timestamp"].max().date()
)

filtered = df[
    (df["timestamp"].dt.date >= start_date) &
    (df["timestamp"].dt.date <= end_date)
]

steps = sorted(filtered["step"].unique())

selected_steps = st.sidebar.multiselect(
    "Select Funnel Steps",
    steps,
    default=steps
)

filtered = filtered[filtered["step"].isin(selected_steps)]

# ------------------------------
# KPI CALCULATIONS
# ------------------------------
total_users = filtered["user_id"].nunique()

completed_users = filtered[
    filtered["step"] == filtered["step"].max()
]["user_id"].nunique()

conversion_rate = (
    completed_users / total_users * 100
    if total_users else 0
)

duplicate_events = filtered.duplicated(
    subset=["user_id", "step"]
).sum()

# ------------------------------
# KPI CARDS
# ------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "👥 Total Users",
    f"{total_users:,}"
)

col2.metric(
    "✅ Completed Users",
    f"{completed_users:,}"
)

col3.metric(
    "📈 Conversion Rate",
    f"{conversion_rate:.2f}%"
)

col4.metric(
    "⚠ Duplicate Events",
    duplicate_events
)

st.markdown("---")
# ==========================================
# FUNNEL ORDER
# ==========================================

FUNNEL_ORDER = [
    "Landing",
    "Signup",
    "Verify",
    "Purchase"
]

filtered["step"] = pd.Categorical(
    filtered["step"],
    categories=FUNNEL_ORDER,
    ordered=True
)

# Remove duplicate user events
clean_df = (
    filtered
    .sort_values("timestamp")
    .drop_duplicates(subset=["user_id", "step"])
)
# Count unique users at each funnel stage
summary = (
    clean_df.groupby("step")["user_id"]
    .nunique()
    .reset_index(name="Users")
)

# Rename column for charts
summary.rename(columns={"step": "Stage"}, inplace=True)

# Keep funnel order
summary["Stage"] = pd.Categorical(
    summary["Stage"],
    categories=FUNNEL_ORDER,
    ordered=True
)

summary = summary.sort_values("Stage").reset_index(drop=True)

# Calculate Drop Off
summary["Drop Off"] = summary["Users"].shift(1) - summary["Users"]
summary["Drop Off"] = summary["Drop Off"].fillna(0).astype(int)

import plotly.graph_objects as go

st.subheader("📊 Funnel Visualization")

funnel_fig = go.Figure(go.Funnel(
    y=summary["Stage"],
    x=summary["Users"],
    textinfo="value+percent initial"
))

funnel_fig.update_layout(height=500)

st.plotly_chart(funnel_fig, use_container_width=True)

st.subheader("📈 Users at Each Stage")

fig_bar = px.bar(
    summary,
    x="Stage",
    y="Users",
    color="Users",
    text="Users",
    title="Stage-wise User Count"
)

fig_bar.update_traces(textposition="outside")

st.plotly_chart(fig_bar, use_container_width=True)

st.subheader("📉 Drop-off Analysis")

drop_chart = px.bar(
    summary.iloc[1:],
    x="Stage",
    y="Drop Off",
    color="Drop Off",
    text="Drop Off",
    title="Users Lost at Each Stage"
)

drop_chart.update_traces(textposition="outside")

st.plotly_chart(drop_chart, use_container_width=True)

completed = summary.iloc[-1]["Users"]
dropped = summary.iloc[0]["Users"] - completed

pie = px.pie(
    values=[completed, dropped],
    names=["Completed", "Dropped"],
    title="Completed vs Dropped Users"
)

st.plotly_chart(pie, use_container_width=True)

st.subheader("📊 Stage Conversion Rate")

conversion_chart = px.bar(
    summary.iloc[1:],
    x="Stage",
    y="Conversion %",
    text="Conversion %",
    color="Conversion %",
    title="Conversion Rate Between Stages"
)

conversion_chart.update_traces(textposition="outside")

st.plotly_chart(conversion_chart, use_container_width=True)

st.subheader("📅 User Activity Timeline")

timeline = (
    clean_df
    .groupby(clean_df["timestamp"].dt.date)
    .size()
    .reset_index(name="Events")
)

timeline_chart = px.line(
    timeline,
    x="timestamp",
    y="Events",
    markers=True,
    title="Daily User Activity"
)

st.plotly_chart(timeline_chart, use_container_width=True)


# ==========================================
# DATA AGGREGATION
# ==========================================

stage_counts = (
    clean_df.groupby("step")["user_id"]
    .nunique()
    .reindex(FUNNEL_ORDER)
    .fillna(0)
    .astype(int)
)

summary = pd.DataFrame({
    "Stage": stage_counts.index,
    "Users": stage_counts.values
})

# ==========================================
# STAGE TO STAGE CONVERSION
# ==========================================

conversion = [100]

for i in range(1, len(stage_counts)):
    previous = stage_counts.iloc[i-1]
    current = stage_counts.iloc[i]

    if previous == 0:
        conversion.append(0)
    else:
        conversion.append(round(current / previous * 100, 2))

summary["Conversion %"] = conversion

# ==========================================
# DROP OFF
# ==========================================

drop_users = [0]

for i in range(1, len(stage_counts)):
    lost = stage_counts.iloc[i-1] - stage_counts.iloc[i]
    drop_users.append(max(lost, 0))

summary["Drop Off"] = drop_users

drop_percent = [0]

for i in range(1, len(stage_counts)):
    previous = stage_counts.iloc[i-1]

    if previous == 0:
        drop_percent.append(0)
    else:
        drop_percent.append(
            round(drop_users[i] / previous * 100, 2)
        )

summary["Drop %"] = drop_percent

# ==========================================
# BIGGEST DROP OFF
# ==========================================

worst_index = summary["Drop Off"].idxmax()

worst_stage = summary.loc[worst_index, "Stage"]
worst_loss = summary.loc[worst_index, "Drop Off"]
worst_percent = summary.loc[worst_index, "Drop %"]

# ==========================================
# DISPLAY
# ==========================================

st.subheader("📊 Funnel Summary")

st.dataframe(
    summary,
    use_container_width=True
)

st.error(
    f"""
⚠ Biggest Drop-off Stage

Stage : {worst_stage}

Users Lost : {worst_loss}

Drop-off : {worst_percent}%
"""
)
# ------------------------------
# USER COUNTS BY STEP
# ------------------------------
stage_counts = (
    filtered.groupby("step")["user_id"]
    .nunique()
    .reset_index(name="Users")
)

fig = px.bar(
    stage_counts,
    x="step",
    y="Users",
    text="Users",
    color="Users",
    title="Users at Each Funnel Stage"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("---")
st.subheader("⏱ Average Time Between Stages")

# Keep first occurrence of each step per user
time_df = (
    clean_df
    .sort_values(["user_id", "timestamp"])
)

pivot = (
    time_df
    .pivot(index="user_id",
           columns="step",
           values="timestamp")
)

time_summary = []

for i in range(len(FUNNEL_ORDER)-1):

    start = FUNNEL_ORDER[i]
    end = FUNNEL_ORDER[i+1]

    if start in pivot.columns and end in pivot.columns:

        diff = (
            pivot[end] - pivot[start]
        ).dropna()

        avg_minutes = diff.dt.total_seconds().mean()/60

        time_summary.append({
            "From": start,
            "To": end,
            "Average Minutes":
                round(avg_minutes,2)
        })

time_table = pd.DataFrame(time_summary)

st.dataframe(
    time_table,
    use_container_width=True
)

fig_time = px.bar(
    time_table,
    x="From",
    y="Average Minutes",
    color="Average Minutes",
    text="Average Minutes",
    title="Average Time Between Stages"
)

st.plotly_chart(fig_time, use_container_width=True)

st.markdown("---")
st.subheader("👥 Segment Comparison")

clean_df["Segment"] = clean_df["user_id"].apply(
    lambda x: "Segment A"
    if int(str(x)[-1]) % 2 == 0
    else "Segment B"
)

segment_result = []

for segment in clean_df["Segment"].unique():

    users = clean_df[
        clean_df["Segment"]==segment
    ]

    total = users["user_id"].nunique()

    completed = users[
        users["step"]=="Purchase"
    ]["user_id"].nunique()

    rate = completed/total*100

    segment_result.append({
        "Segment":segment,
        "Users":total,
        "Conversion":round(rate,2)
    })

segment_df = pd.DataFrame(segment_result)

st.dataframe(segment_df)

segment_chart = px.bar(
    segment_df,
    x="Segment",
    y="Conversion",
    color="Segment",
    text="Conversion",
    title="Conversion Rate by Segment"
)

st.plotly_chart(segment_chart,
                use_container_width=True)

st.markdown("---")
st.subheader("🧹 Data Quality Report")

missing = df.isnull().sum().sum()

duplicates = df.duplicated().sum()

skipped_users = 0

for user in clean_df["user_id"].unique():

    stages = clean_df[
        clean_df["user_id"]==user
    ]["step"].tolist()

    expected = [
        s for s in FUNNEL_ORDER
        if s in stages
    ]

    if stages != expected:
        skipped_users += 1

col1,col2,col3 = st.columns(3)

col1.metric(
    "Missing Values",
    missing
)

col2.metric(
    "Duplicate Rows",
    duplicates
)

col3.metric(
    "Skipped Users",
    skipped_users
)

st.markdown("---")

st.error(
f"""
🚩 Biggest Funnel Drop-off

Stage : {worst_stage}

Users Lost : {worst_loss}

Drop Percentage : {worst_percent}%

Priority: HIGH
"""
)

st.subheader("💡 Recommendation")

recommendation = f"""
The highest drop-off occurs at the **{worst_stage}** stage.

This indicates many users leave before completing the next step.

Recommended improvements:

• Simplify this stage.
• Reduce unnecessary form fields.
• Improve page speed.
• Add progress indicators.
• Test the flow with A/B experiments.
"""

st.info(recommendation)

st.markdown("---")

csv = clean_df.to_csv(index=False)

st.download_button(
    label="📥 Download Clean Dataset",
    data=csv,
    file_name="processed_funnel.csv",
    mime="text/csv"
)


# ------------------------------
# DATA PREVIEW
# ------------------------------
st.subheader("Dataset Preview")

st.dataframe(
    filtered,
    use_container_width=True
)