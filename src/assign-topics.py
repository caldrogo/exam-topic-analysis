import time
import os
from tqdm import tqdm
import pandas as pd
from pydantic import BaseModel
from enum import Enum
from typing import List
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

from topic_list import TOPIC_LIST

SYSTEM_PROMPT = f"""You are tagging IGCSE International Mathematics (0607) exam
questions with a single best-fit topic label.

You must choose exactly one topic from this fixed list — use these exact
strings, with no variation in spelling, capitalization, or phrasing:
{TOPIC_LIST}

Rules:
- Choose the topic that best represents the PRIMARY mathematical skill
  being assessed, even if the question touches on more than one area.
- Use the mark allocation as a secondary signal: higher-mark questions
  often span more of a topic's depth; lower-mark questions are often
  narrower/more atomic.
- If genuinely torn between two topics, choose the one that a teacher
  would file this question under when building a topic-based revision
  worksheet — this is a REVISION-PRIORITY tool, so prioritize the framing
  a student would recognize.
- You will be given ALL questions from one exam paper at once. Return one
  tag per question, and echo back the exact question_number given for
  each — do not renumber, merge, or omit any question.
- Respond only in the specified JSON schema. Do not include commentary,
  explanation, or any text outside the JSON object.
"""

TopicEnum = Enum("TopicEnum", {t.replace(" ", "_").replace("/", "_"): t for t in TOPIC_LIST})

class QuestionTag(BaseModel):
    question_number: str  # echoed back — never trust response order
    topic: TopicEnum
    confidence: str  # "high" / "medium" / "low"

class PaperTags(BaseModel):
    tags: List[QuestionTag]


def build_paper_prompt(paper_df: pd.DataFrame) -> str:
    lines = ["Tag every question below. Return one entry per question, "
             "using the exact question_number given.\n"]
    for _, row in paper_df.iterrows():
        lines.append(
            f"question_number: {row['question_number']}\n"
            f"marks: {row['marks']}\n"
            f"text: {row['question_text']}\n"
        )
    return "\n".join(lines)


def tag_paper(paper_df: pd.DataFrame) -> list[dict]:
    prompt = build_paper_prompt(paper_df)
    n_questions = len(paper_df)

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            max_output_tokens=max(2000, n_questions * 100),  # scale with paper length
            response_mime_type="application/json",
            response_schema=PaperTags,
        ),
    )

    if response.parsed is None:
        finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
        raise ValueError(
            f"Failed to parse paper response. finish_reason={finish_reason}, "
            f"raw_text={response.text!r}"
        )

    returned = {tag.question_number: tag for tag in response.parsed.tags}
    expected_qnums = set(paper_df["question_number"])
    returned_qnums = set(returned.keys())

    missing = expected_qnums - returned_qnums
    extra = returned_qnums - expected_qnums
    if missing or extra:
        raise ValueError(f"Question mismatch. Missing: {missing}, Unexpected extra: {extra}")

    return [
        {
            "question_number": qnum,
            "topic": tag.topic.value,
            "confidence": tag.confidence,
        }
        for qnum, tag in returned.items()
    ]


def tag_all_papers(
    df: pd.DataFrame,
    checkpoint_every: int = 5,
    seconds_between_calls: float = 10,
    checkpoint_path: str = "llm_tags_checkpoint.csv",
    failed_papers_path: str = "failed_papers.txt",
) -> pd.DataFrame:
    done_papers = set()
    results = []

    if os.path.exists(checkpoint_path):
        prior = pd.read_csv(checkpoint_path)
        results = prior.to_dict("records")
        done_papers = set(prior["filename"].unique())
        print(f"Resuming: {len(done_papers)} papers already tagged.")

    all_papers = df["filename"].unique()
    remaining = [f for f in all_papers if f not in done_papers]
    failed = []

    for i, filename in enumerate(tqdm(remaining)):
        paper_df = df[df["filename"] == filename]
        try:
            tags = tag_paper(paper_df)
            for t in tags:
                results.append({"filename": filename, **t})
        except Exception as e:
            print(f"FAILED paper {filename}: {e}")
            failed.append(filename)

        time.sleep(seconds_between_calls)

        if (i + 1) % checkpoint_every == 0:
            pd.DataFrame(results).to_csv(checkpoint_path, index=False)

    pd.DataFrame(results).to_csv(checkpoint_path, index=False)
    if failed:
        with open(failed_papers_path, "w") as f:
            f.write("\n".join(failed))
        print(f"{len(failed)} papers failed validation — see {failed_papers_path}")

    return pd.DataFrame(results)


df = pd.read_csv("manifest_full.csv")

tagged_df = tag_all_papers(df)

tagged_df.to_csv("llm_tags_backup.csv", index=False)