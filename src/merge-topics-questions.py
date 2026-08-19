import pandas as pd

llm_df = pd.read_csv("llm_tags_backup.csv")
questions_df = pd.read_csv("manifest_full.csv")

merged_df = pd.merge(llm_df, questions_df, on=["filename", "question_number"], how="inner")

merged_df.to_csv("tagged_questions.csv", index=False)