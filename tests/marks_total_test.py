import pandas as pd

def marks_total_test() -> None:
    df = pd.read_csv('data/dataset_full.csv')
    print(df.groupby('filename')['marks'].sum())

if __name__ == "__main__":
    marks_total_test()