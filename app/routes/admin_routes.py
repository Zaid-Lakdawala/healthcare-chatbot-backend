"""
Admin Routes
Admin-specific endpoints for dashboard statistics and management
"""
from flask import Blueprint, jsonify
from app.models.user_model import UserModel
from app.models.chat_model import ChatModel
from app.utils.auth import token_required
from app.utils.qdrant_service import QdrantService
from bson import ObjectId

admin_bp = Blueprint("admin_bp", __name__)
qdrant = QdrantService()


@admin_bp.route("/stats", methods=["GET"])
@token_required
def get_admin_stats(current_user):
    """Get admin dashboard statistics"""
    user = current_user or {}
    role = user.get("role")
    
    # Verify user is admin
    if role != "admin":
        return jsonify({
            "success": False,
            "message": "Unauthorized - Admin access required"
        }), 403
    
    try:
        # Get total users
        total_users = UserModel.get_user_count()
        
        # Get total conversations
        total_conversations = ChatModel.get_total_conversations_count()
        
        # Get total documents from Qdrant
        try:
            result = qdrant.client.scroll(
                collection_name="documents",
                limit=20000,
                with_payload=True,
                with_vectors=False
            )
            
            points = result[0]
            unique_doc_ids = set()
            
            for p in points:
                doc_id = p.payload.get("doc_id")
                if doc_id:
                    unique_doc_ids.add(doc_id)
            
            total_documents = len(unique_doc_ids)
        except Exception:
            total_documents = 0
        
        return jsonify({
            "success": True,
            "data": {
                "totalUsers": total_users,
                "totalConversations": total_conversations,
                "totalDocuments": total_documents
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to fetch statistics: {str(e)}"
        }), 500


@admin_bp.route("/users", methods=["GET"])
@token_required
def get_all_users(current_user):
    """Get all users (admin only)"""
    user = current_user or {}
    role = user.get("role")
    
    if role != "admin":
        return jsonify({
            "success": False,
            "message": "Unauthorized - Admin access required"
        }), 403
    
    try:
        users, total = UserModel.get_all_users()
        
        return jsonify({
            "success": True,
            "data": users,
            "count": total
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to fetch users: {str(e)}"
        }), 500


@admin_bp.route("/conversations", methods=["GET"])
@token_required
def get_all_conversations(current_user):
    """Get all conversations (admin only)"""
    user = current_user or {}
    role = user.get("role")
    
    if role != "admin":
        return jsonify({
            "success": False,
            "message": "Unauthorized - Admin access required"
        }), 403
    
    try:
        conversations = ChatModel.get_all_conversations()
        
        return jsonify({
            "success": True,
            "data": conversations,
            "count": len(conversations)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to fetch conversations: {str(e)}"
        }), 500
