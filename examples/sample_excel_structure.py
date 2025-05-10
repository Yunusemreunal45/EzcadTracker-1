"""
This script generates a sample Excel file for demonstrating the EZCAD2 Automation application.
It creates a file with common fields used in laser marking applications.
"""

import pandas as pd
import os

def create_sample_excel():
    """Create a sample Excel file for demonstration"""
    
    # Create sample data
    data = {
        "ID": list(range(1, 11)),
        "SerialNumber": ["SN" + str(100000 + i) for i in range(1, 11)],
        "PartNumber": ["PN-A1234" for _ in range(10)],
        "Date": ["2025-05-10" for _ in range(10)],
        "Text1": ["Sample Text 1-" + str(i) for i in range(1, 11)],
        "Text2": ["Sample Text 2-" + str(i) for i in range(1, 11)],
        "QRCode": ["https://example.com/product/" + str(i) for i in range(1, 11)],
        "Processed": [False for _ in range(10)],
        "Processed_Time": ["" for _ in range(10)]
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create examples directory if it doesn't exist
    if not os.path.exists("examples"):
        os.makedirs("examples")
    
    # Save to Excel
    excel_path = "examples/sample_data.xlsx"
    df.to_excel(excel_path, index=False)
    
    print(f"Sample Excel file created at: {excel_path}")
    
    return excel_path

if __name__ == "__main__":
    create_sample_excel()