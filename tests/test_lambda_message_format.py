print("TESTING LAMBDA MESSAGE FORMAT")
print("=" * 50)

# Create a realistic message that matches what the Lambda sends
lambda_message = {
    "timestamp": "2025-05-24T08:30:45.123Z",
    "runId": "test-message-format-001",
    "status": "SUCCESS",
    "pipeline": "RAG Document Processing",
    "documentInfo": {
        "bucket": "rag-demo-raw-pdf-v2",
        "key": "medical_case_study_20250524_083045.pdf",
        "documentId": "doc-test-001"
    },
    "processingResults": {
        "chunkCount": 8,
        "processingTimeSeconds": 42.5,
        "textLength": 2340,
        "avgChunkSize": 292
    },
    "completionInfo": {
        "dataStored": "8 chunks",
        "searchReady": "Available"
    }
}

# Create email body that matches the CDK template exactly
status = lambda_message["status"]
processing_results = lambda_message.get('processingResults', {})
completion_info = lambda_message.get('completionInfo', {})

email_body = f'''
RAG Pipeline Notification

Status: {status}
Timestamp: {lambda_message.get('timestamp', 'Unknown')}
Run ID: {lambda_message.get('runId', 'Unknown')}

Document Information:
- Bucket: {lambda_message.get('documentInfo', {}).get('bucket', 'Unknown')}
- Key: {lambda_message.get('documentInfo', {}).get('key', 'Unknown')}

INGESTION SUCCESS SUMMARY:
Document processing completed successfully! All text has been processed, embedded, and stored in the vector database.

PROCESSING RESULTS:
- Pipeline: {lambda_message.get('pipeline', 'RAG Document Processing')}
- Chunks Created: {processing_results.get('chunkCount', 'Unknown')}
- Processing Time: {processing_results.get('processingTimeSeconds', 'Unknown')} seconds
- Document Size: {processing_results.get('textLength', 'Unknown')} characters
- Average Chunk Size: {processing_results.get('avgChunkSize', 'Unknown')} characters

STATUS: Ready for querying!
   The document has been successfully ingested and is now available for semantic search.
   Data Stored: {completion_info.get('dataStored', 'Unknown')}
   Search Ready: {completion_info.get('searchReady', 'Unknown')}

NEXT STEPS:
   You can now query this document using the RAG system's search functionality.
'''

subject = f"RAG Pipeline Notification - {status}"

print("MESSAGE DETAILS:")
print(f"   Subject: {subject}")
print(f"   Status: {status}")
print(f"   Processing Time: {processing_results.get('processingTimeSeconds')}s")

print(f"\nEMAIL BODY PREVIEW:")
print(email_body)

# Test sending with SNS
try:
    import boto3
    
    print(f"\nTESTING WITH LAMBDA FORMAT:")
    
    sns = boto3.client('sns')
    topic_arn = "arn:aws:sns:us-east-1:702645448228:rag-pipeline-notifications"
    
    response = sns.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=email_body
    )
    
    print(f"   Lambda format test email sent!")
    print(f"   SNS Message ID: {response['MessageId']}")
    print(f"   Topic: {topic_arn}")
    
except Exception as e:
    print(f"   Failed to send lambda format test: {str(e)}")
    print(f"   Error details: {type(e).__name__}")

# Try a very simple format as backup
print(f"\nTRYING SIMPLIFIED FORMAT:")
try:
    simple_response = sns.publish(
        TopicArn=topic_arn,
        Subject="RAG Pipeline Test - Simple Format",
        Message="This is a simplified test message to verify email delivery is working."
    )
    
    print(f"   Simple format sent: {simple_response['MessageId']}")
except Exception as simple_error:
    print(f"   Even simple format failed: {str(simple_error)}")

print(f"\nDIAGNOSIS:")
print("The message format above should match exactly what Lambda sends.")
print("If you don't receive this email, the issue is likely:")
print("1. SNS topic configuration")
print("2. Email subscription not confirmed")
print("3. Email filtering/spam detection") 