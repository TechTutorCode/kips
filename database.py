# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base


# DATABASE_URL = "postgresql://postgres:deno0707@localhost/kips"
# engine = create_engine(DATABASE_URL)
# Base = declarative_base()

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

# SQLite database URL format
DATABASE_URL = "sqlite:///kips.db"  # The database file will be named kips.db in the current directory
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()