# DynamoDB Logging in RAG Pipeline

This document explains what data is being logged to DynamoDB in your RAG (Retrieval-Augmented Generation) pipeline system.

## Overview

Your system uses **two DynamoDB tables** for different purposes:

1. **`Documents` table** - Stores the actual document content, chunks, and vector embeddings
2. **`ExecLogV2` table** - Tracks pipeline execution metadata and debugging information

## Table 1: `Documents` Table

### Purpose
Stores the processed document content, chunks, and vector embeddings for semantic search.

### Table Structure
- **Partition Key**: `documentId` (String) - Unique identifier for each document
- **Sort Key**: `chunkId` (String) - Identifies individual chunks or metadata records
- **Encryption**: Customer-managed KMS encryption
- **Billing**: Pay-per-request

### Data Stored

#### Document Metadata Record
When a document is first processed, an initial metadata record is created:

```json
{
  "documentId": "abc-123-def-456",
  "chunkId": "metadata",
  "filename": "medical_report.pdf",
  "status": "initialized", // later updated to "loaded"
  "createdAt": "2025-05-24T10:30:45.123Z",
  "lastUpdated": "2025-05-24T10:32:15.456Z",
  "chunkCount": 8,
  "metadata": {
    "bucket": "rag-demo-raw-pdf-v2", 
    "key": "incoming/medical_report.pdf"
  }
}
```

#### Document Chunks with Embeddings
Each text chunk from the document is stored with its vector embedding:

```json
{
  "documentId": "abc-123-def-456",
  "chunkId": "chunk_0",
  "content": "Patient presents with chest pain and shortness of breath...",
  "embedding": [0.1234, -0.5678, 0.9012, ...], // 384-dimensional vector
  "metadata": {
    "chunkIndex": 0,
    "chunkLength": 245,
    "embeddingDimension": 384,
    "confidence": 95.5,
    "timestamp": "2025-05-24T10:32:10.789Z"
  }
}
```

## Table 2: `ExecLogV2` Table (Execution Logging)

### Purpose
Tracks the execution flow and status of each pipeline run for debugging and monitoring.

### Table Structure
- **Partition Key**: `runId` (String) - Unique identifier for each pipeline execution
- **Sort Key**: `stepTimestamp` (String) - Combines step name and timestamp (e.g., "InitDB_2025-05-24T10:30:45.123Z")
- **TTL**: 30 days (automatic cleanup)
- **Encryption**: Customer-managed KMS encryption
- **Billing**: Pay-per-request

### Data Logged

Each Lambda function logs its execution steps:

#### Step Start Logging
```json
{
  "runId": "pipeline-run-789",
  "stepTimestamp": "InitDB_2025-05-24T10:30:45.123Z",
  "documentId": "doc-456-xyz",
  "step": "InitDB",
  "status": "STARTED",
  "timestamp": "2025-05-24T10:30:45.123Z",
  "message": "Initializing document record for s3://rag-demo-raw-pdf-v2/medical_report.pdf",
  "ttl": 1719302445 // Unix timestamp for 30 days from now
}
```

#### Step Success Logging
```json
{
  "runId": "pipeline-run-789",
  "stepTimestamp": "InitDB_2025-05-24T10:30:47.456Z",
  "documentId": "doc-456-xyz", 
  "step": "InitDB",
  "status": "SUCCESS",
  "timestamp": "2025-05-24T10:30:47.456Z",
  "message": "Document record created successfully in table Documents",
  "ttl": 1719302447
}
```

#### Step Failure Logging
```json
{
  "runId": "pipeline-run-789",
  "stepTimestamp": "Validate_2025-05-24T10:31:15.789Z",
  "documentId": "doc-456-xyz",
  "step": "Validate", 
  "status": "FAILED",
  "timestamp": "2025-05-24T10:31:15.789Z",
  "message": "Validation failed: Textract job failed: INVALID_IMAGE_TYPE",
  "ttl": 1719302475
}
```

## Pipeline Steps That Log to DynamoDB

### 1. InitDB Step
- **Purpose**: Creates initial document record
- **Logs**: 
  - STARTED: When document initialization begins
  - SUCCESS: When document record is created in Documents table
  - FAILED: If document creation fails

### 2. Validate Step  
- **Purpose**: Simulates Textract text extraction
- **Logs**:
  - STARTED: When text extraction simulation begins
  - SUCCESS: When text blocks are successfully extracted/simulated
  - FAILED: If validation fails (e.g., unsupported file type)

### 3. Embed Step
- **Purpose**: Generates vector embeddings from text
- **Logs**:
  - STARTED: When embedding generation begins
  - SUCCESS: When embeddings are successfully created
  - FAILED: If embedding generation fails

### 4. Load Step
- **Purpose**: Stores chunks and embeddings in Documents table
- **Logs**:
  - STARTED: When loading chunks begins
  - SUCCESS: When all chunks are stored successfully
  - FAILED: If chunk storage fails

### 5. Notify Step
- **Purpose**: Sends notifications via SQS/SNS
- **Logs**:
  - STARTED: When notification sending begins
  - SUCCESS: When notifications are sent successfully
  - FAILED: If notification sending fails

## Monitoring and Debugging

### What You Can Track

1. **Pipeline Success Rate**: Count of SUCCESS vs FAILED statuses
2. **Step Performance**: Time between STARTED and SUCCESS/FAILED for each step
3. **Error Patterns**: Common failure points and error messages
4. **Document Processing**: Which documents succeed/fail and why
5. **System Health**: Recent execution trends

### Useful Queries

#### Check Recent Pipeline Runs
```python
# Get all steps for a specific run
response = table.query(
    KeyConditionExpression=Key('runId').eq('pipeline-run-789')
)
```

#### Check Failed Steps
```python
# Get failed steps across all runs
response = table.scan(
    FilterExpression=Attr('status').eq('FAILED')
)
```

#### Check Step Performance
```python
# Get all InitDB steps to analyze performance
response = table.scan(
    FilterExpression=Attr('step').eq('InitDB')
)
```

## Data Retention

- **Documents Table**: No TTL - data persists until manually deleted
- **ExecLogV2 Table**: 30-day TTL - logs automatically deleted after 30 days
- **Encryption**: Both tables use customer-managed KMS keys
- **Backups**: Handled by AWS DynamoDB point-in-time recovery

## Key Benefits

1. **Full Pipeline Traceability**: Every execution step is logged with timestamps
2. **Error Debugging**: Detailed error messages help identify issues
3. **Performance Monitoring**: Execution timing data for optimization
4. **Document Tracking**: Complete history of what documents were processed
5. **Automatic Cleanup**: Logs automatically expire to control costs

This logging system provides comprehensive visibility into your RAG pipeline operations while maintaining the actual document content for semantic search functionality. 