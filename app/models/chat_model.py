from app.extensions import mongo
from datetime import datetime, timezone
from bson.objectid import ObjectId
import uuid


class ChatModel:
    collection = mongo.db.conversations

    @staticmethod
    def create_conversation(user_id, title="New Consultation"):
        data = {
            "user_id": user_id,
            "title": title,
            "messages": [],
            "ended": False,
            "summary": None,
            "summary_created_at": None,
            "escalation_pending_consent": False,
            "escalation_suggested_severity": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        result = ChatModel.collection.insert_one(data)
        return str(result.inserted_id)

    @staticmethod
    def append_message(conversation_id, role, content, message_id=None):
        try:
            if message_id is None:
                message_id = str(uuid.uuid4())
            
            doc = {
                "_id": message_id,   # 🔥 UNIQUE MESSAGE ID
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc),
            }

            mongo.db.conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$push": {"messages": doc},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )
            return str(doc["_id"])   # 🔥 return message id if needed
        except Exception as e:
            print("append_message ERROR:", e)
            return False

    @staticmethod
    def get_conversation(conversation_id):
        """Get a conversation by ID"""
        try:
            conversation = ChatModel.collection.find_one({"_id": ObjectId(conversation_id)})
            if conversation:
                conversation["_id"] = str(conversation["_id"])
            return conversation
        except Exception as e:
            print("get_conversation ERROR:", e)
            return None

    @staticmethod
    def get_user_conversations(user_id):
        """Get all conversations for a user, sorted by most recent"""
        try:
            conversations = list(ChatModel.collection.find(
                {"user_id": user_id}
            ).sort("updated_at", -1))
            
            # Convert ObjectId to string for JSON serialization
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
            
            return conversations
        except Exception as e:
            print("get_user_conversations ERROR:", e)
            return []

    @staticmethod
    def get_total_conversations_count():
        """Get total count of all conversations"""
        try:
            return ChatModel.collection.count_documents({})
        except Exception as e:
            print(f"Error getting conversations count: {e}")
            return 0

    @staticmethod
    def get_all_conversations():
        """Get all conversations (for admin)"""
        try:
            conversations = list(ChatModel.collection.find({}).sort("updated_at", -1))
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
            return conversations
        except Exception as e:
            print(f"Error getting all conversations: {e}")
            return []
    
    @staticmethod
    def get_active_conversation(user_id):
        """Get the active conversation for a user (if any)"""
        try:
            conversation = ChatModel.collection.find_one({
                "user_id": user_id,
                "ended": False
            })
            if conversation:
                conversation["_id"] = str(conversation["_id"])
            return conversation
        except Exception as e:
            print(f"Error getting active conversation: {e}")
            return None
    
    @staticmethod
    def end_conversation(conversation_id):
        """End a conversation (mark as ended)"""
        try:
            result = ChatModel.collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "ended": True,
                        "ended_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error ending conversation: {e}")
            return False

    @staticmethod
    def get_conversation_summary(conversation_id):
        """Get summary fields for a conversation"""
        try:
            conversation = ChatModel.collection.find_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "user_id": 1,
                    "summary": 1,
                    "summary_created_at": 1,
                },
            )

            if conversation:
                conversation["_id"] = str(conversation["_id"])

            return conversation
        except Exception as e:
            print(f"Error getting conversation summary: {e}")
            return None

    @staticmethod
    def set_conversation_summary(conversation_id, summary_text):
        """Store summary and timestamp for a conversation"""
        try:
            now = datetime.now(timezone.utc)
            result = ChatModel.collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "summary": summary_text,
                        "summary_created_at": now,
                        "updated_at": now,
                    }
                },
            )
            return result.matched_count > 0
        except Exception as e:
            print(f"Error setting conversation summary: {e}")
            return False

    @staticmethod
    def set_escalation_state(conversation_id, pending, severity=None):
        try:
            result = ChatModel.collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$set": {
                        "escalation_pending_consent": bool(pending),
                        "escalation_suggested_severity": severity if pending else None,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.matched_count > 0
        except Exception as e:
            print(f"Error setting escalation state: {e}")
            return False
