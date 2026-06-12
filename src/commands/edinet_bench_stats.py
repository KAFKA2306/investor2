import pandas as pd
from src.io.edinet_bench import load_fraud_detection, load_earnings_forecast, load_industry_prediction

def print_section(title):
    print(f"\n✨ {title} ✨")
    print("=" * 40)

def analyze_dataset(name, df, label_col):
    print_section(f"Analysis for: {name}")
    print(f"Total Rows: {len(df)}")
    print(f"Unique Companies (EDINET Code): {df['edinet_code'].nunique()}")
    
    if label_col in df.columns:
        print("\nLabel Distribution:")
        dist = df[label_col].value_counts(normalize=True) * 100
        counts = df[label_col].value_counts()
        for label, percent in dist.items():
            print(f"  - Label {label}: {counts[label]} ({percent:.2f}%)")
    
    # Text length stats for 'summary' column (if it exists and is string-like)
    if 'summary' in df.columns:
        # Note: 'summary' seems to be a JSON string or dict in the parquet
        # Let's just check the raw character length if it's a string
        if isinstance(df['summary'].iloc[0], str):
            avg_len = df['summary'].str.len().mean()
            print(f"\nAverage Summary Length: {avg_len:.2f} characters")

def main():
    print("🎀 EDINET-Bench Statistics Master 🎀")
    
    # 1. Fraud Detection
    try:
        df_fraud = load_fraud_detection("train")
        analyze_dataset("Fraud Detection (Train)", df_fraud, "label")
    except Exception as e:
        print(f"Error loading Fraud Detection: {e}")

    # 2. Earnings Forecast
    try:
        df_earnings = load_earnings_forecast("train")
        analyze_dataset("Earnings Forecast (Train)", df_earnings, "label")
    except Exception as e:
        print(f"Error loading Earnings Forecast: {e}")

    # 3. Industry Prediction
    try:
        df_industry = load_industry_prediction("train")
        analyze_dataset("Industry Prediction (Train)", df_industry, "industry")
        
        print("\nTop 10 Industries:")
        top_industries = df_industry["industry"].value_counts().head(10)
        for ind, count in top_industries.items():
            print(f"  - {ind}: {count}")
    except Exception as e:
        print(f"Error loading Industry Prediction: {e}")

    print("\n💖 Statistics calculation complete! 🌈✨")

if __name__ == "__main__":
    main()
