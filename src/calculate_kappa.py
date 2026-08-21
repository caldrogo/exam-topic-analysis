import pandas as pd

def compute_kappa(hand_coded_df: pd.DataFrame, llm_tagged_df: pd.DataFrame) -> dict:
    merged = hand_coded_df.merge(
        llm_tagged_df, on=["filename", "question_number"], suffixes=("_human", "_llm")
    )

    assert len(merged) == len(hand_coded_df), (
        f"Merge lost rows: {len(hand_coded_df)} hand-coded vs {len(merged)} merged. "
        "Check for filename/question_number mismatches."
    )

    kappa = cohen_kappa_score_me(merged["human_topic"], merged["topic"])

    # Per-topic disagreement breakdown — WHERE the model struggles, not just how much
    disagreements = merged[merged["human_topic"] != merged["topic"]]
    disagreement_pairs = (
        disagreements.groupby(["human_topic", "topic"])
        .size()
        .sort_values(ascending=False)
    )

    return {
        "kappa": kappa,
        "n_compared": len(merged),
        "agreement_rate": (merged["human_topic"] == merged["topic"]).mean(),
        "top_disagreements": disagreement_pairs.head(),
    }

def cohen_kappa_score_me(y1, y2):
    assert len(y1) == len(y2)
    n = len(y1)

    # Get all unique categories
    categories = sorted(set(y1) | set(y2))

    # Build confusion matrix
    matrix = {c: {c2: 0 for c2 in categories} for c in categories}
    for a, b in zip(y1, y2):
        matrix[a][b] += 1

    # Observed agreement (Po)
    po = sum(matrix[c][c] for c in categories) / n

    # Expected agreement (Pe)
    row_totals = {c: sum(matrix[c].values()) for c in categories}
    col_totals = {c: sum(matrix[r][c] for r in categories) for c in categories}
    pe = sum((row_totals[c] / n) * (col_totals[c] / n) for c in categories)

    # Kappa
    if pe == 1:
        return 1.0  # avoid division by zero if perfect agreement expected
    kappa = (po - pe) / (1 - pe)
    return kappa