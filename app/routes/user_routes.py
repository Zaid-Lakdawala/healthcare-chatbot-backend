"""
User Routes
Combined routes and business logic for user management
"""
from flask import Blueprint, request, jsonify
from app.models.user_model import UserModel
from app.utils.security import hash_password, verify_password
from datetime import datetime, time, date, timezone
from app.utils.auth import create_token, token_required
import re

user_bp = Blueprint("user_bp", __name__)


@user_bp.route("/login", methods=["POST"])
def login():
    
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required"}), 400

    user = UserModel.find_by_email_with_password(email)

    if not user:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    if not verify_password(password, user["password"]):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    # Create JWT
    token = create_token({
        "_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"] or "user",
    })

    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token
    }), 200


@user_bp.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    
    if not data.get("name") or not data.get("email") or not data.get("password"):
        return jsonify({"success": False, "message": "Name, email, and password required"}), 400
    
    name = data.get("name").strip()
    email = data.get("email").strip().lower()
    password = data.get("password")
        
    if UserModel.find_by_email(email):
        return jsonify({"success": False, "message": "User already exists"}), 409

    user_data = {
        "name": name,
        "email": email,
        "password": hash_password(password),
        "role": "user"
    }
    
    if data.get("gender") in ["male", "female"]:
        user_data["gender"] = data["gender"]
    
    if data.get("dob"):
        try:
            dob_date = datetime.strptime(data["dob"], "%Y-%m-%d").date()
            user_data["dob"] = datetime.combine(dob_date, time())
        except:
            pass

    result = UserModel.create_user(user_data)

    return jsonify({
        "success": True,
        "message": "User created successfully",
        "data": {"_id": str(result.inserted_id)}
    }), 201


@user_bp.route("/questionnaire", methods=["POST"])
@token_required
def submit_questionnaire(decoded_user):
    
    data = request.json or {}
    
    required_fields = ["age", "gender", "medical_history", "medications", "allergies", "height", "weight"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Missing field: {field}"}), 400
    
    # Validate gender
    if data["gender"] not in ["male", "female"]:
        return jsonify({"success": False, "message": "Gender must be male or female"}), 400

    user_id = decoded_user.get("_id")
    questionnaire_data = {
        "age": data["age"],
        "gender": data["gender"],
        "medical_history": data["medical_history"],
        "medications": data["medications"],
        "allergies": data["allergies"],
        "height": data["height"],
        "weight": data["weight"],
        "submitted_at": datetime.now(timezone.utc)
    }
    
    result = UserModel.update_questionnaire(user_id, questionnaire_data)
    
    if result.modified_count > 0 or result.matched_count > 0:
        return jsonify({
            "success": True,
            "message": "Questionnaire submitted successfully",
            "data": questionnaire_data
        }), 200
    
    return jsonify({"success": False, "message": "Failed to submit questionnaire"}), 500


@user_bp.route("/questionnaire/status", methods=["GET"])
@token_required
def get_questionnaire_status(decoded_user):
   
    user_id = decoded_user.get("_id")
    user = UserModel.find_by_id(user_id)
    
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    questionnaire = user.get("questionnaire")
    has_submitted = questionnaire is not None and questionnaire != {}
    
    return jsonify({
        "success": True,
        "hasSubmitted": has_submitted,
        "data": questionnaire if has_submitted else None
    }), 200
