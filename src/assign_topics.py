import json
import os
from pathlib import Path
from typing import List
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


from config import TOPIC_LIST, ASSIGN_MODEL_NAME

prompt_df = pd.read_json('data/prompts.json')
SYSTEM_PROMPT = prompt_df


# 1. Define the Pydantic output schema
class QuestionItem(BaseModel):
    question_number: str = Field(
        description="The question number or sub-part label (e.g., '1', '1(a)', '9(b)(i)')"
    )
    question_text: str = Field(
        description="The full text of the question or prompt"
    )
    marks_available: str = Field(
        description="The marks allocated for this question in brackets, e.g., '[3]', '[1]'"
    )
    topic: str = Field(
        description="The topic assigned to the question"
    )


class QuestionExtractionResult(BaseModel):
    questions: List[QuestionItem]

def has_second_last_digit_six(file_path: Path) -> bool:
    stem = file_path.stem  # Filename without extension
    # Check if stem has at least 2 characters and the 2nd to last char is '6'
    return len(stem) >= 2 and stem[-2] == "6"


def process_pdf_folder_with_resumption(
    input_dir: str = "data/papers_raw",
    output_dir: str = "data/tagged_papers_json",
    model_name: str = "gemini-3.5-flash-lite",
    overwrite_existing: bool = False,
):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all PDF files in the target directory
    # Filter out files where the second-to-last character in the name is '6'
    pdf_files = [f for f in input_path.glob("*.pdf") if not has_second_last_digit_six(f)]

    if not pdf_files:
        print(f"No PDF files found in '{input_dir}'.")
        return

    # Check for pending vs already completed files
    to_process = []
    skipped_count = 0

    pdf_files


    for pdf_file in pdf_files[0:10]:

        json_filename = pdf_file.stem + ".json"
        target_json_path = output_path / json_filename

        if target_json_path.exists() and not overwrite_existing:
            skipped_count += 1
        else:
            to_process.append(pdf_file)

    print(f"Found {len(pdf_files)} PDF(s) total.")
    print(f"  ├─ {skipped_count} already processed (skipping)")
    print(f"  └─ {len(to_process)} remaining to process\n")

    if not to_process:
        print("All PDFs have already been processed. Nothing to do!")
        _rebuild_combined_json(output_path)
        return

    # Initialize the GenAI client only if there are files left to process
    client = genai.Client()

    for i, pdf_file in enumerate(to_process, start=1):
        json_filename = pdf_file.stem + ".json"
        individual_json_path = output_path / json_filename

        print(f"[{i}/{len(to_process)}] Processing: {pdf_file.name} ...")

        try:
            # Read PDF bytes
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()

            pdf_part = types.Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf",
            )

            # API Call with Structured Output
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    pdf_part,
                    (
                        SYSTEM_PROMPT
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuestionExtractionResult,
                ),
            )

            # Parse and save JSON immediately to guarantee state persistence
            extracted_data = json.loads(response.text)

            with open(individual_json_path, "w", encoding="utf-8") as out_f:
                json.dump(extracted_data, out_f, indent=2, ensure_ascii=False)

            question_count = len(extracted_data.get("questions", []))
            print(f"  └─ Saved {question_count} questions -> {individual_json_path}")

        except Exception as e:
            print(f"  └─ ERROR processing {pdf_file.name}: {e}")
            # The script continues to the next file; this failed file will be retried next run

    # Rebuild the master combined aggregate file after run completes
    _rebuild_combined_json(output_path)
    print(f"\nBatch job completed. Output saved in '{output_dir}/'.")


def _rebuild_combined_json(output_path: Path):
    """Utility to build/update a single master JSON from all individual outputs."""
    combined_results = {}
    json_files = [
        f for f in output_path.glob("*.json") if not f.name.startswith("_")
    ]

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                combined_results[jf.stem + ".pdf"] = data.get("questions", [])
        except Exception:
            pass

    combined_json_path = output_path / "_all_extracted_papers.json"
    with open(combined_json_path, "w", encoding="utf-8") as comb_f:
        json.dump(combined_results, comb_f, indent=2, ensure_ascii=False)

    print(f"Updated aggregate file: {combined_json_path}")


if __name__ == "__main__":
    process_pdf_folder_with_resumption(model_name=ASSIGN_MODEL_NAME)