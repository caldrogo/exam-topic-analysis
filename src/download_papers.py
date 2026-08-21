import requests
import time
from pathlib import Path

SYLLABUS = "0607"
YEARS = range(14, 26)          

SESSIONS = ["s", "w", 'm']

PAPERS = {"2": "noncalc", "4": "calc", "6": "investigation"}

VARIANTS = ["1", "2", "3"]

INCLUDE_MARK_SCHEMES = False
DOC_TYPES = ["qp"] + (["ms"] if INCLUDE_MARK_SCHEMES else [])

BASE_URL = (
    "https://pastpapers.papacambridge.com/download_file.php?files=https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/{filename}"
)



OUT_DIR = Path("papers_raw")
OUT_DIR.mkdir(exist_ok=True)

REQUEST_DELAY_SECONDS = 1.5 


def build_filename(session, year, doc_type, paper, variant):
    return f"{SYLLABUS}_{session}{year}_{doc_type}_{paper}{variant}.pdf"


def download_one(session, year, doc_type, paper, variant):
    filename = build_filename(session, year, doc_type, paper, variant)
    url = BASE_URL.format(filename=filename)
    out_path = OUT_DIR / filename

    if out_path.exists():
        return "skipped", filename

    try:
        resp = requests.get(url, timeout=20)
    except requests.RequestException as e:
        return "error", f"{filename} ({e})"
    finally:
        time.sleep(REQUEST_DELAY_SECONDS)

    if resp.status_code == 200:
        out_path.write_bytes(resp.content)
        return "downloaded", filename
    else:
        return "failed", filename


def main():
    results = {"downloaded": [], "skipped": [], "failed": [], "error": []}

    for year in YEARS:
        for session in SESSIONS:
            for paper in PAPERS:
                for variant in VARIANTS:
                    for doc_type in DOC_TYPES:
                        status, filename = download_one(
                            session, year, doc_type, paper, variant
                        )
                        results[status].append(filename)
                        print(f"{status:10s} {filename}")

    print("\n--- Summary ---")
    for status, files in results.items():
        print(f"{status}: {len(files)}")

    if results["failed"]:
        print(
            "\n'failed' entries are expected if SESSIONS/VARIANTS don't yet "
            "match your real pattern -- use this list to sanity-check and "
            "trim the config above."
        )


if __name__ == "__main__":
    main()