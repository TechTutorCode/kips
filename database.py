from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base


DATABASE_URL = "postgresql://postgres:deno0707@localhost/kips"
engine = create_engine(DATABASE_URL)
Base = declarative_base()