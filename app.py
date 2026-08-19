"""
IGCSE International Mathematics — Topic Revision Explorer
Prototype Streamlit dashboard.

Expects a real data file at ./tagged_questions.csv with columns:
    filename, year, session_code, paper_type, question_number,
    question_text, marks, topic
(paper_type in {"non_calculator", "calculator"}, session_code in {"m","s","w"})

"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

from config.topic_list import TOPIC_LIST

st.set_page_config(page_title="IGCSE Topic Explorer", layout="wide")

DATA_PATH = Path("tagged_questions.csv")




SESSION_ORDER = {"m": 1, "s": 2, "w": 3}  # Mar/May, May/Jun, Oct/Nov — chronological within a year
SESSION_NAME = {"m": "Mar/May", "s": "May/Jun", "w": "Oct/Nov"}


@st.cache_data
def load_data() -> tuple[pd.DataFrame, bool]:
    return pd.read_csv(DATA_PATH), False


df, using_demo = load_data()

st.title("IGCSE International Mathematics — Exam Topic Explorer")

tab1, tab2 = st.tabs(["📊 Topic Heatmap", "🔍 Find Questions by Topic"])

# ---------------------------------------------------------------- TAB 1 ----
with tab1:
    st.subheader("Share of marks by topic and year")

    scope = st.radio("Paper type", ["Combined", "Non-calculator", "Calculator"], horizontal=True)
    if scope == "Non-calculator":
        scoped_df = df[df["paper_type"] == "non_calculator"]
    elif scope == "Calculator":
        scoped_df = df[df["paper_type"] == "calculator"]
    else:
        scoped_df = df

    # proportion = topic's marks / total marks that year, within the selected scope
    year_totals = scoped_df.groupby("year")["marks"].sum().rename("year_total_marks")
    topic_year_marks = scoped_df.groupby(["topic", "year"])["marks"].sum().reset_index()
    topic_year_marks = topic_year_marks.merge(year_totals, on="year")
    topic_year_marks["proportion"] = topic_year_marks["marks"] / topic_year_marks["year_total_marks"]

    heat = topic_year_marks.pivot(index="topic", columns="year", values="proportion").fillna(0)
    heat = heat.reindex(TOPIC_LIST)  # keep a stable, syllabus-order row axis rather than alphabetical

    fig = px.imshow(
        heat,
        labels=dict(x="Year", y="Topic", color="Share of marks"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig.update_layout(height=650, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Prototype note: cells currently show **raw** yearly proportions. "
        "The full pipeline will replace these with bootstrap-smoothed estimates "
        "and a per-topic stability score, so a topic's *displayed* share may "
        "still be noisy on a small per-year sample."
    )

# ---------------------------------------------------------------- TAB 2 ----
with tab2:
    st.subheader("Browse past questions by topic")

    col1, col2 = st.columns([2, 1])
    with col1:
        chosen_topic = st.selectbox("Choose a topic", sorted(df["topic"].unique()))
    with col2:
        type_filter = st.multiselect(
            "Paper type",
            ["non_calculator", "calculator"],
            default=["non_calculator", "calculator"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

    filtered = df[(df["topic"] == chosen_topic) & (df["paper_type"].isin(type_filter))].copy()
    filtered["session_order"] = filtered["session_code"].map(SESSION_ORDER)
    filtered = filtered.sort_values(["year", "session_order"], ascending=[False, False])

    st.write(f"**{len(filtered)}** questions found, most recent first")

    for _, row in filtered.iterrows():
        with st.container(border=True):
            session_label = SESSION_NAME.get(row["session_code"], row["session_code"])
            st.markdown(
                f"**{row['year']} {session_label} · "
                f"{row['paper_type'].replace('_', ' ').title()} · "
                f"Q{row['question_number']} · [{row['marks']} marks]**"
            )
            st.write(row["question_text"])
            st.caption(row["filename"])