"""
Test script that generates a consolidated summary from one Bee and one Limitless entry
pulled directly from the database.
"""
import os
import json
import datetime
import pytz
import sqlalchemy
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, Bee_Conversation, Limitless_Lifelog
from compare_and_consolidate import generate_consolidated_summary, generate_differences_explanation
from dateutil.parser import parse

def get_single_bee_conversation():
    """Get a single Bee conversation from the database."""
    # Set up database connection
    engine = create_engine(os.environ.get('DATABASE_URL', 'sqlite:///data.db'))
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get the most recent Bee conversation with a non-null summary
        conversation = session.query(Bee_Conversation)\
            .filter(Bee_Conversation.summary.isnot(None))\
            .order_by(Bee_Conversation.created_at.desc())\
            .first()
        
        if conversation:
            # Convert the raw_data JSON string back to a Python dictionary
            raw_data = json.loads(conversation.raw_data)
            
            # Extract timestamp and format the data
            bee_item = {
                "summary": conversation.summary,
                "start_time": conversation.created_at,
                "end_time": conversation.created_at + datetime.timedelta(minutes=15),  # Assuming 15 min duration
                "source": "Bee"
            }
            
            print(f"Found Bee conversation from {bee_item['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            return bee_item
        else:
            print("No Bee conversation with summary found in database.")
            return None
    finally:
        session.close()

def get_single_limitless_lifelog():
    """Get a single Limitless lifelog from the database."""
    # Set up database connection
    engine = create_engine(os.environ.get('DATABASE_URL', 'sqlite:///data.db'))
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get the most recent Limitless lifelog
        lifelog = session.query(Limitless_Lifelog)\
            .order_by(Limitless_Lifelog.created_at.desc())\
            .first()
        
        if lifelog:
            try:
                # Convert the raw_data JSON string back to a Python dictionary
                raw_data = json.loads(lifelog.raw_data)
                
                # Extract content from raw_data
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
                
                # Use the title if no high-level summary was found
                if not high_level_summary:
                    if 'title' in raw_data:
                        high_level_summary = raw_data['title']
                    else:
                        # Try to extract from log_type
                        high_level_summary = f"Limitless {lifelog.log_type or 'log'}"
                
                # Extract timestamp and format the data
                limitless_item = {
                    "summary": high_level_summary,
                    "content": content_items,
                    "start_time": lifelog.created_at,
                    "end_time": lifelog.updated_at or lifelog.created_at,
                    "source": "Limitless"
                }
                
                print(f"Found Limitless lifelog from {limitless_item['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                return limitless_item
            except Exception as e:
                print(f"Error processing Limitless lifelog: {e}")
                print(f"Raw data sample: {lifelog.raw_data[:100]}...")
                return None
        else:
            print("No Limitless lifelog found in database.")
            return None
    finally:
        session.close()

def create_comparison_file(bee_item, limitless_item):
    """Create a text file with the comparison and consolidated summary."""
    if not bee_item and not limitless_item:
        print("No data found for comparison.")
        return
    
    # Ensure output directory exists
    consolidated_dir = os.path.join(os.getcwd(), "data", "consolidated_summaries")
    os.makedirs(consolidated_dir, exist_ok=True)
    
    # Format the time period
    if bee_item and limitless_item:
        start_time = min(bee_item["start_time"], limitless_item["start_time"])
        end_time = max(bee_item["end_time"], limitless_item["end_time"])
        time_label = "Combined Data"
    elif bee_item:
        start_time = bee_item["start_time"]
        end_time = bee_item["end_time"]
        time_label = "Bee Data Only"
    else:  # limitless_item only
        start_time = limitless_item["start_time"]
        end_time = limitless_item["end_time"]
        time_label = "Limitless Data Only"
    
    start_str = start_time.strftime("%Y-%m-%d %H:%M")
    end_str = end_time.strftime("%H:%M") if start_time.date() == end_time.date() else end_time.strftime("%Y-%m-%d %H:%M")
    time_period = f"{start_str} to {end_str}"
    
    # Generate consolidated summary
    bee_items = [bee_item] if bee_item else []
    limitless_items = [limitless_item] if limitless_item else []
    consolidated_summary = generate_consolidated_summary(bee_items, limitless_items)
    
    # Generate explanation of differences
    differences_explanation = generate_differences_explanation(bee_items, limitless_items)
    
    # Extract only the bullet points from the "Key Take Aways" section, not the heading itself
    bee_key_points = []
    bee_key_takeaways = "No key points found"  # Initialize with default value
    
    if bee_item and bee_item.get('summary'):
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
        f"# Comparison of Database Records ({time_label}) for Time Period: {time_period}\n",
        "## Section 1: Original Bee Summary\n"
    ]
    
    if bee_item:
        file_content.append(f"{bee_key_takeaways}\n")
    else:
        file_content.append("No Bee data available from database.\n")
    
    file_content.append("## Section 2: Original Limitless Summary\n")
    
    if limitless_item:
        file_content.append(f"Summary: {limitless_item.get('summary', 'No Summary')}\n")
    else:
        file_content.append("No Limitless data available from database.\n")
    
    file_content.extend([
        "## Section 3: Consolidated Summary\n",
        f"{consolidated_summary}\n",
        "## Section 4: Consolidation Approach\n",
        f"{differences_explanation}\n"
    ])
    
    # Create output file
    output_file = f"data/consolidated_summaries/db_test_comparison_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(file_content))
    
    print(f"Database comparison file created: {output_file}")
    return output_file

def main():
    """Main function to pull data from DB and generate comparison."""
    print("Retrieving one Bee conversation and one Limitless lifelog from the database...")
    
    # Get data from database
    bee_item = get_single_bee_conversation()
    limitless_item = get_single_limitless_lifelog()
    
    # Create comparison file
    if bee_item or limitless_item:
        output_file = create_comparison_file(bee_item, limitless_item)
        print(f"Successfully created database comparison file: {output_file}")
    else:
        print("No data found in database, no comparison file created.")

if __name__ == "__main__":
    main()