# RAG Pipeline Demo with AWS CDK

This project implements a Retrieval-Augmented Generation (RAG) pipeline using AWS services. The pipeline processes PDF documents through various stages to enable efficient document search and retrieval.

## Architecture Overview

![RAG Pipeline Architecture](docs/architecture.png)

### Components

1. **Storage Layer**
   - S3 Buckets:
     - `rag-demo-raw-pdf-v2`: Stores incoming PDF documents
     - `rag-demo-textract-json-v2`: Stores Textract output
   - Aurora PostgreSQL with pgvector extension for vector storage
   - DynamoDB table for execution logging

2. **Processing Pipeline**
   - AWS Step Functions orchestrates the workflow
   - AWS Lambda functions for each processing step
   - Amazon Textract for PDF text extraction
   - Amazon Bedrock for text embedding generation

### Pipeline Flow

1. PDF Upload → S3 Bucket
2. S3 Event → Trigger Lambda
3. Step Functions Workflow:
   - Initialize Database
   - Extract Text (Textract)
   - Validate Extraction
   - Generate Embeddings
   - Load to Vector Database

## Prerequisites

- AWS CDK CLI
- Python 3.11+
- Node.js (for CDK)
- AWS Account and configured credentials

## Setup Instructions

1. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy the stack**
   ```bash
   cdk deploy
   ```

4. **Configure S3 notifications**
   ```bash
   python configure_notifications.py
   ```

## Usage

### Uploading Documents

1. Place PDF documents in the `incoming/` prefix of the raw PDF bucket:
   ```bash
   aws s3 cp your-document.pdf s3://rag-demo-raw-pdf-v2/incoming/
   ```

2. The pipeline will automatically:
   - Extract text using Textract
   - Validate the extraction
   - Generate embeddings
   - Store results in the vector database

### Monitoring

1. **Step Functions Console**
   - Monitor workflow executions
   - View detailed execution logs
   - Track processing status

2. **CloudWatch Logs**
   - Each Lambda function logs to CloudWatch
   - View detailed processing logs
   - Monitor errors and performance

3. **DynamoDB Execution Log**
   - Track document processing status
   - View processing history
   - Query execution metadata

## Infrastructure Details

### IAM Roles and Permissions

Each component has dedicated IAM roles with least-privilege permissions:

- Lambda functions have specific roles for their tasks
- Step Functions state machine has permissions for Textract and Lambda invocation
- S3 buckets are configured with appropriate bucket policies

### Database Configuration

The Aurora PostgreSQL cluster:
- Uses Serverless v2 for cost optimization
- Has pgvector extension enabled
- Stores embeddings with HNSW index for efficient similarity search

### Security Features

- S3 buckets block public access
- Aurora cluster in private VPC subnets
- Secrets stored in AWS Secrets Manager
- IAM roles follow least-privilege principle

## Development

### Project Structure

```
demo_rag_provectus/
├── demo_provectus/
│   ├── rag_demo_stack.py   # Main CDK stack
│   └── constructs/         # CDK constructs
├── lambdas/
│   ├── init_db/           # Database initialization
│   ├── validate/          # Textract validation
│   ├── embed/            # Text embedding
│   └── load/             # Vector database loading
├── app.py                # CDK app entry point
└── configure_notifications.py  # Post-deployment setup
```

### Adding New Features

1. Modify the relevant Lambda function code in `lambdas/`
2. Update the CDK stack in `rag_demo_stack.py`
3. Deploy changes with `cdk deploy`

### Testing

1. **Unit Tests**
   ```bash
   pytest tests/unit
   ```

2. **Integration Tests**
   ```bash
   pytest tests/integration
   ```

## Troubleshooting

### Common Issues

1. **S3 Notification Issues**
   - Verify Lambda permissions
   - Check S3 bucket notification configuration
   - Ensure correct event types are configured

2. **Database Connection Issues**
   - Check VPC and security group settings
   - Verify database credentials in Secrets Manager
   - Ensure Lambda functions have proper VPC access

3. **Pipeline Processing Errors**
   - Check CloudWatch Logs for specific error messages
   - Verify input PDF format and size
   - Check Step Functions execution history

### Support

For issues and feature requests, please:
1. Check the troubleshooting guide above
2. Review CloudWatch Logs
3. Create an issue in the repository

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

- AWS CDK team for the excellent infrastructure as code framework
- pgvector team for the PostgreSQL vector extension
- AWS Textract and Bedrock teams for the ML services
