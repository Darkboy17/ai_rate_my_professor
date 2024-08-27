from dotenv import load_dotenv
load_dotenv()
from pinecone import Pinecone, ServerlessSpec
from typing import List, Optional
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import os
import json

def embed_reviews(reviews: List[dict], model_name: str = "text-embedding-004", dimensionality: Optional[int] = 768) -> List[List[float]]:
    """Embeds reviews with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)
    
    # Ensure reviews is a list of dictionaries
    if isinstance(reviews, list) and all(isinstance(review, dict) for review in reviews):
        inputs = [TextEmbeddingInput(review['review']) for review in reviews]
        kwargs = dict(output_dimensionality=dimensionality) if dimensionality else {}
        embeddings = model.get_embeddings(inputs, **kwargs)
        return [embedding.values for embedding in embeddings]
    else:
        raise ValueError("Reviews must be a list of dictionaries.")

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Create a Pinecone index
pc.create_index(
    name="rag",
    dimension=768,
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)

# Load the review data
data = json.load(open("reviews.json"))

processed_data = []

# Directly access the list of reviews
reviews_list = data['reviews']

for review in reviews_list:
    professor = review['professor']
    subject = review['subject']
    stars = review['stars']
    review_text = review['review']
    
    embeddings = embed_reviews([review], model_name="text-embedding-004")

    processed_data.append({
    "values": embeddings[0], 
    "id": review["professor"], 
    "metadata": {
        "review": review["review"], 
        "subject": review["subject"], 
        "stars": review["stars"]
    }

})

# Insert the embeddings into the Pinecone index
index = pc.Index("rag")
upsert_response = index.upsert(
    vectors=processed_data,
    namespace="ns1",
)
print(f"Upserted count: {upsert_response['upserted_count']}")

# Print index statistics
print(index.describe_index_stats())