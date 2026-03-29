import pandas as pd

# Path to your Excel file
file_path = r'D:\students list\stdetns list-1.xls'

# Install xlrd if not already installed:
# pip install xlrd

# Try different header rows to find the correct one
for header_row in [0, 1, 2]:
    try:
        df = pd.read_excel(file_path, header=6)
        df.columns = df.columns.str.strip()

        print("\nHeader Row 6 - Columns Detected:")
        for col in df.columns:
            print(f"'{col}'")

    except Exception as e:
        print(f"Failed at header row {header_row}: {e}")
