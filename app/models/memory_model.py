from datetime import datetime, timezone
from app.extensions import mongo


class MemoryModel:
    collection = mongo.db.user_memory

    @staticmethod
    def get_summary(user_id: str) -> str:
        doc = MemoryModel.collection.find_one({"user_id": user_id})
        if not doc:
            return ""
        return doc.get("summary", "") or ""

    @staticmethod
    def save_summary(user_id: str, summary: str):
        return MemoryModel.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "summary": summary,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
    )
