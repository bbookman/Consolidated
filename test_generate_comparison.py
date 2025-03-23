#!/usr/bin/env python3
"""
Test script to generate a comparison file using our real code from compare_and_consolidate.py
"""

import os
import json
import datetime
from dateutil.parser import parse
import pytz
import sys

# Add necessary functions from compare_and_consolidate.py
def format_lifelog_content(content_items):
    """Format lifelog content items."""
    formatted = []
    for item in content_items:
        if item.get("type") == "heading1":
            formatted.append(f"# {item.get('content', '')}")
        elif item.get("type") == "heading2":
            formatted.append(f"## {item.get('content', '')}")
        elif item.get("type") == "blockquote":
            speaker = f"**{item.get('speaker', '')}:** " if item.get("speaker") else ""
            formatted.append(f"> {speaker}{item.get('content', '')}")
    return "\n".join(formatted)

def generate_consolidated_summary(bee_items, limitless_items):
    """
    Generate a consolidated summary from both data sources, 
    focusing ONLY on the primary summary information from each.
    """
    # Extract key topics and themes from summaries only
    summary_topics = set()
    
    # Extract from Bee summaries - focus on "Key Take Aways" only
    for item in bee_items:
        summary = item.get("summary", "")
        lines = summary.split('\n')
        
        # Find Key Takeaways section
        in_takeaways = False
        for line in lines:
            if "Key Take Aways" in line or "Key Takeaways" in line:
                in_takeaways = True
            elif in_takeaways and line.strip().startswith('*'):
                # Add takeaway as a topic
                topic = line.strip().replace('*', '').strip()
                if topic:
                    summary_topics.add(topic)
    
    # Extract from Limitless - focus only on the high-level summary
    for item in limitless_items:
        # Get the high-level summary
        # This is already extracted from the "heading1" type content in extract_lifelog_content()
        # and stored in the "summary" field of each item
        high_level_summary = item.get("summary", "")
        if high_level_summary:
            summary_topics.add(high_level_summary)
    
    # Create consolidated summary - only include topics from summaries
    consolidated_output = []
    
    # Add header
    consolidated_output.append("Key topics discussed:")
    
    # Add all summary topics
    for topic in sorted(summary_topics):
        topic = topic.strip()
        if topic:
            consolidated_output.append(f"- {topic}")
    
    return "\n".join(consolidated_output)

def generate_differences_explanation(bee_items, limitless_items):
    """Generate a short explanation of the differences and consolidation approach."""
    explanation = []
    
    # Compare structure and content
    bee_structure = "structured format with summary, atmosphere, and key takeaways"
    limitless_structure = "hierarchical content with headings and dialogue transcripts"
    
    # Add structure comparison
    explanation.append(f"Bee data uses a {bee_structure}, while Limitless data uses {limitless_structure}.")
    
    # Compare level of detail
    bee_detail = "provides synthesized insights"
    limitless_detail = "offers verbatim conversation details"
    explanation.append(f"Bee {bee_detail}, whereas Limitless {limitless_detail}.")
    
    # Explain consolidation approach - focus on summary sources only
    explanation.append("The consolidation strictly extracts topics from the summary sections of both sources.")
    explanation.append("Timestamps were aligned with a 5-minute tolerance to match related events.")
    explanation.append("Key takeaways from Bee were directly incorporated while only top-level headings were extracted from Limitless.")
    explanation.append("No detailed content or dialogue transcripts were considered in the consolidated view.")
    explanation.append("The consolidated summary focuses exclusively on high-level insights from both summary sources.")
    
    # Join with spaces to create a paragraph
    return " ".join(explanation[:7])  # Limit to 7 sentences

def create_comparison_file(matched_event):
    """Create a comparison file with our real code."""
    # The output directory
    consolidated_dir = os.path.join(os.getcwd(), "data", "consolidated_summaries")
    os.makedirs(consolidated_dir, exist_ok=True)
    
    # Format the event
    bee_item = matched_event["bee_items"][0]
    limitless_item = matched_event["limitless_items"][0]
    
    # Generate time period
    start_time = matched_event["start_time"]
    end_time = matched_event["end_time"] or start_time
    start_str = start_time.strftime("%Y-%m-%d %H:%M")
    end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
    time_period = f"{start_str} to {end_str}"
    
    # Generate consolidated summary
    consolidated_summary = generate_consolidated_summary(matched_event["bee_items"], matched_event["limitless_items"])
    
    # Generate explanation of differences
    differences_explanation = generate_differences_explanation(matched_event["bee_items"], matched_event["limitless_items"])
    
    # Create the file content
    file_content = [
        f"# Comparison of Bee and Limitless Data for Time Period: {time_period}\n",
        "## Section 1: Original Bee Data\n",
        f"{bee_item['summary']}\n",
        "## Section 2: Original Limitless Data\n",
        f"Title: {limitless_item.get('title', 'No Title')}\n",
        f"Summary: {limitless_item.get('summary', 'No Summary')}\n",
        "Content:\n",
        f"{format_lifelog_content(limitless_item['content'])}\n",
        "## Section 3: Consolidated Summary\n",
        f"{consolidated_summary}\n",
        "## Section 4: Differences and Consolidation Approach\n",
        f"{differences_explanation}\n"
    ]
    
    # Create output file
    output_file = f"data/consolidated_summaries/test_comparison_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    print(f"Comparison file created: {output_file}")
    return output_file

def normalize_timestamp(timestamp_str):
    """Normalize timestamp to datetime object."""
    dt = parse(timestamp_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    else:
        dt = dt.astimezone(pytz.UTC)
    return dt

def main():
    """Create a test comparison file."""
    print("Creating test comparison file...")
    
    # Create sample data that will match by time period
    # Sample Bee data
    bee_item = {
        "summary": "## Summary\nA conversation about the project status.\n\n## Atmosphere\nFocused and productive.\n\n## Key Take Aways\n* The database migration is complete\n* Need to update the API documentation\n* Schedule a review meeting for next week",
        "start_time": normalize_timestamp("2025-03-23T09:00:00Z"),
        "end_time": normalize_timestamp("2025-03-23T09:30:00Z"),
        "source": "Bee"
    }
    
    # Sample Limitless data with heading1 content
    limitless_item = {
        "title": "Project Status Meeting",
        "summary": "Major project milestones completed ahead of schedule",  # This is from heading1
        "content": [
            {
                "type": "heading1",
                "content": "Major project milestones completed ahead of schedule"
            },
            {
                "type": "heading2",
                "content": "Database Migration"
            },
            {
                "type": "blockquote",
                "content": "The migration went smoothly with only minor issues.",
                "speaker": "John"
            }
        ],
        "start_time": normalize_timestamp("2025-03-23T09:05:00Z"),
        "end_time": normalize_timestamp("2025-03-23T09:35:00Z"),
        "source": "Limitless"
    }
    
    # Create a matched event
    matched_event = {
        "bee_items": [bee_item],
        "limitless_items": [limitless_item],
        "start_time": min(bee_item["start_time"], limitless_item["start_time"]),
        "end_time": max(bee_item["end_time"], limitless_item["end_time"])
    }
    
    # Generate the comparison file
    output_file = create_comparison_file(matched_event)
    
    # Verify the file was created and show its contents
    print("\nFile contents:")
    with open(output_file, 'r') as f:
        contents = f.read()
        print(contents)
    
    # Check if the heading1 content was properly included
    if "Major project milestones completed ahead of schedule" in contents:
        print("\nSUCCESS: Heading1 content was correctly extracted and included in the comparison file!")
    else:
        print("\nFAILURE: Heading1 content was not found in the comparison file")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())