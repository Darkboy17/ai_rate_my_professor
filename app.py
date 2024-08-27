from flask import Flask, request, jsonify
from typing import List, Optional
from flask_cors import CORS
import requests
import json
from bs4 import BeautifulSoup
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import os

from pinecone import Pinecone, ServerlessSpec

app = Flask(__name__)
CORS(app)

@app.route('/calculate_text_embeddings', methods=['POST'])
def calculate_text_embeddings():
    # Parse the JSON body of the request
    data = request.get_json()

    # Extract 'text', 'model_name', and 'dimensionality' from the JSON, providing defaults if not present
    text = data.get('text')
    model_name = data.get('model_name', "text-embedding-004")
    dimensionality = data.get('dimensionality', 768)

    # Validate that 'text' is provided and is a string
    if not text or not isinstance(text, str):
        return jsonify({"error": "Missing 'text' in request body or 'text' is not a string"}), 400

    """Embeds text with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)

    # Ensure text is a string
    if isinstance(text, str):
        # Create a TextEmbeddingInput instance for the single piece of text
        inputs = [TextEmbeddingInput(text)]
        kwargs = dict(
            output_dimensionality=dimensionality) if dimensionality else {}
        embeddings = model.get_embeddings(inputs, **kwargs)
        # Assuming embeddings is a list of embedding objects, extract the values
        return [[value for value in embedding.values] for embedding in embeddings]
    else:
        raise ValueError("Input must be a string.")


def embed_reviews():
    data = request.get_json()  # Parse the JSON body of the request
    # Extract the 'reviews' key from the JSON, defaulting to an empty list if not present
    reviews = data.get('reviews', [])

    # Ensure reviews is a list of dictionaries
    if not isinstance(reviews, list) or not all(isinstance(review, dict) for review in reviews):
        return jsonify({"error": "Reviews must be a list of dictionaries."}), 400

    # Default model name, can be overridden by the request
    model_name = data.get('model_name', "text-embedding-004")
    # Optional dimensionality, can be provided in the request
    dimensionality = data.get('dimensionality')

    # Now call the actual embedding function with the extracted reviews
    embeddings = calculate_embeddings(reviews, model_name, dimensionality)
    return jsonify(embeddings)

# Generate embeddings for a user query
def calculate_embeddings(reviews: str, model_name: str = "text-embedding-004", dimensionality: Optional[int] = 768) -> List[List[float]]:
    """Embeds reviews with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)

    # Ensure reviews is a list of dictionaries
    if isinstance(reviews, list) and all(isinstance(review, dict) for review in reviews):
        inputs = [TextEmbeddingInput(review['review']) for review in reviews]
        kwargs = dict(
            output_dimensionality=dimensionality) if dimensionality else {}
        embeddings = model.get_embeddings(inputs, **kwargs)
        return [embedding.values for embedding in embeddings]
    else:
        raise ValueError("Reviews must be a list of dictionaries.")


def embed_reviews_list(reviews: List[dict], model_name: str = "text-embedding-004", dimensionality: Optional[int] = 768) -> List[List[float]]:
    """Embeds reviews with a pre-trained, foundational model."""
    model = TextEmbeddingModel.from_pretrained(model_name)

    # Ensure reviews is a list of dictionaries
    if isinstance(reviews, list) and all(isinstance(review, dict) for review in reviews):
        inputs = [TextEmbeddingInput(review['review']) for review in reviews]
        kwargs = dict(
            output_dimensionality=dimensionality) if dimensionality else {}
        embeddings = model.get_embeddings(inputs, **kwargs)
        return [embedding.values for embedding in embeddings]
    else:
        raise ValueError("Reviews must be a list of dictionaries.")


# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


@app.route('/scrape', methods=['GET'])
def scrape_data():
    data = request.json if request.method == 'POST' else request.args
    url = data.get('url')

    if not url:
        return jsonify({'error': 'You forgot to provide the URL for scraping the data'}), 400

    try:
        # Step 1: Scrape the Data
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        ratingsData = soup.find_all('ul', class_='cbdtns')
        stars_data = ratingsData[0].find_all('div', class_='DObVa')[
            0].find_all('div')[0].find_all('div')[1]
        review_data = ratingsData[0].find_all('div', class_='gRjWel')[0]
        professor_data = soup.find_all('div', class_='kFNvIp')[
            0].find_all('span')
        subject_data = soup.find_all('div', class_='iLYGwn')[
            0].find_all('a')[0].find_all('b')[0]

        scraped_data = {
            "professor": f'Prof. {professor_data[1].text} {professor_data[2].text.strip()}',
            "subject": subject_data.text.split()[0],
            "stars": float(stars_data.text),
            "review": review_data.text,
        }

        print("Scraped Data:", scraped_data)

        # Step 2: Load Existing Data and Check for Duplicates
        with open('reviews.json', 'r') as file:
            professor_data = json.load(file)

        if not any(review['professor'] == scraped_data['professor'] and review['subject'] == scraped_data['subject'] for review in professor_data['reviews']):
            professor_data['reviews'].append(scraped_data)

            # Write the updated data back to the JSON file
            with open('reviews.json', 'w') as file:
                json.dump(professor_data, file, indent=4)

            # Step 3: Check if Pinecone Index Exists and Create if Not
            ''' index_name = "rag"
            if index_name not in pc.list_indexes():
                pc.create_index(
                    name=index_name,
                    dimension=768,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            else:
                print(f"Index '{index_name}' already exists. Skipping creation.")'''

            # Step 4: Embed and Upsert Data into Pinecone
            embeddings = embed_reviews_list(
                [scraped_data], model_name="text-embedding-004")
            processed_data = [{
                "values": embeddings[0],
                "id": scraped_data["professor"],
                "metadata": {
                    "review": scraped_data["review"],
                    "subject": scraped_data["subject"],
                    "stars": scraped_data["stars"]
                }
            }]

            # Access the existing index and upsert data
            index = pc.Index("rag")
            upsert_response = index.upsert(
                vectors=processed_data,
                namespace="ns1",
            )
            print(f"Upserted count: {upsert_response['upserted_count']}")
            return jsonify({'message': 'Data Scraped successfully and upserted into pinecone', 'code': 100, 'scraped_data': scraped_data}), 200

        else:
            print(
                "Duplicate entry found. The data will not be appended or upserted to Pinecone.")
            return jsonify({'message': 'Duplicate entry found. The data will not be appended or upserted to Pinecone.', 'code': 300}, 200)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
