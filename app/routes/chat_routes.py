
from flask import Blueprint, request, jsonify
from app.models.chat_model import ChatModel
from app.models.user_model import UserModel
from app.models.memory_model import MemoryModel
from app.utils.auth import token_required
from app.utils.embed_service import EmbedService
from app.utils.qdrant_service import QdrantService
from marshmallow import ValidationError
from datetime import datetime, timezone
from openai import OpenAI
import os
import json
from concurrent.futures import ThreadPoolExecutor

chat_bp = Blueprint("chat_bp", __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@chat_bp.route("", methods=["GET"])
@token_required
def get_conversations(current_user):
    """Get all conversations for the current user"""
    user = current_user or {}
    user_id = user.get("user_id")
    
    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401
    
    conversations = ChatModel.get_user_conversations(user_id)
    
    return {
        "success": True,
        "conversations": conversations
    }, 200


@chat_bp.route("/<conversation_id>", methods=["GET"])
@token_required
def get_conversation(current_user, conversation_id):
    """Get a specific conversation by ID"""
    user = current_user or {}
    user_id = user.get("user_id")
    
    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401
    
    conversation = ChatModel.get_conversation(conversation_id)
    
    if not conversation:
        return {"success": False, "message": "Conversation not found"}, 404
    
    # Verify ownership
    if conversation.get("user_id") != user_id:
        return {"success": False, "message": "Unauthorized"}, 403
    
    return {
        "success": True,
        "conversation": conversation
    }, 200


@chat_bp.route("/check-active", methods=["GET"])
@token_required
def check_active_conversation(current_user):
    """Check if user has an active conversation"""
    user = current_user or {}
    user_id = user.get("user_id")
    
    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401
    
    active_conversation = ChatModel.get_active_conversation(user_id)
    
    return {
        "success": True,
        "has_active": active_conversation is not None,
        "active_conversation": active_conversation
    }, 200


@chat_bp.route("/<conversation_id>/end", methods=["POST"])
@token_required
def end_conversation(current_user, conversation_id):
    """End a conversation and move it to history"""
    user = current_user or {}
    user_id = user.get("user_id")
    
    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401
    
    conversation = ChatModel.get_conversation(conversation_id)
    
    if not conversation:
        return {"success": False, "message": "Conversation not found"}, 404
    
    # Verify ownership
    if conversation.get("user_id") != user_id:
        return {"success": False, "message": "Unauthorized"}, 403
    
    # End the conversation
    result = ChatModel.end_conversation(conversation_id)
    
    if result:
        updated_conversation = ChatModel.get_conversation(conversation_id)
        return {
            "success": True,
            "message": "Consultation ended",
            "conversation": updated_conversation
        }, 200
    else:
        return {"success": False, "message": "Failed to end conversation"}, 500


@chat_bp.route("/start", methods=["POST"])
@token_required
def start_conversation(current_user):
    print("Current User:", current_user)
    user =  current_user or {}
    user_id = user.get("user_id")
    user_name = user.get("name")
    
    # Check if user has an active conversation
    active_conversation = ChatModel.get_active_conversation(user_id)
    if active_conversation:
        return {
            "success": False, 
            "message": "You already have an active consultation. Please end it before starting a new one.",
            "active_conversation": active_conversation
        }, 409

    
    long_term_memory = MemoryModel.get_summary(user_id) or ""

    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401
    else:
        model = "gpt-4.1-mini"

        # 1. Get user details and check questionnaire
        user_details = UserModel.find_by_id(user_id)
        
        if not user_details:
            return {"success": False, "message": "User not found"}, 404
        
        questionnaire = user_details.get("questionnaire")
        
        if not questionnaire:
            return {"success": False, "message": "Please complete the medical questionnaire before proceeding."}, 400

        # 2. Create new conversation
        now = datetime.now(timezone.utc)
        human_time = now.strftime("%b %d, %Y at %I:%M %p")  # Example: "Jan 14, 2026 at 04:32 PM"

        conversation_id = ChatModel.create_conversation(
            user_id,
            f"Consultation {human_time}"
        )

        # 3. Format questionnaire data for AI context
        qa_lines = []
        qa_lines.append(f"- Age: {questionnaire.get('age', 'Not provided')}")
        qa_lines.append(f"- Gender: {questionnaire.get('gender', 'Not provided')}")
        qa_lines.append(f"- Medical History: {questionnaire.get('medical_history', 'Not provided')}")
        qa_lines.append(f"- Current Medications: {questionnaire.get('medications', 'Not provided')}")
        qa_lines.append(f"- Allergies: {questionnaire.get('allergies', 'Not provided')}")


        qa_context = "\n".join(qa_lines)

        # 4. Build SYSTEM message (doctor persona)
        memory_block = (
            f"Long-term information about this user from previous conversations:\n"
            f"{long_term_memory}\n\n"
            if long_term_memory else
            ""
        )

        formatted_dob = user_details.get("dob", "Not provided")
        gender = questionnaire.get("gender", "Not provided")

        system_prompt = (
            "You are a highly skilled, compassionate, and friendly medical doctor AI. "
            "Your goal is to help the user understand their symptoms, offer general guidance, "
            "and ask thoughtful follow-up questions—always in a warm and approachable way. "
            "You are NOT a substitute for a real doctor, but you can provide supportive information "
            "based on what the user shares.\n\n"

            f"{memory_block}"
            f"Patient Name: {user_name}\n"
            f"Patient DOB: {formatted_dob}\n"
            f"Patient Gender: {gender}\n"
            f"Previous Medical Questionnaire:\n{qa_context}\n\n"

            "Begin the conversation with a warm, friendly greeting. "
            "Do NOT repeatedly acknowledge their previous questionnaire answers unless directly relevant. "
            "You may make gentle, human-like remarks such as ‘How have you been feeling lately?’ or "
            "‘Tell me what’s bothering you today’. A light, comforting tone is welcome, but stay medically accurate. these are some examples you can ask similar to this also ask about previous problems\n\n"

            "Your first message should invite the patient to share how they are feeling today "
            "or what symptoms they would like to discuss."
        )
        user_first_message = "Please start the medical consultation."
        print(system_prompt)
        # 5. Make model generate the first message
        try:
            ai_response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_first_message}
                ],
                stream=False
            )
        except Exception as e:
            return {"success": False, "message":  {e}}, 500

        ChatModel.append_message(conversation_id, "system", system_prompt)
        final_message = ""
        for out in ai_response.output:
            if hasattr(out, "text") and isinstance(out.text, str):
                final_message += out.text
                continue

            if hasattr(out, "content") and isinstance(out.content, list):
                for part in out.content:
                    if hasattr(part, "text"):
                        final_message += part.text
                    else:
                        final_message += str(part)
                continue

            # Fallback
            final_message += str(out)

        if not final_message:
            final_message = "Hello! I’m your medical assistant. How can I help you today?"

        
        ChatModel.append_message(
            conversation_id,
            "system",
            f"Patient questionnaire data:\n{qa_context}"
        )

        # 6. Save the first assistant message in conversation
        ChatModel.append_message(conversation_id, "assistant", final_message)

        data = ChatModel.get_conversation(conversation_id)

        # 7. Return everything
        return {
            "success": True,
            "conversation": data
        }, 201


@chat_bp.route("/<conversation_id>/message", methods=["POST"])
@token_required
def send_message(current_user, conversation_id):
    """Send a user message and get AI response via MCP Tool Calling"""
    from mcp_server import TOOLS_FOR_OPENAI, execute_tool
    
    user = current_user or {}
    user_id = user.get("_id")
    
    data = request.json or {}
    user_message = data.get("content", "").strip()
    
    if not user_message:
        return {"success": False, "message": "Message cannot be empty"}, 400
    
    try:
        # 1. Get conversation
        conversation = ChatModel.get_conversation(conversation_id)
        if not conversation:
            return {"success": False, "message": "Conversation not found"}, 404
        
        # Verify ownership
        if conversation.get("user_id") != user_id:
            return {"success": False, "message": "Unauthorized"}, 403
        
        # 2. Save user message
        ChatModel.append_message(conversation_id, "user", user_message)
        
        # 3. Build initial messages list (for OpenAI)
        all_messages = conversation.get("messages", [])
        message_history = [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in all_messages
            if msg.get("role") in ["user", "assistant"]
        ]
        
        # 4. Build system prompt for medical AI
        system_prompt = (
            "You are a highly skilled, compassionate, and friendly medical doctor AI. "
            "You MUST conduct a thorough assessment through questions before giving advice.\n\n"
            "RESPONSE FORMAT RULE (MANDATORY): Respond in plain text only. Do NOT use markdown. "
            "Do NOT use symbols like #, *, -. Use short natural paragraphs and simple sentences.\n\n"
            "QUERIES CAN BE RELATED OR UNRELATED TO PREVIOUS CONVERSATION HISTORY. FOR EVERY QUERY YOU MUST DECIDE IF THE QUERY IS A CONTINUATION OF PREVIOUS CONVERSATION OR NOT. IF IT IS, USE CONTEXT FROM PREVIOUS MESSAGES. IF NOT, TREAT IT AS A NEW QUERY.\n"
            "QUESTION MEMORY RULE (MANDATORY): If you already asked specific assessment questions for the current issue and the user has answered them, do NOT ask those same questions again. "
            "Ask only new follow-up questions that add new clinical value. "
            "Reset questioning only when the user introduces a new or different issue/illness/symptom.\n"
            "Redirect non-medical queries politely\n"
            
            
            "CRITICAL WORKFLOW (FOLLOW THIS EXACTLY):\n"
            
            "Step 1: Identify query type:\n"
            "   - GENERAL QUESTION: 'What causes headaches?', 'How do I treat migraines?', 'What are symptoms of...?' etc\n"
            "   - PERSONAL SYMPTOM: 'I have a headache', 'My head hurts', 'I experience...' etc\n\n"
            "CRITICAL: IDENTIFY QUERY TYPE FIRST:\n"

            "Step 2: For GENERAL QUESTIONS:\n"
            "   → Search knowledge base (use search_documents)\n"
            "   → Provide educational answer directly (no need to ask clarifying questions)\n"
            "   → You can optionally ask if they have this condition to help further\n\n"
            
            "Step 3: For PERSONAL SYMPTOMS:\n"
            "   → Search knowledge base first (use search_documents)\n"
            "   → If VAGUE (like 'something hurts', 'I'm in pain') → Ask WHERE, WHEN, HOW\n"
            "   → If SPECIFIC but NO relevant documents → Tell them you lack verified info\n"
            "   → If found relevant documents →  It is imperative you ask clarifying questions AND comprehensive assessment questions\n\n"
            "   → After user answers clarifying questions → Provide advice based on verified information\n\n"
         
            "TOOLS AVAILABLE:\n"
            "- search_documents: Search medical knowledge base\n"
            "- get_medical_context: Get user's medical history\n"
            "- get_conversation_history: Review previous messages\n\n"
            
            "WORKFLOW:\n"
            "1. User mentions symptom → Call search_documents\n"
            "2. Check 'documents_found' in results:\n"
            "   - If 0 documents + SPECIFIC NONVAGUE query → REJECT immediately\n"
            "   - If 0 documents + VAGUE query → ASK for clarification\n"
            "   - If >0 documents → Ask clarifying questions, then provide advice\n\n"
            
            "Remember: General educational questions get answered directly. Personal symptoms need assessment questions.Redirect non-medical queries politely. Queries can be related or unrelated to previous conversation history. Always prioritize safety, clarity and correct information. If you don't have verified information, say so clearly and recommend consulting a healthcare professional."
            
        )
        
        # 5. Prepare tool descriptions
        print(f"\n[Tool Calling] Starting tool calling loop with user message: '{user_message}'")
        
        # 6. Tool calling loop (OpenAI decides when to use tools)
        max_iterations = 3  # Prevent infinite loops
        iteration = 0
        final_message = None
        any_relevant_documents_found = False

        # Decide if this query should require retrieval using model-based intent classification
        retrieval_required = False
        try:
            classifier_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify whether the user's latest message requires medical knowledge-base retrieval. "
                            "Return STRICT JSON only with keys: requires_retrieval (boolean), reason (string)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Message: {user_message}\n"
                            "Set requires_retrieval=true for medical symptoms, diagnosis requests, treatments, medications, "
                            "or medical condition questions. Set false for greetings, casual chat, and non-medical topics."
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )

            classifier_content = classifier_response.choices[0].message.content or "{}"
            classifier_json = json.loads(classifier_content)
            retrieval_required = bool(classifier_json.get("requires_retrieval", False))
            print(f"[Tool Calling] Retrieval classifier decision: {retrieval_required} , Reason: {classifier_json.get('reason', 'No reason provided')}")
        except Exception as classifier_error:
            print(f"[Tool Calling] Classifier failed, falling back to auto tool choice: {classifier_error}")
            retrieval_required = False
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n[Tool Calling] Iteration {iteration}")
            
            try:
                # Force retrieval on first pass only when classifier says it is needed.
                tool_choice_setting = "required" if iteration == 1 and retrieval_required else "auto"
                print(f"[Tool Calling] Using tool_choice: {tool_choice_setting}")
                
                # Build messages: Only add user message on first iteration
                # After that, message_history already contains everything
                if iteration == 1:
                    current_messages = [
                        {"role": "system", "content": system_prompt},
                        *message_history,
                        {"role": "user", "content": user_message}
                    ]
                else:
                    current_messages = [
                        {"role": "system", "content": system_prompt},
                        *message_history
                    ]
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=current_messages,
                    tools=TOOLS_FOR_OPENAI,
                    tool_choice=tool_choice_setting
                )
                
                print(f"[Tool Calling] OpenAI response finish_reason: {response.choices[0].finish_reason}")
                
                # Check the response
                if response.choices[0].finish_reason == "tool_calls":
                    # OpenAI wants to use tools
                    assistant_message = response.choices[0].message
                    print(f"[Tool Calling] OpenAI called tools: {len(assistant_message.tool_calls)} tool(s)")
                    
                    # Add assistant's response to history
                    message_history.append({
                        "role": "assistant",
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    # Flag to exit outer loop after tool execution
                    should_stop = False
                    
                    # Execute each tool call and add separate response for each
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_input = json.loads(tool_call.function.arguments)
                        
                        print(f"[Tool Calling] Executing: {tool_name}")
                        
                        # Execute the tool (inject user_id and conversation_id)
                        tool_result = execute_tool(tool_name, tool_input, user_id=user_id, conversation_id=conversation_id)
                        
                        # Enforce relevance threshold and reject only if NO relevant docs were found at all
                        if tool_name == "search_documents":
                            documents = tool_result.get('documents', [])
                            min_similarity_threshold = 0.35  # Only accept docs with >0.35 similarity
                            relevant_docs = [
                                doc for doc in documents 
                                if doc.get('similarity_score', 0) >= min_similarity_threshold
                            ]

                            # Always pass only relevant docs back to the model
                            tool_result['documents'] = relevant_docs
                            tool_result['documents_found'] = len(relevant_docs)
                            tool_result['filtered_out'] = len(documents) - len(relevant_docs)
                            
                            if len(relevant_docs) > 0:
                                any_relevant_documents_found = True
                                print(f"[Tool Calling] Relevant documents found above {min_similarity_threshold}")
                            else:
                                print(f"[Tool Calling] No relevant documents found (all below {min_similarity_threshold} similarity)")

                                # If we've already found relevant docs earlier, do NOT hard-reject the whole request.
                                # This handles cases where a later tool call drifts to an unrelated query.
                                if any_relevant_documents_found:
                                    tool_result['no_verified_knowledge_for_query'] = True
                                    tool_result['note'] = (
                                        "No verified knowledge found for this specific query at the current similarity threshold."
                                    )
                                    print("[Tool Calling] Keeping flow alive: earlier relevant docs exist")
                                else:
                                    print(f"[Tool Calling] Hard rejecting query - no verified knowledge")

                                    # Immediate rejection only when no relevant docs were found in any iteration
                                    final_message = (
                                        "I don't currently have verified information about this topic in my knowledge base.\n\n"
                                        "Try rephrasing your question or ask about a different symptom.\n\n"
                                        "I recommend consulting a healthcare professional for accurate guidance on other medical concerns.\n\n"
                                    )
                                    should_stop = True
                                    break  # Exit tool execution loop
                        
                        # Add INDIVIDUAL tool result message (OpenAI requires this format)
                        message_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, indent=2)
                        })
                    
                    # Check if we should stop due to hard rejection
                    if should_stop:
                        print(f"[Tool Calling] Breaking main loop due to hard rejection")
                        break
                    
                    # Continue loop to get final response from OpenAI
                    continue
                
                else:
                    # OpenAI finished with a response (no more tool calls)
                    print(f"[Tool Calling] OpenAI finished with final response")
                    final_message = response.choices[0].message.content
                    break
                    
            except Exception as e:
                print(f"[Tool Calling ERROR] {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "message": f"AI service error: {str(e)}"}, 500
        
        # 7. Use fallback if we hit max iterations
        if final_message is None:
            print(f"[Tool Calling] WARNING: Hit max iterations without final response")
            final_message = "I apologize, but I'm having difficulty processing your request. Please try again."
        
        # 8. Save AI message
        ChatModel.append_message(conversation_id, "assistant", final_message)
        
        # 9. Return updated conversation
        updated_conversation = ChatModel.get_conversation(conversation_id)

        return {
            "success": True,
            "message": final_message,
            "conversation": updated_conversation
        }, 200

    except Exception as e:
        print(f"Error in send_message: {e}")
        return {"success": False, "message": f"Server error: {str(e)}"}, 500


