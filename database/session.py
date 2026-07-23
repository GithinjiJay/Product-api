import os
from sqlmodel import create_engine, Session, SQLModel
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"DEBUG: Attempting to connect to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, echo=True)

# Ensure this function is defined at the same indentation level as the other functions
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session