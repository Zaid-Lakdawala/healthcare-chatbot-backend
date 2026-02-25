import uuid
from qdrant_client.models import VectorParams, Distance, PointStruct, PayloadSchemaType
from app.extensions import qdrant_client

class QdrantService:
    def __init__(self):
        self.client = qdrant_client
        self.collection = "documents"

        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=3072,
                    distance=Distance.COSINE
                )
            )
        
        try:
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="doc_id",
                field_schema=PayloadSchemaType.KEYWORD
            )
        except Exception:
            pass

    def store_vectors(self, doc_id, chunks, vectors, filename=None, file_size=None):
        BATCH_SIZE = 300
        total = len(vectors)

        for start in range(0, total, BATCH_SIZE):
            batch_points = []
            end = min(start + BATCH_SIZE, total)
            batch_vectors = vectors[start:end]

            for idx, vector in enumerate(batch_vectors, start):
                batch_points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "doc_id": doc_id,
                            "chunk_index": idx,
                            "text": chunks[idx],
                            "filename": filename,
                            "file_size": file_size,
                        }
                    )
                )

            # Upsert batch
            self.client.upsert(
                collection_name=self.collection,
                points=batch_points
            )

    def search(self, vector, limit=5):
        try:
            result = self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            return result.points
        except Exception as e:
            print("QDRANT SEARCH ERROR:", e)
            raise e
