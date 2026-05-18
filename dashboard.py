# ---------------- IMPORTS ----------------

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import anthropic
import json


# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="Performance Dashboard",
    layout="wide"
)


# ---------------- API SETUP ----------------

api_key = os.getenv("ANTHROPIC_API_KEY")

if api_key:
    client = anthropic.Anthropic(api_key=api_key)
else:
    client = None


# ---------------- UI ----------------

st.title("📊 Performance Dashboard")

st.caption(
    "Upload your CSV data to see charts and insights."
)


# ---------------- SAMPLE CSV ----------------

def make_sample_csv():

    dates = pd.date_range(
        "2026-04-01",
        periods=30
    )

    rows = []

    for i, d in enumerate(dates):

        rows.append({
            "date": d,
            "platform": "Instagram",
            "reach": np.random.randint(800, 2200),
            "engagement": round(
                np.random.uniform(3.5, 7.2),
                2
            ),
            "followers": 1200 + i * 5,
            "clicks": np.random.randint(20, 90)
        })

        rows.append({
            "date": d,
            "platform": "Facebook",
            "reach": np.random.randint(300, 900),
            "engagement": round(
                np.random.uniform(1.5, 4.0),
                2
            ),
            "followers": 800 + i * 2,
            "clicks": np.random.randint(5, 40)
        })

    return pd.DataFrame(rows).to_csv(index=False)


st.download_button(
    "📥 Download Sample CSV",
    data=make_sample_csv(),
    file_name="sample_performance.csv",
    mime="text/csv"
)


# ---------------- FILE UPLOAD ----------------

uploaded = st.file_uploader(
    "Upload performance CSV",
    type=["csv"]
)

if uploaded is None:

    st.info(
        "👆 Upload a CSV file to begin."
    )

    st.stop()


# ---------------- READ CSV SAFELY ----------------

try:

    df = pd.read_csv(uploaded)

except pd.errors.EmptyDataError:

    st.error(
        "The uploaded CSV file is empty."
    )

    st.stop()

except Exception:

    st.error(
        "Could not read your CSV file. Please upload a valid CSV."
    )

    st.stop()


# ---------------- EMPTY DATA CHECK ----------------

if df.empty:

    st.error(
        "The uploaded CSV has no data rows."
    )

    st.stop()


# ---------------- CLEAN COLUMN NAMES ----------------

df.columns = (
    df.columns
    .str.lower()
    .str.strip()
)


# ---------------- REQUIRED COLUMN CHECK ----------------

REQUIRED_COLUMNS = [
    "date",
    "platform",
    "reach",
    "engagement",
    "followers",
    "clicks"
]

missing = [
    col for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing:

    st.error(
        f"Your CSV is missing these columns: {', '.join(missing)}"
    )

    st.info(
        "Required columns: date, platform, reach, engagement, followers, clicks"
    )

    st.stop()


# ---------------- HANDLE MISSING VALUES ----------------

df["reach"] = df["reach"].fillna(0)

df["engagement"] = df["engagement"].fillna(0.0)

df["followers"] = df["followers"].fillna(0)

df["clicks"] = df["clicks"].fillna(0)


# ---------------- DATE CLEANING ----------------

df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce"
)

bad_dates = df["date"].isna().sum()

if bad_dates > 0:

    st.warning(
        f"{bad_dates} invalid date rows were removed."
    )

    df = df.dropna(subset=["date"])


if df.empty:

    st.error(
        "No valid data remaining after cleaning dates."
    )

    st.stop()


# ---------------- DATE FILTER ----------------

min_date = df["date"].min().date()

max_date = df["date"].max().date()

date_range = st.date_input(
    "Select Date Range",
    value=(min_date, max_date)
)

if len(date_range) == 2:

    start_date, end_date = date_range

    filtered_df = df[
        (df["date"] >= pd.Timestamp(start_date)) &
        (df["date"] <= pd.Timestamp(end_date))
    ]

else:

    filtered_df = df


# ---------------- PLATFORM FILTER ----------------

platforms = filtered_df[
    "platform"
].unique().tolist()

selected_platforms = st.multiselect(
    "Filter Platform",
    platforms,
    default=platforms
)

filtered_df = filtered_df[
    filtered_df["platform"].isin(selected_platforms)
]


# ---------------- EMPTY FILTER CHECK ----------------

if filtered_df.empty:

    st.warning(
        "No data available for selected filters."
    )

    st.stop()


# ---------------- SAFE GROWTH FUNCTION ----------------

def safe_growth_pct(start, end):

    if start == 0:
        return 0.0

    return round(
        ((end - start) / start) * 100,
        2
    )


# ---------------- KPI METRICS ----------------

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Total Reach",
        f"{filtered_df['reach'].sum():,}"
    )

with col2:

    avg_eng = filtered_df[
        "engagement"
    ].mean()

    st.metric(
        "Avg Engagement",
        f"{avg_eng:.2f}%"
    )

with col3:

    best_day = filtered_df.loc[
        filtered_df["reach"].idxmax(),
        "date"
    ]

    st.metric(
        "Best Day",
        str(best_day.date())
    )

with col4:

    top_platform = filtered_df.groupby(
        "platform"
    )["reach"].sum().idxmax()

    st.metric(
        "Top Platform",
        top_platform
    )


# ---------------- CHARTS ----------------

st.subheader("📊 Reach by Platform")

platform_data = filtered_df.groupby(
    "platform"
)["reach"].sum().reset_index()

fig_bar = px.bar(
    platform_data,
    x="platform",
    y="reach",
    color="platform",
    title="Total Reach by Platform"
)

st.plotly_chart(
    fig_bar,
    width="stretch"
)


st.subheader("📈 Engagement Over Time")

engagement_data = filtered_df.groupby(
    "date"
)["engagement"].mean().reset_index()

fig_line = px.line(
    engagement_data,
    x="date",
    y="engagement",
    title="Engagement Over Time"
)

st.plotly_chart(
    fig_line,
    width="stretch"
)


# ---------------- SUMMARY ----------------

def summarise_data(df):

    growth = safe_growth_pct(
        df["followers"].iloc[0],
        df["followers"].iloc[-1]
    )

    return f"""
Performance Summary

Total Reach:
{df['reach'].sum():,}

Average Engagement:
{df['engagement'].mean():.2f}%

Total Clicks:
{df['clicks'].sum():,}

Follower Growth:
{growth}%

Best Platform:
{df.groupby('platform')['reach'].sum().idxmax()}
"""


# ---------------- AI INSIGHTS ----------------

def get_ai_insights(summary_text):

    fallback = """
1. Engagement is steady.
2. Instagram performs strongest.
3. Consider increasing click-focused content.
"""

    if client is None:

        return fallback

    try:

        response = client.messages.create(
            model="claude-opus-4-1",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": f"""
Give exactly 3 simple marketing insights.

{summary_text}
"""
                }
            ]
        )

        return response.content[0].text

    except Exception:

        return """
1. AI service is temporarily unavailable.
2. Your dashboard data loaded successfully.
3. Please try generating insights again later.
"""


# ---------------- AI OUTPUT ----------------

st.divider()

st.subheader("🤖 AI Insights")

st.caption(
    "Generate AI insights from your uploaded performance data."
)

if st.button("Generate AI Insights"):

    with st.spinner("Generating insights..."):

        summary = summarise_data(filtered_df)

        insights = get_ai_insights(summary)

        st.session_state["insights"] = insights

    for line in insights.split("\n"):

        if line.strip():

            st.info(line.strip())


# ---------------- DOWNLOAD INSIGHTS ----------------

if st.session_state.get("insights"):

    st.download_button(
        "⬇ Download Insights",
        data=st.session_state["insights"],
        file_name="ai_insights.txt",
        mime="text/plain"
    )


# ---------------- EXPORT FOR MODULE 4 ----------------

def export_for_report(
    filtered_df,
    start_date,
    end_date
):

    summary = {

        "business_name":
        os.path.splitext(uploaded.name)[0],

        "period": {

            "start": str(start_date),

            "end": str(end_date)
        },

        "platforms": {}
    }

    for platform in filtered_df[
        "platform"
    ].unique():

        pdf = filtered_df[
            filtered_df["platform"] == platform
        ]

        growth = safe_growth_pct(
            pdf["followers"].iloc[0],
            pdf["followers"].iloc[-1]
        )

        summary["platforms"][platform] = {

            "total_reach": int(
                pdf["reach"].sum()
            ),

            "avg_engagement": round(
                float(pdf["engagement"].mean()),
                2
            ),

            "total_clicks": int(
                pdf["clicks"].sum()
            ),

            "follower_growth_pct": growth,

            "best_day": str(
                pdf.loc[
                    pdf["reach"].idxmax(),
                    "date"
                ].date()
            )
        }

    st.session_state.performance_data = summary

    return summary

# ---------------- EXPORT BUTTON ----------------

st.divider()

st.subheader(
    "📤 Export for Module 4"
)

st.caption(
    "Export filtered KPI data for the AI Report Generator."
)

if st.button(
    "📤 Export for Report Generator (Module 4)"
):

    report_data = export_for_report(
        filtered_df,
        start_date,
        end_date
    )

    st.success(
        "✅ Performance data exported successfully."
    )

    st.code(
        json.dumps(report_data, indent=2),
        language="json"
    )
