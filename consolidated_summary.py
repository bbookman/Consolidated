"""
Consolidated Summary Generator

This script generates a consolidated summary from Bee conversations and Limitless lifelogs
by matching them based on timestamps and extracting key information from both sources.
"""

import json
import datetime
import os
from dateutil.parser import parse
import pytz
from collections import defaultdict

def load_json_file(file_path):
    """Load and parse JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def get_latest_file(directory, prefix):
    """Get the most recent file with the specified prefix in the directory."""
    files = [f for f in os.listdir(directory) if f.startswith(prefix)]
    if not files:
        return None
    files.sort(reverse=True)  # Sort by filename (which includes timestamp)
    return os.path.join(directory, files[0])

def normalize_timestamp(timestamp_str):
    """Normalize timestamp to UTC ISO format."""
    if not timestamp_str:
        return None
    
    dt = parse(timestamp_str)
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=pytz.UTC)
    else:
        # Convert to UTC
        dt = dt.astimezone(pytz.UTC)
    
    return dt

def extract_bee_summaries(conversations_data):
    """
    Extract summaries from Bee conversations with timestamps.
    
    Returns a list of dicts with:
    - start_time: normalized timestamp
    - end_time: normalized timestamp
    - summary: the conversation summary text
    - source: "Bee"
    """
    summaries = []
    
    for conv in conversations_data.get("conversations", []):
        if conv.get("summary"):
            start_time = normalize_timestamp(conv.get("start_time"))
            end_time = normalize_timestamp(conv.get("end_time"))
            
            if start_time:  # Only include if we have a valid start time
                summaries.append({
                    "start_time": start_time,
                    "end_time": end_time or start_time,  # Use start_time as fallback
                    "summary": conv.get("summary"),
                    "source": "Bee"
                })
    
    return summaries

def extract_lifelog_content(lifelogs_data):
    """
    Extract content from Limitless lifelogs with timestamps.
    
    Returns a list of dicts with:
    - start_time: normalized timestamp
    - end_time: normalized timestamp
    - title: the lifelog title
    - content: extracted content items
    - summary: high-level summary (from heading1)
    - source: "Limitless"
    """
    contents = []
    
    for log in lifelogs_data.get("lifelogs", []):
        start_time = normalize_timestamp(log.get("startTime"))
        end_time = normalize_timestamp(log.get("endTime"))
        
        if start_time:  # Only include if we have a valid start time
            # First, look for heading1 which contains the high-level summary
            high_level_summary = ""
            for item in log.get("contents", []):
                if item.get("type") == "heading1":
                    high_level_summary = item.get("content", "")
                    break
            
            # Extract all content items for detailed view
            content_items = []
            for item in log.get("contents", []):
                if item.get("type") in ["heading1", "heading2", "blockquote"]:
                    content_items.append({
                        "type": item.get("type"),
                        "content": item.get("content"),
                        "speaker": item.get("speakerName", "") if "speakerName" in item else ""
                    })
            
            contents.append({
                "start_time": start_time,
                "end_time": end_time or start_time,  # Use start_time as fallback
                "title": log.get("title", ""),
                "summary": high_level_summary,  # Add high-level summary separately
                "content": content_items,
                "source": "Limitless"
            })
    
    return contents

def do_time_periods_overlap(period1, period2, tolerance_minutes=5):
    """
    Check if two time periods overlap, with a tolerance window.
    
    Args:
        period1: Dict with start_time and end_time
        period2: Dict with start_time and end_time
        tolerance_minutes: Minutes to extend periods for matching
    
    Returns:
        Boolean indicating if periods overlap
    """
    # Add tolerance to both periods
    tolerance = datetime.timedelta(minutes=tolerance_minutes)
    
    p1_start = period1["start_time"] - tolerance
    p1_end = period1["end_time"] + tolerance if period1["end_time"] else p1_start + tolerance
    
    p2_start = period2["start_time"] - tolerance
    p2_end = period2["end_time"] + tolerance if period2["end_time"] else p2_start + tolerance
    
    # Check for overlap
    return (p1_start <= p2_end) and (p2_start <= p1_end)

def match_events_by_time(bee_summaries, limitless_contents):
    """
    Match Bee summaries with Limitless contents based on overlapping time periods.
    
    Returns a list of matched event groups, each containing one or more items from either source.
    """
    all_events = bee_summaries + limitless_contents
    all_events.sort(key=lambda x: x["start_time"])  # Sort by start time
    
    # Group overlapping events
    event_groups = []
    current_group = []
    
    for event in all_events:
        if not current_group:
            current_group.append(event)
        else:
            # Check if current event overlaps with any event in the current group
            overlaps = any(do_time_periods_overlap(event, existing) for existing in current_group)
            
            if overlaps:
                current_group.append(event)
            else:
                event_groups.append(current_group)
                current_group = [event]
    
    # Add the last group if not empty
    if current_group:
        event_groups.append(current_group)
    
    return event_groups

def format_lifelog_content(content_items):
    """Format Limitless content items into readable text."""
    formatted = []
    
    for item in content_items:
        if item["type"] == "heading1":
            formatted.append(f"# {item['content']}")
        elif item["type"] == "heading2":
            formatted.append(f"## {item['content']}")
        elif item["type"] == "blockquote":
            speaker = f"{item['speaker']}: " if item.get("speaker") else ""
            formatted.append(f"> {speaker}{item['content']}")
    
    return "\n".join(formatted)

def generate_consolidated_summary(event_groups):
    """
    Generate a consolidated summary from matched event groups.
    
    Returns a list of summary entries, each containing:
    - time_period: formatted time range
    - source_summaries: original summaries from each source
    - consolidated_summary: an integrated summary combining both sources
    - sources: list of source types included
    """
    consolidated_summaries = []
    
    for group in event_groups:
        start_time = min(event["start_time"] for event in group)
        end_times = [event["end_time"] for event in group if event["end_time"]]
        end_time = max(end_times) if end_times else start_time
        
        # Format time period
        start_str = start_time.strftime("%Y-%m-%d %H:%M")
        end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
        time_period = f"{start_str} to {end_str}"
        
        # Separate by source
        bee_items = [e for e in group if e["source"] == "Bee"]
        limitless_items = [e for e in group if e["source"] == "Limitless"]
        
        # Build source-specific summaries
        source_summaries = []
        integrated_summary_parts = []
        sources = []
        
        # Process Bee summaries
        if bee_items:
            sources.append("Bee")
            for item in bee_items:
                source_summaries.append({
                    "source": "Bee",
                    "summary": item['summary']
                })
                integrated_summary_parts.append(f"**Bee Summary:**\n{item['summary']}")
        
        # Process Limitless content
        if limitless_items:
            sources.append("Limitless")
            for item in limitless_items:
                # Format Limitless content
                title = item.get("title", "")
                high_level_summary = item.get("summary", "")
                content = format_lifelog_content(item["content"])
                
                source_summaries.append({
                    "source": "Limitless",
                    "title": title,
                    "summary": high_level_summary,
                    "content_details": content
                })
                
                display_title = f"**Limitless Recording: {title}**" if title else "**Limitless Recording**"
                integrated_summary_parts.append(f"{display_title}\n{content}")
        
        # If only one source has data, use just that source directly 
        # Otherwise, generate a truly integrated summary when both sources are present
        if len(sources) == 1:
            # Simplified format for single source
            if "Bee" in sources:
                integrated_summary = "**Key information (from Bee):**\n\n"
                for item in bee_items:
                    if 'summary' in item and item['summary']:
                        integrated_summary += item['summary']
            else:  # Limitless
                integrated_summary = "**Key information (from Limitless):**\n\n"
                for item in limitless_items:
                    high_level_summary = item.get("summary", "")
                    if high_level_summary:
                        integrated_summary += f"{high_level_summary}\n\n"
                    content = format_lifelog_content(item["content"])
                    if content:
                        integrated_summary += content
                        
            # Replace the integrated parts with the simple format
            integrated_summary_parts = [integrated_summary]
        elif len(sources) > 1:
            # Extract key topics and themes from both sources
            combined_topics = extract_combined_topics(bee_items, limitless_items)
            integrated_section = generate_integrated_insight(combined_topics, time_period)
            
            # Add the integrated section at the beginning
            if integrated_section:
                integrated_summary_parts.insert(0, integrated_section)
        
        consolidated_summaries.append({
            "time_period": time_period,
            "source_summaries": source_summaries,
            "consolidated_summary": "\n\n---\n\n".join(integrated_summary_parts),
            "sources": sources
        })
    
    return consolidated_summaries

def extract_combined_topics(bee_items, limitless_items):
    """
    Extract key topics and themes from both Bee and Limitless items.
    This is used to generate a truly integrated summary.
    
    Args:
        bee_items: List of items from Bee API
        limitless_items: List of items from Limitless API
        
    Returns:
        Dictionary of combined topics
    """
    topics = {
        "people": set(),
        "main_themes": set(),
        "activities": set(),
        "locations": set()
    }
    
    # Extract from Bee summaries
    for item in bee_items:
        summary = item.get("summary", "")
        # Simple keyword extraction - in a real implementation,
        # this would use NLP for more sophisticated extraction
        for line in summary.split("\n"):
            if "Key Take Aways" in line or "Key Takeaways" in line:
                # Extract topics from key takeaways
                for takeaway in summary.split("*")[1:]:  # Split by bullet points
                    topics["main_themes"].add(takeaway.strip())
    
    # Extract from Limitless content
    for item in limitless_items:
        summary = item.get("summary", "")
        topics["main_themes"].add(summary)
        
        # Extract speakers from content
        for content_item in item.get("content", []):
            speaker = content_item.get("speaker", "")
            if speaker and speaker not in ["You", "Unknown Speaker"]:
                topics["people"].add(speaker)
    
    return topics

def generate_integrated_insight(topics, time_period):
    """
    Generate an integrated insight section that combines information from both sources.
    
    Args:
        topics: Dictionary of combined topics extracted from both sources
        time_period: The time period of the event
        
    Returns:
        Formatted integrated insight text
    """
    if not topics["main_themes"]:
        return ""
    
    # Create a coherent integrated summary
    insight = "**Integrated Summary:**\n\n"
    
    # Add themes
    if topics["main_themes"]:
        themes = list(topics["main_themes"])
        if len(themes) == 1:
            insight += f"This event primarily focused on {themes[0]}.\n\n"
        else:
            insight += "This event covered multiple topics including:\n"
            for theme in themes:
                if theme.strip():
                    insight += f"- {theme.strip()}\n"
            insight += "\n"
    
    # Add people if present
    if topics["people"]:
        people = list(topics["people"])
        if len(people) == 1:
            insight += f"The conversation involved {people[0]}.\n"
        elif len(people) > 1:
            insight += f"The conversation involved multiple people including {', '.join(people[:-1])} and {people[-1]}.\n"
    
    # Add summary statement
    insight += "\nThis summary combines data from both Bee AI and Limitless recordings captured during this time period.\n"
    
    return insight

def main():
    """Main function to generate consolidated summaries."""
    # Load the latest data files
    bee_conversations_file = get_latest_file("data/bee", "conversations_")
    limitless_lifelogs_file = get_latest_file("data/limitless", "lifelogs_")
    
    if not bee_conversations_file:
        print("Error: No Bee conversations file found.")
        return
    
    if not limitless_lifelogs_file:
        print("Error: No Limitless lifelogs file found.")
        return
    
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
    print(f"Matched events into {len(event_groups)} time-based groups")
    
    # Generate consolidated summaries
    consolidated_summaries = generate_consolidated_summary(event_groups)
    
    # Ensure data/consolidated_summaries directory exists
    consolidated_dir = os.path.join(os.getcwd(), "data", "consolidated_summaries")
    os.makedirs(consolidated_dir, exist_ok=True)
    
    # Output consolidated summaries to the proper directory
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(consolidated_dir, f"consolidated_{timestamp}.json")
    print(f"Saving consolidated summaries to: {output_file}")
    
    with open(output_file, 'w') as f:
        json.dump({
            "consolidated_summaries": consolidated_summaries
        }, f, indent=2, default=str)
    
    # Also output a markdown version for better readability
    md_output_file = os.path.join(consolidated_dir, f"consolidated_{timestamp}.md")
    
    with open(md_output_file, 'w') as f:
        f.write("# Consolidated Summaries\n\n")
        for i, summary in enumerate(consolidated_summaries, 1):
            f.write(f"## Event {i}: {summary['time_period']}\n")
            f.write(f"**Sources:** {', '.join(summary['sources'])}\n\n")
            f.write(f"{summary['consolidated_summary']}\n\n")
            f.write("---\n\n")
    
    print(f"Also saved readable version to: {md_output_file}")
    print("Done!")

if __name__ == "__main__":
    main()