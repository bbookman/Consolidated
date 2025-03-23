"""
Consolidated Summary Comparison

This script compares Bee and Limitless data for overlapping time periods and 
generates a formatted text file with the original data and a consolidated summary.
"""

import json
import datetime
import os
from dateutil.parser import parse
import pytz
from consolidated_summary import (
    load_json_file, get_latest_file, normalize_timestamp, 
    extract_bee_summaries, extract_lifelog_content, 
    match_events_by_time, format_lifelog_content
)

def find_matching_events(tolerance_minutes=5):
    """Find events that match between Bee and Limitless."""
    # Load the latest data files
    bee_conversations_file = get_latest_file("data/bee", "conversations_")
    limitless_lifelogs_file = get_latest_file("data/limitless", "lifelogs_")
    
    if not bee_conversations_file or not limitless_lifelogs_file:
        print("Error: Required data files not found.")
        return []
    
    print(f"Loading Bee conversations from: {bee_conversations_file}")
    print(f"Loading Limitless lifelogs from: {limitless_lifelogs_file}")
    
    bee_data = load_json_file(bee_conversations_file)
    limitless_data = load_json_file(limitless_lifelogs_file)
    
    # Extract summaries and content with timestamps
    bee_summaries = extract_bee_summaries(bee_data)
    limitless_contents = extract_lifelog_content(limitless_data)
    
    print(f"Extracted {len(bee_summaries)} summaries from Bee conversations")
    print(f"Extracted {len(limitless_contents)} content items from Limitless lifelogs")
    
    # Match events by overlapping time periods
    event_groups = match_events_by_time(bee_summaries, limitless_contents)
    
    # Filter only groups that have both Bee and Limitless data
    matching_events = []
    for group in event_groups:
        bee_items = [e for e in group if e["source"] == "Bee"]
        limitless_items = [e for e in group if e["source"] == "Limitless"]
        
        if bee_items and limitless_items:
            matching_events.append({
                "bee_items": bee_items,
                "limitless_items": limitless_items,
                "start_time": min(event["start_time"] for event in group),
                "end_time": max([event["end_time"] for event in group if event["end_time"]], default=None)
            })
    
    print(f"Found {len(matching_events)} time periods with both Bee and Limitless data")
    return matching_events

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
    return " ".join(explanation[:7])  # Limit to 7 sentences as requested

def create_comparison_file(matching_events):
    """Create a text file with the comparison and consolidated summary."""
    if not matching_events:
        print("No matching events found for comparison.")
        return
    
    # The output directory is created automatically by app.py
    # but we'll ensure it exists here as well for standalone script usage
    consolidated_dir = os.path.join(os.getcwd(), "data", "consolidated_summaries")
    os.makedirs(consolidated_dir, exist_ok=True)
    
    # Pick the first matching event for the example
    event = matching_events[0]
    bee_item = event["bee_items"][0]  # Take the first Bee item
    limitless_item = event["limitless_items"][0]  # Take the first Limitless item
    
    # Format the time period
    start_time = event["start_time"]
    end_time = event["end_time"] or start_time
    start_str = start_time.strftime("%Y-%m-%d %H:%M")
    end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
    time_period = f"{start_str} to {end_str}"
    
    # Generate consolidated summary
    consolidated_summary = generate_consolidated_summary(event["bee_items"], event["limitless_items"])
    
    # Generate explanation of differences
    differences_explanation = generate_differences_explanation(event["bee_items"], event["limitless_items"])
    
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
    output_file = f"data/consolidated_summaries/comparison_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    print(f"Comparison file created: {output_file}")
    return output_file

def main():
    """Main function."""
    matching_events = find_matching_events()
    if matching_events:
        output_file = create_comparison_file(matching_events)
        print(f"Successfully created comparison file: {output_file}")
    else:
        print("No matching events found, no comparison file created.")

if __name__ == "__main__":
    main()