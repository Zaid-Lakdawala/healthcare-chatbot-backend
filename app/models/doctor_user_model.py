from app.models.user_model import UserModel


class DoctorUserModel:
    @staticmethod
    def find_doctor_by_id(user_id):
        user = UserModel.find_by_id(user_id)
        if not user:
            return None
        if user.get("role") != "doctor":
            return None
        return user

    @staticmethod
    def get_all_doctors():
        users, _ = UserModel.get_all_users(filters={"role": "doctor"}, page=1, limit=1000)
        return users
