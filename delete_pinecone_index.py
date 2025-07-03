from pinecone import Pinecone
import os

# Delete the old Pinecone index with the wrong dimension
pinecone_api_key = os.getenv('PINECONE_API_KEY')
pc = Pinecone(api_key=pinecone_api_key)
index_name = 'medical-analyzer-index'

if index_name in pc.list_indexes().names():
    pc.delete_index(index_name)
    print(f"Deleted Pinecone index: {index_name}")
else:
    print(f"Index {index_name} does not exist.")
