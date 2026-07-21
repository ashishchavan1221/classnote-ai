import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger("app.db.mongo")

class MongoDBConnection:
    client: AsyncIOMotorClient = None
    db = None

    def connect(self):
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
            client_kwargs = {"serverSelectionTimeoutMS": 4000}
            try:
                import certifi
                client_kwargs["tlsCAFile"] = certifi.where()
            except Exception:
                client_kwargs["tlsAllowInvalidCertificates"] = True

            try:
                self.client = AsyncIOMotorClient(settings.MONGODB_URI, **client_kwargs)
            except Exception:
                self.client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=4000, tlsAllowInvalidCertificates=True)

            self.db = self.client[settings.MONGO_DB_NAME]
            logger.info("MongoDB client wrapper initialized.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

db_connection = MongoDBConnection()

# Helper function to get database
def get_db():
    if db_connection.db is None:
        # Re-try connecting
        db_connection.connect()
    return db_connection.db
