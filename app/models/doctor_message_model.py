from app.extensions import mongo
from datetime import datetime, timezone
from bson.objectid import ObjectId


class DoctorMessageModel:
    collection = mongo.db.doctor_messages

    @staticmethod
    def add_message(consultation_id, sender, message):
        payload = {
            "consultation_id": consultation_id,
            "sender": sender,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
        }
        result = DoctorMessageModel.collection.insert_one(payload)
        return str(result.inserted_id)

    @staticmethod
    def get_messages(consultation_id):
        messages = list(
            DoctorMessageModel.collection.find({"consultation_id": consultation_id}).sort("timestamp", 1)
        )
        for msg in messages:
            msg["_id"] = str(msg["_id"])
        return messages
