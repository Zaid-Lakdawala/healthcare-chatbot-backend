from app.extensions import mongo
from datetime import datetime, timezone
from bson.objectid import ObjectId


class UserModel:
    collection = mongo.db.users

    @staticmethod
    def create_user(data):
        data["status"] = "active"
        data["role"] = "user"
        data["created_at"] = datetime.now(timezone.utc)
        data["updated_at"] = datetime.now(timezone.utc)
        return UserModel.collection.insert_one(data)

    @staticmethod
    def get_all_users(filters=None, page=1, limit=10, search=None):
        query = filters or {}
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}}
            ]

        skip = (page - 1) * limit
        cursor = UserModel.collection.find(query).skip(skip).limit(limit)
        total = UserModel.collection.count_documents(query)

        # Convert ObjectId to string
        users = []
        for user in cursor:
            user["_id"] = str(user["_id"])
            users.append(user)

        return users, total

    @staticmethod
    def find_by_email(email):
        return UserModel.collection.find_one({"email": email})

    @staticmethod
    def find_by_id(user_id):
        try:
            user = UserModel.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except:
            return None

    @staticmethod
    def find_by_email_with_password(email):
        return UserModel.collection.find_one({"email": email, "status": "active"})

    @staticmethod
    def get_user_count():
        """Get total count of users"""
        try:
            return UserModel.collection.count_documents({"role": "user"})
        except Exception as e:
            print(f"Error getting user count: {e}")
            return 0


    @staticmethod
    def update_user(user_id, data):
        try:
            result = UserModel.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": data}
            )
            return result.modified_count > 0
        except:
            return False

    @staticmethod
    def update_status(user_id, status):
        try:
            result = UserModel.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except:
            return False

    @staticmethod
    def update_questionnaire(user_id, questionnaire_data):
        """Update user's questionnaire data"""
        try:
            return UserModel.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"questionnaire": questionnaire_data, "updated_at": datetime.now(timezone.utc)}}
            )
        except Exception as e:
            print(f"Error updating questionnaire: {e}")
            return None
