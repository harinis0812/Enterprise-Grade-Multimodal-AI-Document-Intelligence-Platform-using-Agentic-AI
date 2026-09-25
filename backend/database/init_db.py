from backend.database.database import Base, engine
from backend.database.models import Document


def init_database():
    Base.metadata.create_all(bind=engine)
