from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import os
from datetime import datetime

# Get database URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create declarative base
Base = declarative_base()

class Bee_Conversation(Base):
    __tablename__ = 'bee_conversations'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, unique=True)  # External ID from Bee API
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime)
    address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    def __repr__(self):
        return f"<Bee_Conversation(id={self.id}, created_at={self.created_at})>"

class Bee_Fact(Base):
    __tablename__ = 'bee_facts'
    
    id = Column(Integer, primary_key=True)
    fact_id = Column(String, nullable=True)  # External ID from Bee API if available
    text = Column(Text, nullable=False)
    created_at = Column(DateTime)
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    # Create a unique constraint on the text field to prevent duplicates
    __table_args__ = (UniqueConstraint('text', name='uq_bee_fact_text'),)
    
    def __repr__(self):
        return f"<Bee_Fact(id={self.id}, text={self.text[:30]}...)>"

class Bee_Todo(Base):
    __tablename__ = 'bee_todos'
    
    id = Column(Integer, primary_key=True)
    todo_id = Column(String, unique=True)  # External ID from Bee API
    task = Column(Text, nullable=False)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime)
    raw_data = Column(Text)  # Store the raw JSON for reference
    
    def __repr__(self):
        return f"<Bee_Todo(id={self.id}, task={self.task[:30]}..., completed={self.completed})>"

# Create all tables in the database
Base.metadata.create_all(engine)