import boto3
import json

print("🧪 TESTING LAMBDA MESSAGE FORMAT")
print("=" * 60)

# Recreate the exact message format that our Lambda sends
# Based on our successful pipeline run
test_message_body = {
    "timestamp": "2025-05-24T12:12:27.000000Z",
    "runId": "7a79cc4b-a626-42d5-a099-a34039c01906",
    "status": "SUCCESS",
    "pipeline": "RAG Document Processing",
    "documentInfo": {
        "bucket": "rag-demo-raw-pdf-v2",
        "key": "test_success_notification_20250524_081217.txt",
        "fileName": "test_success_notification_20250524_081217.txt"
    },
    "processingResults": {
        "chunkCount": 3,
        "textLength": 143,
        "processingTimeSeconds": 2.5,
        "avgChunkSize": 47
    },
    "completionInfo": {
        "dataStored": True,
        "searchReady": True
    }
}

# Recreate the exact email body format from our Lambda
status = test_message_body.get('status', 'UNKNOWN')
processing_results = test_message_body.get('processingResults', {})
completion_info = test_message_body.get('completionInfo', {})

email_body = f'''
RAG Pipeline Notification

Status: {status}
Timestamp: {test_message_body.get('timestamp', 'Unknown')}
Run ID: {test_message_body.get('runId', 'Unknown')}

Document Information:
- Bucket: {test_message_body.get('documentInfo', {}).get('bucket', 'Unknown')}
- Key: {test_message_body.get('documentInfo', {}).get('key', 'Unknown')}

'''

email_body += f'''
🎉 INGESTION SUCCESS SUMMARY:
Document processing completed successfully! All text has been processed, embedded, and stored in the vector database.

📊 PROCESSING RESULTS:
- Pipeline: {test_message_body.get('pipeline', 'RAG Document Processing')}
- Chunks Created: {processing_results.get('chunkCount', 'Unknown')}
- Processing Time: {processing_results.get('processingTimeSeconds', 'Unknown')} seconds
- Document Size: {processing_results.get('textLength', 'Unknown')} characters
- Average Chunk Size: {processing_results.get('avgChunkSize', 'Unknown')} characters

✅ STATUS: Ready for querying! 
   The document has been successfully ingested and is now available for semantic search.
   Data Stored: {completion_info.get('dataStored', 'Unknown')}
   Search Ready: {completion_info.get('searchReady', 'Unknown')}

💡 NEXT STEPS:
   You can now query this document using the RAG system's search functionality.
'''

subject = f"📡 RAG Pipeline Notification - {status}"

print("📋 MESSAGE DETAILS:")
print(f"Subject: {subject}")
print(f"Message length: {len(email_body)} characters")

print(f"\n📧 EMAIL BODY PREVIEW:")
print("=" * 40)
print(email_body[:500] + "..." if len(email_body) > 500 else email_body)
print("=" * 40)

# Test sending this exact format
sns = boto3.client('sns')
notification_topic_arn = "arn:aws:sns:us-east-1:702645448228:rag-pipeline-notifications"

try:
    print(f"\n🧪 SENDING TEST WITH LAMBDA FORMAT:")
    response = sns.publish(
        TopicArn=notification_topic_arn,
        Subject=subject,
        Message=email_body
    )
    print(f"   ✅ Lambda format test email sent!")
    print(f"   📧 SNS Message ID: {response['MessageId']}")
    print(f"   ⏰ Check your email in 1-5 minutes")
    
except Exception as e:
    print(f"   ❌ Failed to send lambda format test: {str(e)}")
    print(f"   🔍 Error details: {type(e).__name__}")
    
    # Try with simpler format
    print(f"\n🔧 TRYING SIMPLIFIED FORMAT:")
    simple_message = f"RAG Pipeline Test - Status: {status}\nRun ID: {test_message_body.get('runId')}\nDocument: {test_message_body.get('documentInfo', {}).get('key')}"
    
    try:
        simple_response = sns.publish(
            TopicArn=notification_topic_arn,
            Subject=f"Simple Test - {status}",
            Message=simple_message
        )
        print(f"   ✅ Simple format sent: {simple_response['MessageId']}")
    except Exception as simple_error:
        print(f"   ❌ Even simple format failed: {str(simple_error)}")

print(f"\n🔍 DIAGNOSIS:")
print(f"   If you receive the Lambda format test email, then the issue was timing/delivery")
print(f"   If you don't receive it, there's a formatting issue with the Lambda message")
print(f"   The emojis or special characters might be causing problems") 