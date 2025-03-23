#!/usr/bin/env python3
"""
Test script to verify the extraction of heading1 content from Limitless API responses.
"""

import json
import os
from datetime import datetime
import sys

# Create sample Limitless data with heading1 content
sample_limitless_data = {
    "lifelogs": [
        {
            "id": "sample123",
            "title": "Test Lifelog",
            "startTime": "2025-03-23T10:00:00Z",
            "endTime": "2025-03-23T10:30:00Z",
            "contents": [
                {
                    "type": "heading1",
                    "content": "This is a test summary from heading1"
                },
                {
                    "type": "paragraph",
                    "content": "This is regular paragraph content that should not be used as the main summary"
                },
                {
                    "type": "heading2",
                    "content": "Secondary heading that isn't the main summary"
                }
            ]
        }
    ]
}

# Create a function to extract heading1 content, similar to the one in consolidated_summary.py
def extract_heading1_content(lifelog_data):
    """Extract heading1 content from Limitless lifelog data."""
    results = []
    
    for log in lifelog_data.get("lifelogs", []):
        # Extract high-level summary from heading1
        high_level_summary = ""
        for item in log.get("contents", []):
            if item.get("type") == "heading1":
                high_level_summary = item.get("content", "")
                break
        
        results.append({
            "title": log.get("title", ""),
            "summary": high_level_summary,
            "all_content_types": [item.get("type") for item in log.get("contents", [])]
        })
    
    return results

# Run the test
def main():
    print("Testing heading1 extraction from Limitless data...")
    
    # Extract data
    extracted_data = extract_heading1_content(sample_limitless_data)
    
    # Print results
    print("\nExtracted data:")
    for item in extracted_data:
        print(f"Title: {item['title']}")
        print(f"Summary (from heading1): '{item['summary']}'")
        print(f"All content types in lifelog: {item['all_content_types']}")
    
    # Verify extraction
    if extracted_data and extracted_data[0]["summary"] == "This is a test summary from heading1":
        print("\nSUCCESS: Correctly extracted heading1 content as the summary!")
    else:
        print("\nFAILURE: heading1 content was not correctly extracted")
        
    # Save test output to file
    os.makedirs("data/tests", exist_ok=True)
    output_path = f"data/tests/heading1_extraction_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_path, 'w') as f:
        json.dump({
            "input": sample_limitless_data,
            "extracted": extracted_data,
            "test_result": "success" if extracted_data[0]["summary"] == "This is a test summary from heading1" else "failure"
        }, f, indent=2)
    
    print(f"\nTest results saved to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())