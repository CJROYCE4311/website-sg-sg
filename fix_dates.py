import pandas as pd
import os

FINANCIALS_FILE = "data/financials.csv"

def fix():
    if not os.path.exists(FINANCIALS_FILE):
        print("Financials file not found.")
        return

    df = pd.read_csv(FINANCIALS_FILE)
    
    # Check counts before
    print("Before:")
    print(df['Date'].value_counts())
    
    # Update dates
    df.loc[df['Date'] == '2025-12-07', 'Date'] = '2024-12-14'
    df.loc[df['Date'] == '2025-12-08', 'Date'] = '2024-12-14'
    
    # Save
    df.to_csv(FINANCIALS_FILE, index=False)
    
    print("\nAfter:")
    print(df['Date'].value_counts())
    print("\n✅ Dates corrected.")

if __name__ == "__main__":
    fix()
