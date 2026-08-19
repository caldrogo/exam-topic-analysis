"""
IGCSE International Mathematics — Topic Revision Explorer
Prototype Streamlit dashboard.

Expects a real data file at ./tagged_questions.csv with columns:
    filename, year, session_code, paper_type, question_number,
    question_text, marks, topic
(paper_type in {"non_calculator", "calculator"}, session_code in {"m","s","w"})

If that file isn't present, the app falls back to synthetic demo data so the
UI can be built/demoed before the tagging pipeline (Phase 0-1) is finished.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

from topic_list import TOPIC_LIST

st.set_page_config(page_title="IGCSE Topic Explorer", layout="wide")

DATA_PATH = Path("tagged_questions.csv")



SESSION_ORDER = {"m": 1, "s": 2, "w": 3}  # Mar/May, May/Jun, Oct/Nov — chronological within a year
SESSION_NAME = {"m": "Mar/May", "s": "May/Jun", "w": "Oct/Nov"}


def generate_demo_data(n_years: int = 10, seed: int = 42) -> pd.DataFrame:
    """Synthetic stand-in matching the real pipeline's output schema."""
    rng = np.random.default_rng(seed)
    years = list(range(2015, 2015 + n_years))
    paper_types = {"2": "non_calculator", "4": "calculator"}
    base_weights = rng.dirichlet(np.ones(len(TOPIC_LIST)) * 3)

    rows, qid = [], 0
    for year in years:
        year_weights = rng.dirichlet(base_weights * 20)  # yearly wobble around the base distribution
        for session in ["m", "s", "w"]:
            for pnum, ptype in paper_types.items():
                n_q = rng.integers(25, 31)
                for qn in range(1, n_q + 1):
                    topic = rng.choice(TOPIC_LIST, p=year_weights)
                    marks = int(rng.choice([1, 2, 3, 4, 5, 6], p=[.15, .25, .25, .15, .1, .1]))
                    rows.append({
                        "filename": f"0607_{session}{str(year)[2:]}_qp_{pnum}2.json",
                        "year": year,
                        "session_code": session,
                        "paper_type": ptype,
                        "question_number": str(qn),
                        "question_text": f"[Demo question] Item {qid} assessing {topic.lower()}.",
                        "marks": marks,
                        "topic": topic,
                    })
                    qid += 1
    return pd.DataFrame(rows)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, bool]:
    if DATA_PATH.exists():
        return pd.read_csv(DATA_PATH), False
    return generate_demo_data(), True


df, using_demo = load_data()

st.title("IGCSE International Mathematics — Exam Topic Explorer")
if using_demo:
    st.warning(
        "Showing SYNTHETIC demo data — drop a real `tagged_questions.csv` "
        "next to this app to switch to actual past-paper data.",
        icon="⚠️",
    )

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