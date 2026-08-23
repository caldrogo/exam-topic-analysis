import re
from pathlib import Path

import json
import pandas as pd
import numpy as np

FILENAME_PATTERN = re.compile(
    r"^(?P<syllabus>\d{4})_"
    r"(?P<session>[a-z])(?P<year>\d{2})_"
    r"qp_"
    r"(?P<paper_number>\d)(?P<variant>\d)$"
)

SESSION_MAP = {"m": "Mar/May", "s": "May/Jun", "w": "Oct/Nov"}
PAPER_TYPE_MAP = {"2": "non_calculator", "4": "calculator", "6": "investigation"}

def parse_filename(filename: str) -> dict:
    stem = Path(filename).stem  # strips .json
    match = FILENAME_PATTERN.match(stem)
    if not match:
        raise ValueError(f"Filename doesn't match expected pattern: {filename}")

    g = match.groupdict()
    paper_type = PAPER_TYPE_MAP.get(g["paper_number"])
    if paper_type is None:
        raise ValueError(f"Unrecognized paper number '{g['paper_number']}' in {filename}")

    return {
        "filename": filename,
        "syllabus": g["syllabus"],
        "session_code": g["session"],
        "session_name": SESSION_MAP.get(g["session"], "unknown"),
        "year": 2000 + int(g["year"]),
        "paper_number": g["paper_number"],
        "paper_type": paper_type,
        "variant": g["variant"],
    }

def build_dataset(papers_dir: str) -> pd.DataFrame:
    rows = []
    papers_path = Path(papers_dir)

    for json_file in sorted(papers_path.glob("*.json")):
        try:
            meta = parse_filename(json_file.name)
        except ValueError as e:
            print(f"SKIPPING (parse error): {e}")
            continue

        with open(json_file, "r", encoding="utf-8") as f:
            paper_data = json.load(f)

        for q in paper_data["questions"]:
            marks_str = q["marks_available"].strip("[]")
            marks = int(marks_str) if marks_str.isdigit() else None
            if marks is None:
                print(f"WARNING: unparseable marks in {json_file.name}, "
                      f"question {q['question_number']}: {q['marks_available']}")

            rows.append({
                **meta,
                "question_number": q["question_number"],
                "question_text": q["question_text"],
                "marks": marks,
                'topic' : q['topic']
            })

    df = pd.DataFrame(rows)
    return df

def build_hand_coding_sample(
    df: pd.DataFrame,
    target_fraction: float = 0.05,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Draws a stratified, question-level random sample for manual topic
    validation. Strata: paper_type (non_calculator / calculator) x
    time_period (early / late, split at median year).
    """
    df = df.copy()

    # --- define time_period stratum: split at median year ---
    median_year = df["year"].median()
    df["time_period"] = np.where(df["year"] <= median_year, "early", "late")

    df["stratum"] = df["paper_type"] + " | " + df["time_period"]

    total_n = len(df)
    target_n = round(total_n * target_fraction)

    print(f"Total questions in dataset: {total_n}")
    print(f"Target sample size (~{target_fraction:.0%}): {target_n}")
    print(f"\nStratum sizes (population):")
    print(df["stratum"].value_counts())

    rng = np.random.default_rng(random_seed)
    sampled_frames = []

    for stratum, group in df.groupby("stratum"):
        stratum_share = len(group) / total_n
        stratum_n = round(stratum_share * target_n)
        stratum_n = min(stratum_n, len(group))  # safety guard

        sampled_idx = rng.choice(group.index, size=stratum_n, replace=False)
        sampled_frames.append(df.loc[sampled_idx])

    sample_df = pd.concat(sampled_frames).drop(columns=['topic']).sort_index()

    print(f"\nActual sample size drawn: {len(sample_df)}")
    print(f"\nSample composition by stratum:")
    print(sample_df["stratum"].value_counts())

    return sample_df

def build(first_run: bool = False, target_fraction=0.01):

    df = build_dataset("data/tagged_papers_latest_json")

    print(f"Total questions: {len(df)}")
    print(f"Total papers: {df['filename'].nunique()}")
    print(f"\nPapers per year:\n{df.groupby('year')['filename'].nunique()}")
    print(f"\nPapers per (year, paper_type):\n{df.groupby(['year','paper_type'])['filename'].nunique()}")
    print(f"\nDistinct session_code/variant combos per year:\n{df.groupby('year')[['session_code','variant']].nunique()}")

    df.to_csv("data/dataset_full_latest.csv", index=False)
    print(f"All questions tagged by LLM saved to data/dataset_full_latest.csv")

    if first_run:
        sample_df = build_hand_coding_sample(df, target_fraction=target_fraction, random_seed=42)
        sample_df.to_csv("data/dataset_sample.csv", index=False)
        print(f"Sample questions to be tagged by human saved to data/dataset_sample.csv")
        print(f"Tag these by introducing a new column 'human_topic")