import pandas as pd
def test_read():
    try:
        # Replace 'DEMO_J.XPT' with the name of one of your downloaded files
        df = pd.read_sas('DEMO_J.XPT', format='xport')
        print("Success! Pandas read the file using its internal engine.")
        print(df.head())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_read()