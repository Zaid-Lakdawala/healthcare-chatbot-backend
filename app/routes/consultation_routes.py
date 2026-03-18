from flask import Blueprint, request, jsonify
from hashlib import sha256
from app.models.chat_model import ChatModel
from app.models.consultation_request_model import ConsultationRequestModel
from app.models.doctor_message_model import DoctorMessageModel
from app.models.doctor_user_model import DoctorUserModel
from app.utils.auth import token_required

consultation_bp = Blueprint("consultation_bp", __name__)


def anonymise_user_id(user_id):
    return f"anon_{sha256(user_id.encode()).hexdigest()[:12]}"


def _build_summary_for_request(conversation):
    existing_summary = (conversation.get("summary") or "").strip()
    if existing_summary:
        return existing_summary

    messages = conversation.get("messages", [])
    transcript = []
    for msg in messages:
        role = msg.get("role")
        if role not in ["user", "assistant"]:
            continue
        prefix = "Patient" if role == "user" else "Assistant"
        transcript.append(f"{prefix}: {msg.get('content', '')}")

    if not transcript:
        return "No clinical details were captured in the chat history."

    return "\n".join(transcript[-12:])


@consultation_bp.route("/create", methods=["POST"])
@token_required
def create_consultation(current_user):
    user = current_user or {}
    user_id = user.get("user_id")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    data = request.json or {}
    chat_id = (data.get("chat_id") or "").strip()
    severity = (data.get("severity") or "high").strip().lower()

    if not chat_id:
        return {"success": False, "message": "chat_id is required"}, 400

    if severity not in ["low", "medium", "high"]:
        severity = "medium"

    conversation = ChatModel.get_conversation(chat_id)
    if not conversation:
        return {"success": False, "message": "Conversation not found"}, 404

    if conversation.get("user_id") != user_id:
        return {"success": False, "message": "Unauthorized"}, 403

    existing_open = ConsultationRequestModel.find_open_by_chat(chat_id)
    if existing_open:
        return {
            "success": True,
            "message": "Open consultation request already exists",
            "consultation": {
                "id": existing_open.get("_id"),
                "chat_id": existing_open.get("chat_id"),
                "summary": existing_open.get("summary"),
                "severity": existing_open.get("severity"),
                "status": existing_open.get("status"),
                "assigned_doctor_id": existing_open.get("assigned_doctor_id"),
                "created_at": existing_open.get("created_at"),
            },
        }, 200

    request_summary = (data.get("summary") or "").strip() or _build_summary_for_request(conversation)

    consultation_id = ConsultationRequestModel.create_request(
        {
            "user_id": anonymise_user_id(user_id),
            "owner_user_id": user_id,
            "chat_id": chat_id,
            "summary": request_summary,
            "severity": severity,
            "status": "pending",
            "assigned_doctor_id": None,
        }
    )

    consultation = ConsultationRequestModel.get_by_id(consultation_id)

    return {
        "success": True,
        "message": "Consultation request created",
        "consultation": {
            "id": consultation.get("_id"),
            "chat_id": consultation.get("chat_id"),
            "summary": consultation.get("summary"),
            "severity": consultation.get("severity"),
            "status": consultation.get("status"),
            "assigned_doctor_id": consultation.get("assigned_doctor_id"),
            "created_at": consultation.get("created_at"),
        },
    }, 201


@consultation_bp.route("/pending", methods=["GET"])
@token_required
def get_pending_consultations(current_user):
    user = current_user or {}
    user_id = user.get("user_id")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    doctor = DoctorUserModel.find_doctor_by_id(user_id)
    if not doctor:
        return {"success": False, "message": "Unauthorized - doctor access required"}, 403

    pending = ConsultationRequestModel.get_pending()

    items = [
        {
            "id": c.get("_id"),
            "user_id": c.get("user_id"),
            "chat_id": c.get("chat_id"),
            "summary": c.get("summary"),
            "severity": c.get("severity"),
            "status": c.get("status"),
            "created_at": c.get("created_at"),
        }
        for c in pending
    ]

    return {"success": True, "consultations": items}, 200


@consultation_bp.route("/mine", methods=["GET"])
@token_required
def get_my_consultations(current_user):
    user = current_user or {}
    user_id = user.get("user_id")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    mine = ConsultationRequestModel.get_for_user(user_id)

    items = [
        {
            "id": c.get("_id"),
            "chat_id": c.get("chat_id"),
            "summary": c.get("summary"),
            "severity": c.get("severity"),
            "status": c.get("status"),
            "assigned_doctor_id": c.get("assigned_doctor_id"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
        }
        for c in mine
    ]

    return {"success": True, "consultations": items}, 200


@consultation_bp.route("/doctor/assigned", methods=["GET"])
@token_required
def get_assigned_consultations(current_user):
    user = current_user or {}
    user_id = user.get("user_id")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    doctor = DoctorUserModel.find_doctor_by_id(user_id)
    if not doctor:
        return {"success": False, "message": "Unauthorized - doctor access required"}, 403

    assigned = ConsultationRequestModel.get_for_doctor(user_id)
    items = [
        {
            "id": c.get("_id"),
            "user_id": c.get("user_id"),
            "chat_id": c.get("chat_id"),
            "summary": c.get("summary"),
            "severity": c.get("severity"),
            "status": c.get("status"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
        }
        for c in assigned
    ]
    return {"success": True, "consultations": items}, 200


@consultation_bp.route("/<consultation_id>/accept", methods=["POST"])
@token_required
def accept_consultation(current_user, consultation_id):
    user = current_user or {}
    doctor_id = user.get("user_id")

    if not doctor_id:
        return {"success": False, "message": "Unauthorized"}, 401

    doctor = DoctorUserModel.find_doctor_by_id(doctor_id)
    if not doctor:
        return {"success": False, "message": "Unauthorized - doctor access required"}, 403

    consultation = ConsultationRequestModel.get_by_id(consultation_id)
    if not consultation:
        return {"success": False, "message": "Consultation not found"}, 404

    accepted = ConsultationRequestModel.accept_consultation(consultation_id, doctor_id)
    if not accepted:
        return {"success": False, "message": "Consultation is not available for acceptance"}, 409

    updated = ConsultationRequestModel.get_by_id(consultation_id)

    return {
        "success": True,
        "message": "Consultation accepted",
        "consultation": {
            "id": updated.get("_id"),
            "status": updated.get("status"),
            "assigned_doctor_id": updated.get("assigned_doctor_id"),
        },
    }, 200


@consultation_bp.route("/<consultation_id>", methods=["GET"])
@token_required
def get_consultation(current_user, consultation_id):
    user = current_user or {}
    user_id = user.get("user_id")
    role = user.get("role")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    consultation = ConsultationRequestModel.get_by_id(consultation_id)
    if not consultation:
        return {"success": False, "message": "Consultation not found"}, 404

    if role == "doctor":
        if consultation.get("status") == "closed":
            return {"success": False, "message": "Consultation not found"}, 404
        if consultation.get("assigned_doctor_id") not in [None, user_id] and consultation.get("status") != "pending":
            return {"success": False, "message": "Unauthorized"}, 403
    else:
        if consultation.get("owner_user_id") != user_id:
            return {"success": False, "message": "Unauthorized"}, 403

    return {
        "success": True,
        "consultation": {
            "id": consultation.get("_id"),
            "user_id": consultation.get("user_id"),
            "chat_id": consultation.get("chat_id"),
            "summary": consultation.get("summary"),
            "severity": consultation.get("severity"),
            "status": consultation.get("status"),
            "assigned_doctor_id": consultation.get("assigned_doctor_id"),
            "created_at": consultation.get("created_at"),
            "updated_at": consultation.get("updated_at"),
        },
    }, 200


@consultation_bp.route("/<consultation_id>/messages", methods=["GET"])
@token_required
def get_consultation_messages(current_user, consultation_id):
    user = current_user or {}
    user_id = user.get("user_id")
    role = user.get("role")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    consultation = ConsultationRequestModel.get_by_id(consultation_id)
    if not consultation:
        return {"success": False, "message": "Consultation not found"}, 404

    if role == "doctor" and consultation.get("status") == "closed":
        return {"success": False, "message": "Consultation not found"}, 404

    is_owner = consultation.get("owner_user_id") == user_id
    is_assigned_doctor = role == "doctor" and consultation.get("assigned_doctor_id") == user_id

    if not (is_owner or is_assigned_doctor):
        return {"success": False, "message": "Unauthorized"}, 403

    messages = DoctorMessageModel.get_messages(consultation_id)
    return {"success": True, "messages": messages}, 200


@consultation_bp.route("/<consultation_id>/messages", methods=["POST"])
@token_required
def post_consultation_message(current_user, consultation_id):
    user = current_user or {}
    user_id = user.get("user_id")
    role = user.get("role")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    consultation = ConsultationRequestModel.get_by_id(consultation_id)
    if not consultation:
        return {"success": False, "message": "Consultation not found"}, 404

    if role == "doctor" and consultation.get("status") == "closed":
        return {"success": False, "message": "Consultation not found"}, 404

    is_owner = consultation.get("owner_user_id") == user_id
    is_assigned_doctor = role == "doctor" and consultation.get("assigned_doctor_id") == user_id

    if not (is_owner or is_assigned_doctor):
        return {"success": False, "message": "Unauthorized"}, 403

    body = request.json or {}
    message = (body.get("message") or "").strip()

    if not message:
        return {"success": False, "message": "message is required"}, 400

    sender = "doctor" if role == "doctor" else "user"
    DoctorMessageModel.add_message(consultation_id, sender, message)

    if consultation.get("status") in ["accepted", "active"]:
        ConsultationRequestModel.set_active(consultation_id)

    messages = DoctorMessageModel.get_messages(consultation_id)
    return {"success": True, "messages": messages}, 201


@consultation_bp.route("/<consultation_id>/close", methods=["POST"])
@token_required
def close_consultation(current_user, consultation_id):
    user = current_user or {}
    user_id = user.get("user_id")
    role = user.get("role")

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    consultation = ConsultationRequestModel.get_by_id(consultation_id)
    if not consultation:
        return {"success": False, "message": "Consultation not found"}, 404

    is_owner = consultation.get("owner_user_id") == user_id
    is_assigned_doctor = role == "doctor" and consultation.get("assigned_doctor_id") == user_id

    if not (is_owner or is_assigned_doctor):
        return {"success": False, "message": "Unauthorized"}, 403

    closed = ConsultationRequestModel.close_consultation(consultation_id)
    if not closed:
        return {"success": False, "message": "Consultation already closed"}, 409

    return {"success": True, "message": "Consultation closed"}, 200
