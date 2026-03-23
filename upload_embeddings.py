import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Connect to NeonDB
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Create pgvector extension
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Create embeddings table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL,
        embedding vector(1536),
        source VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

# Create index for faster searches
cursor.execute("""
    CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
    ON embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
""")

conn.commit()

# Read knowledge base files
knowledge_base_path = Path("knowledge_base")
files = list(knowledge_base_path.glob("*.txt"))

if not files:
    print("No .txt files found in knowledge_base folder!")
    sys.exit(1)

print(f"Found {len(files)} files to process")

# Process each file
for file_path in files:
    print(f"\nProcessing: {file_path.name}")
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Split content into chunks (roughly 500 characters each)
    chunk_size = 500
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    print(f"  Creating {len(chunks)} chunks...")
    
    # Generate embeddings for each chunk
    embeddings_data = []
    for i, chunk in enumerate(chunks):
        if chunk.strip():  # Skip empty chunks
            try:
                response = client.embeddings.create(
                    input=chunk,
                    model="text-embedding-3-small"
                )
                embedding = response.data[0].embedding
                embeddings_data.append((chunk, embedding, file_path.name))
                print(f"  Chunk {i+1}/{len(chunks)} embedded")
            except Exception as e:
                print(f"  Error embedding chunk {i+1}: {e}")
    
    # Insert into database
    if embeddings_data:
        print(f"  Inserting {len(embeddings_data)} embeddings into database...")
        execute_values(
            cursor,
            "INSERT INTO embeddings (content, embedding, source) VALUES %s",
            embeddings_data
        )
        conn.commit()
        print(f"  ✓ Successfully inserted {len(embeddings_data)} embeddings")

print("\n✓ All files processed and uploaded to NeonDB!")
cursor.close()
conn.close()
