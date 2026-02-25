"""
MCP Server - Defines RAG tools for OpenAI Tool Calling
No separate process needed - functions are called directly from Flask
"""

import json
from bson import ObjectId
from datetime import datetime, date

from app import create_app
flask_app = create_app()

from app.models.user_model import UserModel
from app.models.chat_model import ChatModel
from app.utils.qdrant_service import QdrantService
from app.utils.embed_service import EmbedService


def sanitize(obj):
    """Convert MongoDB types to JSON-serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    return obj

def get_medical_context(user_id: str) -> dict:

    try:
        print(f"\n[MCP Tool] get_medical_context called for user: {user_id}")
        
        # Convert string to ObjectId if needed
        try:
            uid = ObjectId(user_id)
        except Exception as e:
            print(f"[MCP] Invalid user_id format: {user_id}")
            return {
                'user_id': user_id,
                'medical_info': {},
                'error': f'Invalid user_id format: {str(e)}'
            }
        
        user = UserModel.find_by_id(uid)
        if not user:
            print(f"[MCP] User not found: {user_id}")
            return {
                'user_id': user_id,
                'medical_info': {},
                'error': 'User not found'
            }
        
        questionnaire = user.get('questionnaire', {})
        
        context = {
            'user_id': user_id,
            'medical_info': {
                'age': questionnaire.get('age'),
                'gender': questionnaire.get('gender'),
                'height': questionnaire.get('height'),
                'weight': questionnaire.get('weight'),
                'medical_history': questionnaire.get('medical_history'),
                'medications': questionnaire.get('medications'),
                'allergies': questionnaire.get('allergies'),
            }
        }
        
        # Log retrieved data
        print(f"[MCP] Medical Context Retrieved:")
        for key, value in context['medical_info'].items():
            if value:
                print(f"  - {key}: {value}")
        
        clean_context = sanitize(context)
        return clean_context
        
    except Exception as e:
        print(f"[MCP ERROR] get_medical_context: {e}")
        import traceback
        traceback.print_exc()
        return {'user_id': user_id, 'medical_info': {}, 'error': str(e)}


def search_documents(query: str, user_id: str, limit: int = 5) -> dict:
    try:
        print(f"\n[MCP Tool] search_documents called")
        print(f"[MCP] Query: '{query}'")
        print(f"[MCP] Limit: {limit}")
        
        # Generate embedding for query
        query_vector = EmbedService.embed_query(query)
        print(f"[MCP] Embedding generated: {len(query_vector)} dimensions")
        
        # Search in vector database
        qdrant_service = QdrantService()
        results = qdrant_service.search(query_vector, limit=limit)
        print(f"[MCP] Qdrant returned: {len(results) if results else 0} results")
        
        # Format results
        formatted_results = []
        if results:
            for idx, point in enumerate(results, 1):
                content = point.payload.get('text', '')
                filename = point.payload.get('filename', '')
                score = point.score if hasattr(point, 'score') else 0
                chunk_idx = point.payload.get('chunk_index', 0)
                
                print(f"[MCP]   #{idx}: {filename} (similarity: {score:.4f})")
                
                formatted_results.append({
                    'content': content,
                    'filename': filename,
                    'similarity_score': float(score),
                    'chunk_index': chunk_idx
                })
        else:
            print(f"[MCP] No results found for query")
        
        result = {
            'query': query,
            'documents_found': len(formatted_results),
            'documents': formatted_results
        }
        
        clean_result = sanitize(result)
        return clean_result
        
    except Exception as e:
        print(f"[MCP ERROR] search_documents: {e}")
        import traceback
        traceback.print_exc()
        return {'query': query, 'documents_found': 0, 'documents': [], 'error': str(e)}


def get_conversation_history(conversation_id: str, limit: int = 10) -> dict:
   
    try:
        print(f"\n[MCP Tool] get_conversation_history called for: {conversation_id}")
        
        # Convert string to ObjectId if needed
        try:
            conv_id = ObjectId(conversation_id)
        except Exception as e:
            print(f"[MCP] Invalid conversation_id format: {conversation_id}")
            return {
                'conversation_id': conversation_id,
                'messages': [],
                'error': f'Invalid conversation_id format: {str(e)}'
            }
        
        conversation = ChatModel.get_conversation(conv_id)
        if not conversation:
            print(f"[MCP] Conversation not found: {conversation_id}")
            return {
                'conversation_id': conversation_id,
                'messages': [],
                'error': 'Conversation not found'
            }
        
        messages = conversation.get('messages', [])
        
        # Filter to only user and assistant messages
        visible_messages = [
            {
                'role': msg.get('role'),
                'content': msg.get('content'),
                'created_at': msg.get('created_at')
            }
            for msg in messages
            if msg.get('role') in ['user', 'assistant']
        ]
        
        # Return last N messages
        recent_messages = visible_messages[-limit:]
        
        print(f"[MCP] Conversation history: {len(recent_messages)} messages")
        
        result = {
            'conversation_id': conversation_id,
            'total_messages': len(visible_messages),
            'returned_messages': len(recent_messages),
            'messages': recent_messages
        }
        
        clean_result = sanitize(result)
        return clean_result
        
    except Exception as e:
        print(f"[MCP ERROR] get_conversation_history: {e}")
        import traceback
        traceback.print_exc()
        return {'conversation_id': conversation_id, 'messages': [], 'error': str(e)}



TOOLS_FOR_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the medical knowledge base for relevant documents using vector similarity. Use this when the user asks about symptoms, treatments, medications, or medical conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'symptoms of diabetes', 'how to treat fever')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_medical_context",
            "description": "Get the user's medical background including age, gender, medical history, medications, and allergies. Use this to personalize medical advice based on their specific health profile.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_conversation_history",
            "description": "Get recent conversation history to understand context and previous messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of messages to return (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    }
]



def execute_tool(tool_name: str, tool_input: dict, user_id: str = None, conversation_id: str = None) -> dict:

    print(f"\n[MCP] Executing tool: {tool_name}")
    print(f"[MCP] Input: {tool_input}")
    
    try:
        if tool_name == "search_documents":
            result = search_documents(
                query=tool_input.get('query'),
                user_id=user_id,  # Use injected user_id, not from OpenAI
                limit=tool_input.get('limit', 5)
            )
        elif tool_name == "get_medical_context":
            result = get_medical_context(
                user_id=user_id  # Use injected user_id, not from OpenAI
            )
        elif tool_name == "get_conversation_history":
            result = get_conversation_history(
                conversation_id=conversation_id,  # Use injected conversation_id, not from OpenAI
                limit=tool_input.get('limit', 10)
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        
        print(f"[MCP] Tool result: {str(result)[:200]}...")
        return result
        
    except Exception as e:
        print(f"[MCP ERROR] Tool execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


