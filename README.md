# RAG Document Processing Pipeline Demo

A production-ready **Retrieval-Augmented Generation (RAG)** pipeline built with AWS services, featuring comprehensive document processing, vector embeddings, and **robust SQS notification system**.

## 🚀 New Features: Comprehensive SQS Notification System

### 📡 Real-time Pipeline Notifications
- **4 SQS Queues**: Main notifications, success-only, errors-only, and dead letter queue
- **Direct Error Notifications**: Lambda functions send immediate notifications when failures occur
- **Comprehensive Monitoring**: Real-time notification monitoring with detailed error tracking
- **Bypass Complex Step Functions**: Reliable notifications independent of Step Functions error handling

### 📊 Notification Features
- **Success Notifications**: Document processing completion with metrics (chunks, processing time, text length)
- **Error Notifications**: Detailed failure information with step identification and error messages  
- **Processing Metadata**: runId tracking, timestamps, document information, and retry indicators
- **Message Attributes**: SQS message filtering by status, pipeline, and failed step

## 🏗️ Architecture Overview

```
📄 S3 Upload → 🔄 Step Functions → 📊 Textract → 🧠 Bedrock → 🗄️ DynamoDB
     ↓              ↓                ↓            ↓            ↓
📡 Trigger     📡 Notifications   📡 Error    📡 Processing 📡 Success
```

### Core Components
- **S3**: Document storage with automatic pipeline triggering  
- **Textract**: Text extraction from PDFs and images
- **Bedrock**: Vector embeddings using Amazon Titan models
- **DynamoDB**: Vector storage with similarity search capabilities
- **Step Functions**: Workflow orchestration with error handling
- **SQS**: Real-time notifications for all pipeline events
- **Lambda**: Serverless processing with direct notification capabilities

## 📋 SQS Queues

| Queue Name | Purpose | Use Case |
|------------|---------|----------|
| `rag-pipeline-notifications` | Main notifications | All pipeline events |
| `rag-pipeline-success` | Success only | Successful completions |
| `rag-pipeline-errors` | Errors only | Failed operations |
| `rag-pipeline-notifications-dlq` | Dead letter | Failed notifications |

## 🛠️ Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Node.js 18+ and AWS CDK v2
- Python 3.11+

### Deployment
```bash
# Clone and install dependencies
git clone <repository>
cd demo_rag_provectus
npm install

# Deploy infrastructure
cdk deploy --require-approval never

# Test the pipeline
aws s3 cp your_document.pdf s3://rag-demo-raw-pdf-v2/incoming/
```

### Monitor Notifications
```bash
# Real-time notification monitoring
python monitor_sqs_notifications.py --queue notifications

# Monitor specific queue types
python monitor_sqs_notifications.py --queue success
python monitor_sqs_notifications.py --queue errors
```

## 📊 Usage Examples

### Document Processing
```bash
# Upload document to trigger pipeline
aws s3 cp medical_report.pdf s3://rag-demo-raw-pdf-v2/incoming/

# Monitor processing notifications
python monitor_sqs_notifications.py --max-messages 5
```

### Query Documents
```python
# Query the processed documents
python demo_rag_system.py

# Sample queries:
# - "What are the patient's cardiac symptoms?"
# - "Show me laboratory test results"
# - "What medications were prescribed?"
```

### View Execution Logs
```python
# View pipeline execution history
python view_execution_logs.py --show-details

# View specific execution
python view_execution_logs.py --run-id <your-run-id>
```

## 📡 Notification System Details

### Success Notification Example
```json
{
  "timestamp": "2025-05-23T10:30:45.123Z",
  "runId": "abc-123-def",
  "status": "SUCCESS",
  "pipeline": "RAG Document Processing",
  "documentInfo": {
    "bucket": "rag-demo-raw-pdf-v2",
    "key": "incoming/medical_report.pdf",
    "documentId": "doc-456-xyz"
  },
  "processingResults": {
    "chunkCount": 8,
    "textLength": 2340,
    "processingTimeSeconds": 45.2
  }
}
```

### Error Notification Example
```json
{
  "timestamp": "2025-05-23T10:35:12.456Z", 
  "runId": "abc-123-def",
  "status": "FAILED",
  "pipeline": "RAG Document Processing",
  "documentInfo": {
    "bucket": "rag-demo-raw-pdf-v2",
    "key": "incoming/invalid_file.txt"
  },
  "errorDetails": {
    "failedStep": "Validate",
    "errorMessage": "Textract job failed: INVALID_IMAGE_TYPE",
    "retryable": false
  }
}
```

## 🔧 Configuration

### Environment Variables
- `NOTIFICATION_QUEUE_URL`: Main SQS notification queue
- `SUCCESS_QUEUE_URL`: Success-only notifications  
- `ERROR_QUEUE_URL`: Error-only notifications
- `TABLE_NAME`: DynamoDB table for vector storage
- `EXEC_LOG_TABLE`: Execution logging table

## 📈 Performance & Metrics

### Current Performance
- **Processing Time**: 3-5 minutes for typical documents
- **Success Rate**: 95%+ for valid PDF documents
- **Notification Delivery**: <30 seconds from event occurrence
- **Cost**: ~$0.10 per document processed

### Monitoring Tools
- **Real-time SQS monitoring**: `monitor_sqs_notifications.py`
- **CloudWatch metrics**: Lambda execution times, error rates
- **DynamoDB insights**: Execution logs with 30-day TTL
- **Step Functions console**: Visual workflow monitoring

## 🚨 Known Issues & Limitations

### Current Limitations
- **File Types**: PDF and image files only (Textract limitation)
- **File Size**: 500MB maximum (Textract limitation)  
- **Processing Time**: Large documents may take 15+ minutes
- **Step Functions Error Handling**: Complex error handling patterns unreliable

### Workarounds Implemented
- ✅ **Direct SQS notifications**: Bypass Step Functions error handling issues
- ✅ **Retry logic**: Built-in retries for Textract operations
- ✅ **Timeout handling**: Proper timeout management for long operations
- ✅ **Cost optimization**: Sample data creation to reduce testing costs

## 🗂️ Project Structure

```
demo_rag_provectus/
├── demo_provectus/              # CDK infrastructure code
│   └── rag_demo_stack.py       # Main CDK stack with SQS configuration
├── lambdas/                     # Lambda function code
│   ├── common/                  # Shared utilities
│   │   └── exec_logger.py      # Execution logging utility
│   ├── init_db/                # Database initialization
│   ├── validate/               # Document validation with SQS notifications
│   ├── embed/                  # Text embedding generation  
│   ├── load/                   # Vector storage in DynamoDB
│   ├── query/                  # Document querying
│   └── notify/                 # SQS notification handler
├── monitor_sqs_notifications.py # Real-time SQS monitoring tool
├── demo_rag_system.py          # End-to-end system demonstration
├── view_execution_logs.py      # Execution log viewer
└── TODO.md                     # Comprehensive improvement roadmap
```

## 🔮 Future Enhancements

See [TODO.md](TODO.md) for comprehensive roadmap including:
- **Enhanced Monitoring**: CloudWatch dashboards and alarms
- **Additional Integrations**: Slack/Teams notifications
- **Performance Optimization**: Batch processing and cost reduction
- **Advanced Features**: Machine learning for predictive failure detection

## 🤝 Contributing

1. Check [TODO.md](TODO.md) for current priorities
2. Focus on immediate priority items (SQS notification improvements)
3. Test thoroughly with the monitoring tools provided
4. Ensure proper error handling and notification coverage

## 📄 License

This project is a demonstration of AWS RAG pipeline capabilities with production-ready notification systems.

---

**Latest Update**: Implemented comprehensive SQS notification system with direct Lambda error notifications, bypassing Step Functions error handling limitations for reliable pipeline monitoring.
