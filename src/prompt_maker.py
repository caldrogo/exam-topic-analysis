import asyncio
import os
import uuid

from pydantic import BaseModel, Field

import pandas as pd

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from config import PROMPT_MODEL_NAME, DATA_PATH

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "prompt_optimizer"
USER_ID = "optimizer_user"

TASK = """
Task: Automated topic tagging of IGCSE International Mathematics (0607) exam
questions, for building topic-based revision worksheets.

Input: The full text of one exam paper (all questions and sub-questions
together, as they appear in the paper), plus a fixed list of topic labels
(TOPIC_LIST) the model must choose from.

Expected output: A JSON list with one entry per question/sub-question,
each containing question_number (matching the source paper exactly),
question_text, marks_available, and a single topic tag chosen verbatim
from TOPIC_LIST.

Ground truth: Each question in the eval set has been independently tagged
by an experienced maths teacher with one topic from the same TOPIC_LIST.

Scoring: Cohen's kappa between the model's tags and the teacher's tags
across the eval set (kappa_score). Kappa is used rather than raw accuracy
because topic classes are imbalanced and we want a metric that corrects
for agreement expected by chance. Higher is better; 1.0 is perfect
agreement, 0 is chance-level agreement.

Known failure modes to watch for: (1) topic strings that don't exactly
match TOPIC_LIST (wrong spelling/casing/phrasing), (2) questions skipped,
merged, or renumbered relative to the source paper, (3) tagging based on
surface features (e.g. "has a graph" -> Graphs) rather than the primary
skill being tested, (4) inconsistent handling of multi-topic questions.
"""

# ---------------------------------------------------------------------------
# Structured output: forces Gemini to return {reasoning, new_prompt} as JSON
# instead of free text you'd have to parse out of a longer reply.
# ---------------------------------------------------------------------------
class OptimizedPrompt(BaseModel):
    reasoning: str = Field(
        description=(
            "Brief analysis of what likely helped or hurt the score in each "
            "of the two prior prompts."
        )
    )
    new_prompt: str = Field(
        description=(
            "The complete, ready-to-use improved prompt text. No preamble, "
            "no commentary -- just the prompt itself."
        )
    )


optimizer_agent = Agent(
    model=PROMPT_MODEL_NAME,
    name="prompt_optimizer",
    description="Proposes an improved prompt given two previous prompt+score pairs.",
    instruction=(
        "You are an expert prompt engineer running one step of an optimization "
        "loop. You will be given a task description, the best-scoring prompt "
        "found so far, and the most recently tried prompt, each with a numeric "
        "score (higher is better) produced by an external evaluation function.\n\n"
        "Analyze why the best prompt scored higher, and whether the most recent "
        "prompt contains any useful ideas worth keeping even though it scored "
        "lower (or equal/higher -- treat it as new information either way). "
        "Then write ONE new candidate prompt designed to score higher than both.\n\n"
        "Make targeted, deliberate edits rather than an unrelated rewrite: keep "
        "what is evidently working, change what is likely hurting the score. "
        "Do not just return one of the two prompts unchanged."
    ),
    output_schema=OptimizedPrompt,
)

session_service = InMemorySessionService()
runner = Runner(agent=optimizer_agent, app_name=APP_NAME, session_service=session_service)


def _build_meta_prompt(
    task_description: str,
    best_prompt: str,
    best_score: float,
    latest_prompt: str,
    latest_score: float,
) -> str:
    return f"""TASK THE PROMPT IS FOR:
{task_description}

BEST PROMPT SO FAR (score: {best_score}):
---
{best_prompt}
---

MOST RECENT PROMPT TRIED (score: {latest_score}):
---
{latest_prompt}
---

Write one new candidate prompt that should score higher than both."""


async def propose_next_prompt(
    task_description: str,
    best_prompt: str,
    best_score: float,
    latest_prompt: str,
    latest_score: float,
) -> tuple[str, str]:
    """Ask Gemini (via ADK) for one new candidate prompt.

    Returns (new_prompt, reasoning).
    """
    session_id = f"opt-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=_build_meta_prompt(
                    task_description, best_prompt, best_score, latest_prompt, latest_score
                )
            )
        ],
    )

    final_text = None
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    if final_text is None:
        raise RuntimeError("No response received from the optimizer agent.")

    result = OptimizedPrompt.model_validate_json(final_text)
    return result.new_prompt, result.reasoning


if __name__ == "__main__":
    prompt_df = pd.read_json(DATA_PATH + 'prompts.json')

    best_row = prompt_df.loc[prompt_df['kappa_score'].idxmax()] 
    latest_row = prompt_df.sort_values('iteration').iloc[-1]

    best_prompt, best_score = best_row['prompt'], best_row['kappa_score']
    latest_prompt, latest_score = latest_row['prompt'], latest_row['kappa_score']

    new_prompt, reasoning = asyncio.run(propose_next_prompt(
        task_description='TASK',
        best_prompt=best_prompt,
        best_score=best_score,
        latest_prompt=latest_prompt,
        latest_score=latest_score,
        ))

    new_prompt_df = pd.DataFrame({'prompt' : [new_prompt], 'iteration': [latest_row['iteration'] + 1], 'reasoning': [reasoning], 'kappa_score': [pd.NA]})

    prompt_df = pd.concat([prompt_df, new_prompt_df]).reset_index()

    prompt_df.to_json(DATA_PATH + 'prompts.json')