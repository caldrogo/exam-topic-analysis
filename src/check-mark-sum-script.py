import sys
import json
import re
from pathlib import Path


def sum_marks_from_json(json_path: str) -> None:
    path = Path(json_path)

    if not path.exists():
        print(f"Error: File '{json_path}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle both single paper dict {"questions": [...]} and list of questions [...]
        if isinstance(data, dict):
            questions = data.get("questions", [])
        elif isinstance(data, list):
            questions = data
        else:
            print("Error: Unrecognized JSON structure.", file=sys.stderr)
            sys.exit(1)

        total_marks = 0
        parsed_count = 0

        for q in questions:
            marks_raw = q.get("marks_available", "")
            
            # Extract digits from string (e.g., "[3]" -> 3)
            match = re.search(r"\d+", str(marks_raw))
            if match:
                total_marks += int(match.group())
                parsed_count += 1

        print(f"File: {path.name}")
        print(f"Questions processed: {parsed_count}")
        print(f"Total Marks Available: {total_marks}")

    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON from '{json_path}'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sum_marks.py <path_to_json_file>")
        sys.exit(1)

    sum_marks_from_json(sys.argv[1])