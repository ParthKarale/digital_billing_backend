import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 1. Open the secret .env file
load_dotenv()

# 2. Get the password line you just wrote
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 3. Connect to PostgreSQL (This is the HDMI cable)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Create a session (This keeps the connection open while the app runs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Set up the base for our Python tables
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()