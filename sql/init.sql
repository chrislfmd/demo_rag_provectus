-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for storing embeddings
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id UUID PRIMARY KEY,
    source_s3 TEXT NOT NULL,
    chunk_no INTEGER NOT NULL,
    embedding vector(1536),  -- Titan model produces 1536-dimensional vectors
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Add index for similarity search
    -- Using HNSW index for better performance
    -- https://github.com/pgvector/pgvector#hnsw
    INDEX embedding_idx USING hnsw (embedding vector_cosine_ops)
);

-- Add composite index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_source_chunk ON rag_embeddings(source_s3, chunk_no);

-- Grant necessary permissions
GRANT SELECT, INSERT ON rag_embeddings TO pgadmin; 