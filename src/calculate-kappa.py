from sklearn.metrics import cohen_kappa_score, confusion_matrix
import pandas as pd

def compute_kappa(hand_coded_df: pd.DataFrame, llm_tagged_df: pd.DataFrame) -> dict:
    merged = hand_coded_df.merge(
        llm_tagged_df, on=["filename", "question_number"], suffixes=("_human", "_llm")
    )

    assert len(merged) == len(hand_coded_df), (
        f"Merge lost rows: {len(hand_coded_df)} hand-coded vs {len(merged)} merged. "
        "Check for filename/question_number mismatches."
    )

    kappa = cohen_kappa_score(merged["human_topic"], merged["topic"])

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
        "top_disagreements": disagreement_pairs.head(10),
    }

hand_coded_df = pd.read_csv("data/manifest_sample.csv")

print(f"Hand-coded questions df: {hand_coded_df.head()}")

llm_tagged_df = pd.read_csv("data/llm_tags_backup.csv")

results = compute_kappa(hand_coded_df, llm_tagged_df)

print(f"Cohen's Kappa: {results['kappa']:.4f}")
print(f"Number of questions compared: {results['n_compared']}")
print(f"Agreement rate: {results['agreement_rate']:.2%}")