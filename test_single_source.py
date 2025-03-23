"""
Test script to demonstrate how the comparison file looks with only one source
"""
import os
import json
import datetime
from compare_and_consolidate import generate_consolidated_summary, generate_differences_explanation

def load_json_file(file_path):
    """Load and parse JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def main():
    """Create a test comparison with only Bee data."""
    # Ensure the output directory exists
    consolidated_dir = os.path.join(os.getcwd(), "data", "consolidated_summaries")
    os.makedirs(consolidated_dir, exist_ok=True)
    
    # Create test data - only Bee
    bee_item = {
        "summary": """## Summary
        
        Bruce is reviewing his blood tests with someone else. His blood glucose level is 125 mg/dL, which is on the higher side but not in the diabetic range. His weight is 188 lbs, which seems consistent with previous measurements. Bruce also mentions needing to move Benetton's things to use the bathroom.
        
        ## Atmosphere
        
        The conversation is calm and matter-of-fact. Bruce seems slightly concerned about his glucose level but not overly worried. There's a practical tone as they discuss the logistics of the bathroom situation.
        
        ## Key Take Aways
        
        * Bruce's blood glucose was 125.
        * Bruce's weight was 188 lbs.
        * Bruce had to move Benetton's things to use the bathroom.
        """
    }
    
    # Empty Limitless data
    limitless_item = {}
    
    # Time period
    start_time = datetime.datetime.strptime("2025-03-22 12:20:00", "%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.strptime("2025-03-22 12:35:00", "%Y-%m-%d %H:%M:%S")
    
    start_str = start_time.strftime("%Y-%m-%d %H:%M")
    end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
    time_period = f"{start_str} to {end_str}"
    
    # Generate consolidated summary with only Bee data
    bee_items = [bee_item]
    limitless_items = []
    consolidated_summary = generate_consolidated_summary(bee_items, limitless_items)
    
    # Generate explanation
    differences_explanation = generate_differences_explanation(bee_items, limitless_items)
    
    # Extract only the bullet points from the "Key Take Aways" section
    bee_key_points = []
    bee_key_takeaways = "No key points found"  # Initialize with default value
    
    if bee_item.get('summary'):
        lines = bee_item['summary'].split('\n')
        in_takeaways = False
        
        for line in lines:
            if "Key Take Aways" in line or "Key Takeaways" in line:
                in_takeaways = True
            elif in_takeaways and line.strip().startswith('*'):
                # Only add the bullet points, not the "Key Take Aways" heading
                bee_key_points.append(line.strip())
        
        if bee_key_points:
            bee_key_takeaways = "\n".join(bee_key_points)
    
    # Create the file content
    file_content = [
        f"# Comparison with Only Bee Data for Time Period: {time_period}\n",
        "## Section 1: Original Bee Summary\n",
        f"{bee_key_takeaways}\n",  # We've already set a default value
        "## Section 2: Original Limitless Summary\n",
        "No Limitless data available for this time period.\n",
        "## Section 3: Consolidated Summary\n",
        f"{consolidated_summary}\n",
        "## Section 4: Consolidation Approach\n",
        f"{differences_explanation}\n"
    ]
    
    # Create output file
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"data/consolidated_summaries/bee_only_comparison_{timestamp}.txt"
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    print(f"Single-source comparison file created: {output_file}")
    
    # Now create a test case with only Limitless data
    limitless_item = {
        "summary": "Conversation shifts to a child at a party, food, and Benetton's health",
        "content": []
    }
    
    # Empty Bee data
    bee_item = {}
    
    # Generate consolidated summary with only Limitless data
    bee_items = []
    limitless_items = [limitless_item]
    consolidated_summary = generate_consolidated_summary(bee_items, limitless_items)
    
    # Generate explanation
    differences_explanation = generate_differences_explanation(bee_items, limitless_items)
    
    # Create the file content
    file_content = [
        f"# Comparison with Only Limitless Data for Time Period: {time_period}\n",
        "## Section 1: Original Bee Summary\n",
        "No Bee data available for this time period.\n",
        "## Section 2: Original Limitless Summary\n",
        f"Summary: {limitless_item.get('summary', 'No Summary')}\n",
        "## Section 3: Consolidated Summary\n",
        f"{consolidated_summary}\n",
        "## Section 4: Consolidation Approach\n",
        f"{differences_explanation}\n"
    ]
    
    # Create output file
    output_file = f"data/consolidated_summaries/limitless_only_comparison_{timestamp}.txt"
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    print(f"Single-source comparison file created: {output_file}")
    
if __name__ == "__main__":
    main()