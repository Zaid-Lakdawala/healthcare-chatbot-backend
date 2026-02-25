import uuid
from datetime import datetime
from flask import Blueprint, request

from app.utils.file_extractor import FileExtractor
from app.utils.chunk_service import ChunkService
from app.utils.embed_service import EmbedService
from app.utils.qdrant_service import QdrantService
from app.utils.auth import token_required

from qdrant_client.models import Filter, FieldCondition, MatchValue

qdrant = QdrantService()


documents_bp = Blueprint("documents_bp", __name__)


@documents_bp.route("/upload", methods=["POST"])
@token_required
def upload_documents(current_user):
    files = request.files.getlist("documents")
    
    if not files or len(files) == 0:
        return {"success": False, "message": "At least one document is required."}, 400
 
    uploaded = []
    try:
        for f in files:
            doc_id = str(uuid.uuid4())

            
            file_size = len(f.read())
            f.seek(0)

            text = FileExtractor.extract(f)
            if not text.strip():
                return {
                    "success": False,
                    "message": f"Document '{f.filename}' contains no readable text"
                }, 400

            chunks = ChunkService.split_text(text)
            if not chunks:
                return {
                    "success": False,
                    "message": f"Document '{f.filename}' could not be chunked"
                }, 400

            try:
                vectors = EmbedService.embed_text_list(chunks)
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Embedding failed for '{f.filename}': {str(e)}"
                }, 500

        
            qdrant.store_vectors(
                doc_id=doc_id,
                chunks=chunks,
                vectors=vectors,
                filename=f.filename,
                file_size=file_size
            )

            uploaded.append({
                "document_id": doc_id,
                "filename": f.filename,
                "file_size": file_size,
                "chunk_count": len(chunks)
            })

        return {
            "success": True,
            "message": "Documents uploaded successfully",
            "documents": uploaded
        }, 201
    
    except Exception as e:
        return {"success": False, "message": str(e)}, 500


@documents_bp.route("", methods=["GET"])
@token_required
def get_documents(current_user):
    try:
        result = qdrant.client.scroll(
            collection_name="documents",
            limit=20000,
            with_payload=True,
            with_vectors=False
        )

        points = result[0]
        documents = {}

        for p in points:
            doc_id = p.payload.get("doc_id")
            if not doc_id:
                continue

            filename = p.payload.get("filename")
            file_size = p.payload.get("file_size")

            if doc_id not in documents:
                documents[doc_id] = {
                    "document_id": doc_id,
                    "filename": filename,
                    "file_size": file_size,
                    "chunk_count": 0
                }

            documents[doc_id]["chunk_count"] += 1

        return {
            "success": True,
            "documents": list(documents.values())
        }, 200

    except Exception as e:
        return {"success": False, "message": str(e)}, 500


@documents_bp.route("/<document_id>", methods=["DELETE"])
@token_required
def delete_document(current_user, document_id):
    try:
        qdrant.client.delete(
            collection_name="documents",
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )

        return {
            "success": True,
            "message": "Document deleted successfully"
        }, 200

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete document: {str(e)}"
        }, 500
   
