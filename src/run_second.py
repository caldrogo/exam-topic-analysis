import os
import shutil

import pandas as pd


from calculate_kappa import compute_kappa

latest_df = pd.read_csv('data/dataset_full_latest.csv')
human_df = pd.read_csv('data/dataset_sample.csv')
prompts_df = pd.read_json('data/prompts.json')

stats = compute_kappa(human_df, latest_df)
prompts_df.loc[prompts_df['iteration'].idxmax(), 'kappa']  = stats['kappa']
prompts_df.loc[prompts_df['iteration'].idxmax(), 'agreement_rate']  = stats["agreement_rate"]


shutil.move(os.path.join("data/",'dataset_full_latest.csv'), os.path.join("data/",'dataset_full.csv'))
shutil.move(os.path.join("data/",'tagged_papers_latest_json'), os.path.join("data/",'tagged_papers_json'))


prompts_df.to_json('data/prompts.json')