import boto3
import json
import uuid
from datetime import datetime

# Create a small test file and trigger the pipeline
s3 = boto3.client('s3')
stepfunctions = boto3.client('stepfunctions')

# Create a simple test document
test_content = '''
This is a test document for RAG pipeline verification.
The document contains some basic medical information about patient care and treatment protocols.
'''

# Upload to S3
bucket_name = 'rag-demo-raw-pdf-v2'
file_key = f'test_success_notification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

s3.put_object(
    Bucket=bucket_name,
    Key=file_key,
    Body=test_content.encode('utf-8'),
    ContentType='text/plain'
)

print(f'Uploaded test file: s3://{bucket_name}/{file_key}')

# Trigger pipeline
state_machine_arn = 'arn:aws:states:us-east-1:702645448228:stateMachine:StateMachineEtlStateMachine241248B6-nmg8xN9bET1J'

input_payload = {
    'bucket': bucket_name,
    'key': file_key,
    'runId': str(uuid.uuid4())
}

response = stepfunctions.start_execution(
    stateMachineArn=state_machine_arn,
    input=json.dumps(input_payload)
)

print(f'Started execution: {response["executionArn"]}')
print(f'Run ID: {input_payload["runId"]}') 