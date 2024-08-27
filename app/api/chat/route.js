import { NextResponse } from "next/server";
import { Pinecone } from "@pinecone-database/pinecone";

const { VertexAI } = require("@google-cloud/vertexai");

// Inform the AI what should it focus on when trying to give answers to users.
const textsi_1 = {
  text: `
  You are an AI assistant specializing in helping students find professors based on their specific criteria. Your primary function is to analyze user queries and provide information about the top 3 most relevant professors using a Retrieval-Augmented Generation (RAG) system.

For each user query:

1. Analyze the student's request, identifying key criteria such as subject area, teaching style, difficulty level, or any other specific requirements.

2. Use the RAG system to retrieve information about the top 3 professors who best match the criteria.

3. Present the information for each professor in a clear, concise format that includes:
   - professor: Professor's name
   - subject: Subject the professor teaches
   - stars: Overall rating given by students
   - review: A brief summary of student feedback

4. If the query is too broad or lacks specific criteria, ask follow-up questions to refine the search.

5. Maintain a neutral tone and provide objective information based on the data available in the RAG system.

6. If asked, explain the reasoning behind your professor selections.

7. Remind students that while this information can be helpful, it's always best to research further and consider multiple sources when making decisions about courses or professors.

8. Do not invent or fabricate information about professors. If certain details are not available in the RAG system, clearly state this.

9. Respect privacy and adhere to ethical guidelines. Do not share personal information about professors beyond what is publicly available and relevant to their professional roles.

10. Be prepared to answer follow-up questions about the professors or help refine the search based on additional criteria.

Remember, your goal is to assist students in making informed decisions about their education while providing accurate and helpful information based on the data available in the RAG system.
  `,
};

// Initialize Vertex with your Cloud project and location
const vertex_ai = new VertexAI({
  project: "rate-my-prof-rag-433210",
  location: "us-central1",
});

// Model currently in use
const model = "gemini-1.5-flash-001";

// Instantiate the models
const generativeModel = vertex_ai.preview.getGenerativeModel({
  model: model,
  generationConfig: {
    maxOutputTokens: 8192,
    temperature: 1,
    topP: 0.95,
  },
  safetySettings: [
    {
      category: "HARM_CATEGORY_HATE_SPEECH",
      threshold: "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
      category: "HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold: "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
      category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold: "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
      category: "HARM_CATEGORY_HARASSMENT",
      threshold: "BLOCK_MEDIUM_AND_ABOVE",
    },
  ],
  systemInstruction: {
    parts: [textsi_1],
  },
});

export async function POST(req) {
  // data from the frontend will be received here; the user's query
  const data = await req.json();

  /**
   * Step 4: Initialize Pinecone and OpenAI
   *
   */
  const pc = new Pinecone({
    apiKey: process.env.PINECONE_API_KEY,
  });
  const index = pc.index("rag").namespace("ns1");

  const text = data[data.length - 1].content;

  /**
   * Step 5: Process the user’s query
   * Extract the user’s question and create an embedding:
   * This is similar to the openAI embedding fetching API but it's rewritten to work with
   * vertex AI embedding
   */
  //
  const embedding = await fetchEmbeddings(text);

  /**
   * Step 6: Query Pinecone
   * Use the embedding to find similar professor reviews in Pinecone:
   */
  const results = await index.query({
    topK: 5,
    includeMetadata: true,
    vector: embedding,
  });

  /**
   * Step 7: Format the results
   * Process the Pinecone results into a readable string:
   */
  let resultString = "";
  results.matches.forEach((match) => {
    resultString += `
  Returned Results:
  Professor: ${match.id}
  Review: ${match.metadata.stars}
  Subject: ${match.metadata.subject}
  Stars: ${match.metadata.stars}
  \n\n`;
  });

  /**
   * Step 8: Prepare the OpenAI request
   * Combine the user’s question with the Pinecone results:
   */
  const lastMessage = data[data.length - 1];
  const lastMessageContent = lastMessage.content + resultString;
  const lastDataWithoutLastMessage = data.slice(0, data.length - 1);

  /**
   * Step 9: Send request to VertexAI
   * Create a chat completion request to VertexAI:
   */
  const reqBody = {
    contents: [{ role: "user", parts: [{ text: lastMessageContent }] }],
  };

  const streamingResp = await generativeModel.generateContentStream(reqBody);

  console.log(
    "streamingResponse:",
    JSON.stringify(await streamingResp.response)
  );

  // Create a new ReadableStream
  const stream = new ReadableStream({
    async start(controller) {
      for await (const item of streamingResp.stream) {
        const chunk = item.candidates[0].content.parts[0].text;
        // Encode the chunk and enqueue it
        controller.enqueue(new TextEncoder().encode(chunk));
      }
      controller.close();
    },
  });

  // Return a streaming response
  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
    },
  });
}

async function fetchEmbeddings(text) {
  try {
    const response = await fetch(
      "http://localhost:5000/calculate_text_embeddings",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }
    );

    if (!response.ok) {
      console.error("Server responded with status:", response.status);
      const text = await response.text(); // Get the response body as text
      console.error("Response body:", text);
      throw new Error("Failed to fetch embeddings");
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      console.error("Expected JSON response, received:", contentType);
      throw new Error("Received invalid response");
    }

    const embeddings = await response.json(); // Parse the JSON response
    return embeddings; // Return the embeddings
  } catch (error) {
    console.error("Error fetching embeddings:", error);
    throw error; // Rethrow the error to handle it where the function is called
  }
}
