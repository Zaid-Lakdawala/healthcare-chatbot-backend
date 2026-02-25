
from flask_pymongo import PyMongo
from qdrant_client import QdrantClient

# MongoDB instance
mongo = PyMongo()

# Qdrant client
qdrant_client = QdrantClient(
    url="https://17de627e-c1fe-41e3-9ef3-22b4afc083b9.us-east4-0.gcp.cloud.qdrant.io",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.bPxr_VQ_smYJBo-tT8Y1jquw5pv9S2CLx9BuDEqDuF4",
)
