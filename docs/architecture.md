```mermaid
graph TD
    %% Storage Components
    S3Raw[S3 Raw PDF Bucket] --> TriggerLambda[Trigger Lambda]
    S3Textract[S3 Textract JSON Bucket]
    DDB[(DynamoDB Execution Log)]
    Aurora[(Aurora PostgreSQL + pgvector)]

    %% Pipeline Components
    TriggerLambda --> |Start Execution| StepFunctions{Step Functions}
    
    %% Step Functions Flow
    StepFunctions --> |1| InitDB[Initialize DB Lambda]
    StepFunctions --> |2| Textract[Amazon Textract]
    StepFunctions --> |3| ValidateLambda[Validate Lambda]
    StepFunctions --> |4| EmbedLambda[Embed Lambda]
    StepFunctions --> |5| LoadLambda[Load Lambda]

    %% Service Connections
    Textract --> S3Textract
    ValidateLambda --> S3Textract
    EmbedLambda --> |Bedrock API| Bedrock[Amazon Bedrock]
    LoadLambda --> Aurora
    
    %% Logging Flow
    InitDB --> |Log Status| DDB
    ValidateLambda --> |Log Status| DDB
    EmbedLambda --> |Log Status| DDB
    LoadLambda --> |Log Status| DDB

    %% Styling
    classDef storage fill:#2c3e50,stroke:#2c3e50,color:white
    classDef lambda fill:#e67e22,stroke:#d35400,color:white
    classDef service fill:#2980b9,stroke:#2573a7,color:white
    classDef orchestrator fill:#8e44ad,stroke:#8e44ad,color:white

    class S3Raw,S3Textract,DDB,Aurora storage
    class TriggerLambda,InitDB,ValidateLambda,EmbedLambda,LoadLambda lambda
    class Textract,Bedrock service
    class StepFunctions orchestrator

    %% Subgraph for Storage Layer
    subgraph Storage Layer
        S3Raw
        S3Textract
        DDB
        Aurora
    end

    %% Subgraph for Processing Layer
    subgraph Processing Layer
        TriggerLambda
        StepFunctions
        InitDB
        Textract
        ValidateLambda
        EmbedLambda
        LoadLambda
        Bedrock
    end
```

# Architecture Diagram

The above diagram shows the complete RAG (Retrieval-Augmented Generation) pipeline architecture. Here's a detailed breakdown:

## Storage Layer
- **S3 Buckets**: 
  - Raw PDF bucket for document ingestion
  - Textract JSON bucket for extracted text storage
- **DynamoDB**: Execution logging and status tracking
- **Aurora PostgreSQL**: Vector storage with pgvector extension

## Processing Layer
1. **Document Upload Flow**:
   - PDF uploaded to S3 Raw bucket
   - Triggers Lambda function
   - Lambda starts Step Functions execution

2. **Step Functions Workflow**:
   - Initialize database (if needed)
   - Extract text using Textract
   - Validate extraction results
   - Generate embeddings via Bedrock
   - Load vectors into Aurora

3. **Monitoring and Logging**:
   - All Lambda functions log to DynamoDB
   - Status tracking throughout pipeline
   - Error handling at each step

## Key Features
- Serverless architecture
- Event-driven processing
- Scalable vector storage
- Comprehensive logging
- Error handling and retry mechanisms 