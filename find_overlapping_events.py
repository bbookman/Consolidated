"""
Find Overlapping Events

This script searches through the database to identify events from Bee and Limitless
that overlap in time, and then generates consolidated summaries for these overlapping events.
"""
import os
import json
import logging
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, Bee_Conversation, Limitless_Lifelog
from database_handler import parse_date
from compare_and_consolidate import create_comparison_file

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_connection():
    """Set up the database connection."""
    engine = create_engine(os.environ.get('DATABASE_URL'))
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine)
    return Session()

def format_bee_event(conversation):
    """Format a Bee conversation from the database into a standard event format."""
    if not conversation:
        return None
    
    # Convert raw_data JSON string to Python dict
    raw_data = json.loads(conversation.raw_data)
    
    # Extract key take aways
    summary = conversation.summary or ""
    key_points = []
    
    if summary:
        lines = summary.split('\n')
        in_takeaways = False
        
        for line in lines:
            line = line.strip()
            if "Key Take Aways" in line or "Key Takeaways" in line:
                in_takeaways = True
            elif in_takeaways and line.startswith('*'):
                key_points.append(line)
    
    # Format the event
    return {
        "id": conversation.conversation_id,
        "summary": summary,
        "key_points": key_points,
        "start_time": conversation.created_at,
        "end_time": conversation.created_at + datetime.timedelta(minutes=15),  # Estimate end time
        "source": "Bee",
        "raw_data": raw_data
    }

def format_limitless_event(lifelog):
    """Format a Limitless lifelog from the database into a standard event format."""
    if not lifelog:
        return None
    
    # Convert raw_data JSON string to Python dict
    try:
        raw_data = json.loads(lifelog.raw_data)
        
        # Extract content items and high-level summary
        content_items = []
        high_level_summary = ""
        
        # Handle different possible formats of Limitless API data
        if 'content' in raw_data and isinstance(raw_data['content'], list):
            for item in raw_data['content']:
                if item.get('type') == 'heading1':
                    high_level_summary = item.get('text', '')
                content_items.append(item)
        elif 'contents' in raw_data and isinstance(raw_data['contents'], list):
            for item in raw_data['contents']:
                if item.get('type') == 'heading1':
                    high_level_summary = item.get('content', '')
                content_items.append(item)
        
        # Use title as fallback for summary
        if not high_level_summary and lifelog.title:
            high_level_summary = lifelog.title
        
        # Process timestamps - ensure both are non-None
        start_time = lifelog.created_at
        if not start_time:
            # If created_at is None, we can't process this event properly
            logger.warning(f"Skipping Limitless lifelog {lifelog.id} with None created_at timestamp")
            return None
            
        # Use updated_at if available, otherwise estimate end_time as start_time + 15 minutes
        end_time = None
        if lifelog.updated_at:
            end_time = lifelog.updated_at
        else:
            end_time = start_time + datetime.timedelta(minutes=15)
        
        # Format the event
        return {
            "id": lifelog.log_id,
            "summary": high_level_summary,
            "content": content_items,
            "start_time": start_time,
            "end_time": end_time,
            "source": "Limitless",
            "raw_data": raw_data
        }
    except Exception as e:
        logger.error(f"Error processing Limitless lifelog {lifelog.id}: {e}")
        return None

def find_overlapping_events(tolerance_minutes=5):
    """
    Find events from Bee and Limitless that overlap in time.
    
    Args:
        tolerance_minutes: Number of minutes tolerance for matching events
        
    Returns:
        List of matched event pairs (bee_event, limitless_event)
    """
    session = get_database_connection()
    
    try:
        # Get all Bee conversations
        bee_conversations = session.query(Bee_Conversation).all()
        logger.info(f"Found {len(bee_conversations)} Bee conversations")
        
        # Get all Limitless lifelogs
        limitless_lifelogs = session.query(Limitless_Lifelog).all()
        logger.info(f"Found {len(limitless_lifelogs)} Limitless lifelogs")
        
        # Format events
        bee_events = []
        for conv in bee_conversations:
            event = format_bee_event(conv)
            if event:
                bee_events.append(event)
        
        limitless_events = []
        for log in limitless_lifelogs:
            event = format_limitless_event(log)
            if event:
                limitless_events.append(event)
        
        logger.info(f"Formatted {len(bee_events)} Bee events and {len(limitless_events)} Limitless events")
        
        # Find overlapping events
        overlapping_pairs = []
        tolerance = datetime.timedelta(minutes=tolerance_minutes)
        
        for bee_event in bee_events:
            bee_start = bee_event["start_time"]
            bee_end = bee_event["end_time"]
            
            # Extend time range by tolerance
            extended_bee_start = bee_start - tolerance
            extended_bee_end = bee_end + tolerance
            
            for limitless_event in limitless_events:
                limitless_start = limitless_event["start_time"]
                limitless_end = limitless_event["end_time"]
                
                # Check if time ranges overlap
                if (extended_bee_start <= limitless_end and extended_bee_end >= limitless_start):
                    overlapping_pairs.append((bee_event, limitless_event))
        
        logger.info(f"Found {len(overlapping_pairs)} overlapping event pairs")
        return overlapping_pairs
    
    finally:
        session.close()

def generate_reports_for_overlapping_events():
    """
    Generate consolidated summary reports for all overlapping events.
    
    Returns:
        dict: Information about the reports that were generated:
            - count: Number of overlapping events found
            - report_files: List of report file paths
            - index_file: Path to the index file
    """
    # Ensure output directory exists
    consolidated_dir = os.path.join(os.getcwd(), "data", "consolidated_summaries")
    os.makedirs(consolidated_dir, exist_ok=True)
    
    # Find overlapping events
    overlapping_pairs = find_overlapping_events()
    
    if not overlapping_pairs:
        logger.info("No overlapping events found")
        return {"count": 0, "report_files": [], "index_file": None}
    
    # Generate reports for each pair
    report_files = []
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for i, (bee_event, limitless_event) in enumerate(overlapping_pairs):
        logger.info(f"Generating report for pair {i+1}/{len(overlapping_pairs)}")
        
        # Create a comparison file
        output_file = f"data/consolidated_summaries/overlapping_events_{timestamp}_{i+1}.txt"
        create_matched_comparison_file(bee_event, limitless_event, output_file)
        report_files.append(output_file)
    
    # Create an index file
    index_file = None
    if report_files:
        index_file = f"data/consolidated_summaries/overlapping_events_index_{timestamp}.txt"
        
        with open(index_file, 'w') as f:
            f.write("# Overlapping Events Summary\n\n")
            f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Found {len(report_files)} overlapping event pairs\n\n")
            
            for i, report_file in enumerate(report_files):
                bee_event, limitless_event = overlapping_pairs[i]
                start_time = min(bee_event["start_time"], limitless_event["start_time"])
                end_time = max(bee_event["end_time"], limitless_event["end_time"])
                
                start_str = start_time.strftime("%Y-%m-%d %H:%M")
                end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
                time_period = f"{start_str} to {end_str}"
                
                f.write(f"## Event Pair {i+1}\n")
                f.write(f"Time Period: {time_period}\n")
                f.write(f"Bee Summary: {bee_event['summary'][:100]}...\n")
                f.write(f"Limitless Summary: {limitless_event['summary'][:100]}...\n")
                f.write(f"Report: {os.path.basename(report_file)}\n\n")
        
        logger.info(f"Created index file: {index_file}")
    
    # Return information about the reports that were generated
    return {
        "count": len(overlapping_pairs), 
        "report_files": report_files, 
        "index_file": index_file
    }

def create_matched_comparison_file(bee_event, limitless_event, output_file):
    """Create a comparison file for a matched pair of events."""
    # Extract timestamps
    start_time = min(bee_event["start_time"], limitless_event["start_time"])
    end_time = max(bee_event["end_time"], limitless_event["end_time"])
    
    start_str = start_time.strftime("%Y-%m-%d %H:%M")
    end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
    time_period = f"{start_str} to {end_str}"
    
    # Extract key points from Bee
    bee_key_points = bee_event.get("key_points", [])
    bee_key_takeaways = "No key points found"
    
    if bee_key_points:
        bee_key_takeaways = "\n".join(bee_key_points)
    
    # Create the file content
    file_content = [
        f"# Comparison of Overlapping Events for Time Period: {time_period}\n",
        "## Section 1: Original Bee Summary\n",
        f"{bee_key_takeaways}\n",
        "## Section 2: Original Limitless Summary\n",
        f"Summary: {limitless_event.get('summary', 'No Summary')}\n",
        "## Section 3: Consolidated Summary\n"
    ]
    
    # Generate consolidated summary
    from compare_and_consolidate import generate_consolidated_summary, generate_differences_explanation
    
    consolidated_summary = generate_consolidated_summary([bee_event], [limitless_event])
    file_content.append(f"{consolidated_summary}\n")
    
    # Generate explanation
    differences_explanation = generate_differences_explanation([bee_event], [limitless_event])
    file_content.extend([
        "## Section 4: Consolidation Approach\n",
        f"{differences_explanation}\n"
    ])
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    logger.info(f"Created comparison file: {output_file}")
    return output_file

def main():
    """Main function."""
    logger.info("Starting overlapping events analysis")
    generate_reports_for_overlapping_events()
    logger.info("Completed overlapping events analysis")

if __name__ == "__main__":
    main()