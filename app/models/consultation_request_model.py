from app.extensions import mongo
from datetime import datetime, timezone
from bson.objectid import ObjectId


class ConsultationRequestModel:
    collection = mongo.db.consultation_requests

    @staticmethod
    def create_request(data):
        payload = {
            "user_id": data["user_id"],
            "owner_user_id": data["owner_user_id"],
            "chat_id": data["chat_id"],
            "summary": data.get("summary", ""),
            "severity": data.get("severity", "medium"),
            "status": data.get("status", "pending"),
            "assigned_doctor_id": data.get("assigned_doctor_id"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "closed_at": None,
        }
        result = ConsultationRequestModel.collection.insert_one(payload)
        return str(result.inserted_id)

    @staticmethod
    def _to_serializable(doc):
        if not doc:
            return None
        item = dict(doc)
        item["_id"] = str(item["_id"])
        return item

    @staticmethod
    def get_by_id(consultation_id):
        try:
            doc = ConsultationRequestModel.collection.find_one({"_id": ObjectId(consultation_id)})
            return ConsultationRequestModel._to_serializable(doc)
        except Exception:
            return None

    @staticmethod
    def get_pending():
        docs = ConsultationRequestModel.collection.find({"status": "pending"}).sort("created_at", -1)
        return [ConsultationRequestModel._to_serializable(d) for d in docs]

    @staticmethod
    def get_for_user(owner_user_id):
        docs = ConsultationRequestModel.collection.find({"owner_user_id": owner_user_id}).sort("created_at", -1)
        return [ConsultationRequestModel._to_serializable(d) for d in docs]

    @staticmethod
    def get_for_doctor(doctor_id):
        docs = ConsultationRequestModel.collection.find(
            {
                "assigned_doctor_id": doctor_id,
                "status": {"$ne": "closed"},
            }
        ).sort("updated_at", -1)
        return [ConsultationRequestModel._to_serializable(d) for d in docs]

    @staticmethod
    def find_open_by_chat(chat_id):
        doc = ConsultationRequestModel.collection.find_one(
            {
                "chat_id": chat_id,
                "status": {"$in": ["pending", "accepted", "active"]},
            }
        )
        return ConsultationRequestModel._to_serializable(doc)

    @staticmethod
    def accept_consultation(consultation_id, doctor_id):
        result = ConsultationRequestModel.collection.update_one(
            {
                "_id": ObjectId(consultation_id),
                "status": "pending",
            },
            {
                "$set": {
                    "status": "accepted",
                    "assigned_doctor_id": doctor_id,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    @staticmethod
    def set_active(consultation_id):
        result = ConsultationRequestModel.collection.update_one(
            {
                "_id": ObjectId(consultation_id),
                "status": {"$in": ["accepted", "active"]},
            },
            {
                "$set": {
                    "status": "active",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    @staticmethod
    def close_consultation(consultation_id):
        result = ConsultationRequestModel.collection.update_one(
            {
                "_id": ObjectId(consultation_id),
                "status": {"$in": ["pending", "accepted", "active"]},
            },
            {
                "$set": {
                    "status": "closed",
                    "closed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0
