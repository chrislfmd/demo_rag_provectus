#!/usr/bin/env python3
"""
Test the RAG pipeline with execution logging
"""

import boto3
import json
import time
import uuid

def test_pipeline_with_logging():
    """Test the pipeline and view execution logs"""
    
    print("🧪 Testing RAG Pipeline with Execution Logging")
    print("=" * 60)
    
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
        print("Available state machines:")
        for sm in state_machines['stateMachines']:
            print(f"   - {sm['name']}")
        return
    
    print(f"✅ Found state machine: {rag_state_machine.split('/')[-1]}")
    
    # Create test input
    test_input = {
        "bucket": "rag-demo-raw-pdf-v2",
        "key": "small_clinical_case_study.pdf",
        "runId": str(uuid.uuid4())
    }
    
    print(f"🚀 Starting execution with runId: {test_input['runId']}")
    print(f"📄 Processing: s3://{test_input['bucket']}/{test_input['key']}")
    
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
        
        max_wait = 600  # 10 minutes
        wait_time = 0
        
        while wait_time < max_wait:
            exec_response = sfn.describe_execution(executionArn=execution_arn)
            status = exec_response['status']
            
            print(f"   📊 Status: {status} (waited {wait_time}s)")
            
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
            
            time.sleep(30)
            wait_time += 30
        
        if wait_time >= max_wait:
            print(f"⏰ Stopped monitoring after {max_wait} seconds")
        
        # View execution logs
        print(f"\n📋 EXECUTION LOGS:")
        print("=" * 40)
        
        # Import and use the log viewer
        import sys
        sys.path.append('.')
        from view_execution_logs import view_execution_logs
        
        # View logs for this specific run
        view_execution_logs(run_id=test_input['runId'], show_details=True)
        
        return test_input['runId']
        
    except Exception as e:
        print(f"❌ Error starting execution: {str(e)}")
        return None

if __name__ == "__main__":
    test_pipeline_with_logging() 