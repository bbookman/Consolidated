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
    - source: "Limitless"
    """
    contents = []
    
    for log in lifelogs_data.get("lifelogs", []):
        start_time = normalize_timestamp(log.get("startTime"))
        end_time = normalize_timestamp(log.get("endTime"))
        
        if start_time:  # Only include if we have a valid start time
            # Extract content items, focusing on blockquote types which usually contain conversation text
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
    - consolidated_summary: text combining both sources
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
        
        # Build consolidated summary
        summary_parts = []
        sources = []
        
        if bee_items:
            sources.append("Bee")
            for item in bee_items:
                summary_parts.append(f"**Bee Summary:**\n{item['summary']}")
        
        if limitless_items:
            sources.append("Limitless")
            for item in limitless_items:
                title = f"**Limitless Recording: {item['title']}**" if item.get("title") else "**Limitless Recording**"
                content = format_lifelog_content(item["content"])
                summary_parts.append(f"{title}\n{content}")
        
        consolidated_summaries.append({
            "time_period": time_period,
            "consolidated_summary": "\n\n---\n\n".join(summary_parts),
            "sources": sources
        })
    
    return consolidated_summaries

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
    
    # Output consolidated summaries
    output_file = f"consolidated_summaries_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    print(f"Saving consolidated summaries to: {output_file}")
    
    with open(output_file, 'w') as f:
        json.dump({
            "consolidated_summaries": consolidated_summaries
        }, f, indent=2, default=str)
    
    # Also output a markdown version for better readability
    md_output_file = f"consolidated_summaries_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
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