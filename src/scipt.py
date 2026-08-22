import pandas as pd

df = pd.read_json('data/prompts.json')

print(df[df['iteration']==3])