import os
import shutil

import pandas as pd

from prompt_maker import update_prompts

update_prompts()

from assign_topics import assign_topics

assign_topics()

from build_dataset import build

build()

from calculate_kappa import compute_kappa

latest_df = pd.read_csv('data/dataset_full_latest.csv')
human_df = pd.read_csv('data/dataset_sample.csv')
prompts_df = pd.read_json('data/prompts.json')
best_kappa = prompts_df['kappa'].max()
stats = compute_kappa(human_df, latest_df)
prompts_df.loc[prompts_df['iteration'].idxmax(), 'kappa']  = stats['kappa']
prompts_df.loc[prompts_df['iteration'].idxmax(), 'agreement_rate']  = stats["agreement_rate"]

if stats['kappa'] > best_kappa:
    os.rename(os.path.join("data/",'dataset_full_latest.csv'), os.path.join("data/",'dataset_full.csv'))
    os.rename(os.path.join("data/",'tagged_papers_latest_json'), os.path.join("data/",'tagged_papers_json'))
else:
    os.remove(os.path.join("data/",'dataset_full_latest.csv'))
    shutil.rmtree(os.path.join("data/",'tagged_papers_latest_json'))


prompts_df.to_json('data/prompts.json')


