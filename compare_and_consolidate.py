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
    
    If one of the sources has no summary data, the consolidated summary
    will simply be the content from the non-null source.
    """
    # Check if either source is empty or has no meaningful summary data
    bee_has_summaries = False
    limitless_has_summaries = False
    
    # Extract key topics and themes from summaries only
    summary_topics = set()
    
    # Process Bee summaries - focus ONLY on the bullet points within "Key Take Aways" section
    bee_topics = set()
    for item in bee_items:
        summary = item.get("summary", "")
        lines = summary.split('\n')
        
        # Find Key Takeaways section but don't include the heading text itself
        in_takeaways = False
        for line in lines:
            if "Key Take Aways" in line or "Key Takeaways" in line:
                in_takeaways = True
                # Skip the heading line itself
                continue
            
            if in_takeaways and line.strip().startswith('*'):
                # Add only the bullet point content as a topic
                topic = line.strip().replace('*', '').strip()
                if topic:
                    bee_topics.add(topic)
    
    if bee_topics:
        bee_has_summaries = True
        summary_topics.update(bee_topics)
    
    # Process Limitless - focus only on the high-level summary
    limitless_topics = set()
    for item in limitless_items:
        # Get the high-level summary
        # This is already extracted from the "heading1" type content in extract_lifelog_content()
        # and stored in the "summary" field of each item
        high_level_summary = item.get("summary", "")
        if high_level_summary:
            limitless_topics.add(high_level_summary)
    
    if limitless_topics:
        limitless_has_summaries = True
        summary_topics.update(limitless_topics)
    
    # Handle the case where one source has no summary data
    if not bee_has_summaries and limitless_has_summaries:
        # Only Limitless has data, use just that
        consolidated_output = []
        consolidated_output.append("Summary from Limitless:")
        for topic in sorted(limitless_topics):
            topic = topic.strip()
            if topic:
                consolidated_output.append(f"- {topic}")
        return "\n".join(consolidated_output)
    
    elif bee_has_summaries and not limitless_has_summaries:
        # Only Bee has data, use just that
        consolidated_output = []
        consolidated_output.append("Key topics from Bee:")
        for topic in sorted(bee_topics):
            topic = topic.strip()
            if topic:
                consolidated_output.append(f"- {topic}")
        return "\n".join(consolidated_output)
    
    # Both sources have data or both are empty
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
    """Generate a concise explanation of the summary consolidation approach."""
    explanation = []
    
    # Check if both sources have data
    bee_has_data = len(bee_items) > 0 and any(item.get('summary') for item in bee_items)
    limitless_has_data = len(limitless_items) > 0 and any(item.get('summary') for item in limitless_items)
    
    if bee_has_data and limitless_has_data:
        # Both sources have data - regular explanation
        explanation.append("This consolidated summary extracts only key information from both sources.")
        explanation.append("From Bee data, we extract the 'Key Take Aways' bullet points.")
        explanation.append("From Limitless data, we extract only the top-level heading1 content.")
        explanation.append("Timestamps were aligned with a 5-minute tolerance to match related events.")
        explanation.append("All detailed content, dialogue transcripts, and background information is excluded.")
        explanation.append("The consolidated summary focuses exclusively on high-level insights.")
        explanation.append("Topics are presented as a simple bulleted list for clarity and direct insight extraction.")
    elif bee_has_data and not limitless_has_data:
        # Only Bee has data
        explanation.append("Only Bee data is available for this time period.")
        explanation.append("The consolidated summary contains only Bee's 'Key Take Aways' bullet points.")
        explanation.append("No Limitless data was found with matching timestamps (within 5-minute tolerance).")
        explanation.append("The summary represents a direct extraction of Bee's high-level insights.")
        explanation.append("Only bullet points from the Key Take Aways section are included.")
        explanation.append("Detailed content and dialogue transcripts are excluded.")
    elif not bee_has_data and limitless_has_data:
        # Only Limitless has data
        explanation.append("Only Limitless data is available for this time period.")
        explanation.append("The consolidated summary contains only Limitless's top-level heading1 content.")
        explanation.append("No Bee data was found with matching timestamps (within 5-minute tolerance).")
        explanation.append("The summary represents a direct extraction of Limitless's high-level insights.")
        explanation.append("Only top-level headings from the content are included.")
        explanation.append("Detailed content and dialogue transcripts are excluded.")
    else:
        # Neither has useful data - shouldn't happen but handle it
        explanation.append("No meaningful summary data was found from either source for this time period.")
        explanation.append("Both sources had records but no extractable summary content was present.")
        explanation.append("The consolidated view is empty or contains only metadata.")
    
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
    
    # Extract only the bullet points from the "Key Take Aways" section, not the heading itself
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
    
    # Create the file content - with focus only on summaries
    file_content = [
        f"# Comparison of Bee and Limitless Data for Time Period: {time_period}\n",
        "## Section 1: Original Bee Summary\n",
        f"{bee_key_takeaways}\n",  # We've already set a default value
        "## Section 2: Original Limitless Summary\n",
        f"Summary: {limitless_item.get('summary', 'No Summary')}\n",
        "## Section 3: Consolidated Summary\n",
        f"{consolidated_summary}\n",
        "## Section 4: Consolidation Approach\n",
        f"{differences_explanation}\n"
    ]
    
    # Create output file
    output_file = f"data/consolidated_summaries/comparison_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    print(f"Comparison file created: {output_file}")
    return output_file

def ensure_directory_structure():
    """Ensure all necessary directories exist."""
    directories = [
        "data",
        "data/bee",
        "data/limitless",
        "data/consolidated_summaries"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Ensured directory exists: {directory}")

def main():
    """Main function."""
    # Ensure directories exist
    ensure_directory_structure()
    
    # Find matching events
    matching_events = find_matching_events()
    if matching_events:
        output_file = create_comparison_file(matching_events)
        print(f"Successfully created comparison file: {output_file}")
    else:
        print("No matching events found, no comparison file created.")

if __name__ == "__main__":
    main()