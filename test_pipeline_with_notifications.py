#!/usr/bin/env python3
"""
Test the RAG pipeline with SQS notifications
"""

import boto3
import json
import time
import uuid
import threading

def monitor_sqs_notifications(duration=300):
    """Monitor SQS notifications in background"""
    
    sqs = boto3.client('sqs')
    
    # Get notification queue URL
    queues = sqs.list_queues(QueueNamePrefix='rag-pipeline-notifications')
    main_queue_url = None
    
    for queue_url in queues.get('QueueUrls', []):
        if queue_url.endswith('rag-pipeline-notifications'):
            main_queue_url = queue_url
            break
    
    if not main_queue_url:
        print("❌ Notification queue not found")
        return
    
    print(f"\n📡 Starting SQS monitoring for {duration} seconds...")
    print(f"🔗 Queue: {main_queue_url}")
    
    start_time = time.time()
    messages_received = 0
    
    while time.time() - start_time < duration:
        try:
            response = sqs.receive_message(
                QueueUrl=main_queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=10,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            
            for message in messages:
                messages_received += 1
                
                try:
                    body = json.loads(message['Body'])
                    
                    status = body.get('status', 'UNKNOWN')
                    run_id = body.get('runId', 'unknown')
                    timestamp = body.get('timestamp', 'unknown')
                    document_info = body.get('documentInfo', {})
                    
                    status_icon = '✅' if status == 'SUCCESS' else '❌' if status == 'FAILED' else '❓'
                    
                    print(f"\n{status_icon} SQS NOTIFICATION #{messages_received}")
                    print(f"   🕐 Time: {timestamp}")
                    print(f"   🆔 Run ID: {run_id[:12]}...")
                    print(f"   📊 Status: {status}")
                    print(f"   📄 Document: {document_info.get('key', 'unknown')}")
                    
                    if status == 'SUCCESS' and 'processingResults' in body:
                        results = body['processingResults']
                        print(f"   📈 Results: {results.get('chunkCount', 0)} chunks, {results.get('textLength', 0)} chars")
                    
                    if status == 'FAILED' and 'error' in body:
                        print(f"   ❌ Error: {body['error']}")
                    
                    # Delete message
                    sqs.delete_message(
                        QueueUrl=main_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                except Exception as e:
                    print(f"⚠️ Error processing SQS message: {str(e)}")
        
        except Exception as e:
            if 'QueueDoesNotExist' not in str(e):
                print(f"⚠️ SQS monitoring error: {str(e)}")
            time.sleep(5)
    
    print(f"\n📊 SQS monitoring complete: {messages_received} notifications received")

def test_pipeline_with_notifications():
    """Test the pipeline and monitor SQS notifications"""
    
    print("🧪 Testing RAG Pipeline with SQS Notifications")
    print("=" * 70)
    
    # Initialize clients
    sfn = boto3.client('stepfunctions')
    
    # Find the state machine
    state_machines = sfn.list_state_machines()
    rag_state_machine = None
    
    for sm in state_machines['stateMachines']:
        if 'StateMachine' in sm['name'] or 'EtlStateMachine' in sm['name']:
            rag_state_machine = sm['stateMachineArn']
            break
    
    if not rag_state_machine:
        print("❌ RAG state machine not found!")
        return
    
    print(f"✅ Found state machine: {rag_state_machine.split('/')[-1]}")
    
    # Generate unique run ID
    run_id = str(uuid.uuid4())
    
    # Create test input with runId
    test_input = {
        "bucket": "rag-demo-raw-pdf-v2",
        "key": "small_clinical_case_study.pdf",
        "runId": run_id
    }
    
    print(f"🚀 Starting execution with runId: {run_id}")
    print(f"📄 Processing: s3://{test_input['bucket']}/{test_input['key']}")
    
    # Start SQS monitoring in background
    monitor_thread = threading.Thread(
        target=monitor_sqs_notifications, 
        args=(300,),  # Monitor for 5 minutes
        daemon=True
    )
    monitor_thread.start()
    
    try:
        # Start execution
        response = sfn.start_execution(
            stateMachineArn=rag_state_machine,
            input=json.dumps(test_input)
        )
        
        execution_arn = response['executionArn']
        execution_name = execution_arn.split(':')[-1]
        
        print(f"✅ Execution started: {execution_name}")
        print(f"🔗 Execution ARN: {execution_arn}")
        
        # Monitor execution
        print(f"\n⏳ Monitoring execution progress...")
        
        max_wait = 300  # 5 minutes
        wait_time = 0
        
        while wait_time < max_wait:
            exec_response = sfn.describe_execution(executionArn=execution_arn)
            status = exec_response['status']
            
            print(f"   📊 Step Functions Status: {status} (waited {wait_time}s)")
            
            if status == 'SUCCEEDED':
                print(f"✅ Execution completed successfully!")
                break
            elif status == 'FAILED':
                print(f"❌ Execution failed!")
                print(f"   Error: {exec_response.get('error', 'Unknown error')}")
                break
            elif status == 'TIMED_OUT':
                print(f"⏰ Execution timed out!")
                break
            
            time.sleep(20)
            wait_time += 20
        
        if wait_time >= max_wait:
            print(f"⏰ Stopped monitoring after {max_wait} seconds")
        
        # Give SQS monitoring a bit more time
        print(f"\n⏳ Waiting for SQS notifications...")
        time.sleep(30)
        
        # View execution logs
        print(f"\n📋 EXECUTION LOGS:")
        print("=" * 40)
        
        # Import and use the log viewer
        import sys
        sys.path.append('.')
        from view_execution_logs import view_execution_logs
        
        # View logs for this specific run
        view_execution_logs(run_id=run_id, show_details=True)
        
        print(f"\n🎯 TESTING SUMMARY:")
        print(f"   🆔 Run ID: {run_id}")
        print(f"   📊 Step Functions Status: {status}")
        print(f"   📡 SQS Monitoring: Active (check output above)")
        print(f"   📋 Execution Logs: Available in DynamoDB")
        
        return run_id
        
    except Exception as e:
        print(f"❌ Error starting execution: {str(e)}")
        return None

if __name__ == "__main__":
    test_pipeline_with_notifications() 