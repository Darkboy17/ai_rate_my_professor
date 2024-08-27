# Rate My Professor

Rate My Professor is a web application designed to help students find the perfect professor for their needs by leveraging AI . It uses a combination of data stored in Pinecone, web scraping, and advanced search and recommendation systems to provide personalized professor recommendations based on user input criteria such as subject area, teaching style, difficulty level, and more. The project is divided into three main levels, each building upon the previous to offer a comprehensive solution for students.

## Getting Started

### Prerequisites

-   Python 3.x
-   Node.js
-   Flask
-   Pinecone
-   BeautifulSoup

### Installation

1.  Clone the repository:

```
   git clone https://github.com/yourusername/rate-my-professor.git
```

2.  Navigate to the project directory:

```
   cd rate-my-professor
```

3.  Install the required Python packages:

```
   pip install -r requirements.txt
```

4.  Set up your environment variables for Pinecone API key and any other necessary configurations.

### Usage

-   Run the Flask app  which is the backend api:

```
  python app.py
```
then

- Run the NextJS app:
```
	npm run dev
```

-   Access the application at  `http://localhost:4000`
