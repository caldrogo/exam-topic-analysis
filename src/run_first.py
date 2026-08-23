import pandas as pd

from config import TOPIC_LIST, INITIAL_PROMPT, DATA_PATH

init_df = pd.DataFrame({'prompt' : [INITIAL_PROMPT], 'reasoning' : ['Initial Prompt'], 'kappa' : pd.NA, 'iteration' : 1, 'agreement_rate' : pd.NA})

init_df.to_json(DATA_PATH + 'prompts.json')

from assign_topics import assign_topics

assign_topics()

from build_dataset import build

build()
