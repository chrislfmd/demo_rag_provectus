import boto3
from datetime import datetime, timedelta

print("🔍 CHECKING RECENT PIPELINE EXECUTIONS")
print("=" * 60)

stepfunctions = boto3.client('stepfunctions')
state_machine_arn = "arn:aws:states:us-east-1:702645448228:stateMachine:StateMachineEtlStateMachine241248B6-nmg8xN9bET1J"

# Check all recent executions (last 10 minutes)
try:
    executions = stepfunctions.list_executions(
        stateMachineArn=state_machine_arn,
        maxResults=10
    )
    
    print(f"📊 Found {len(executions['executions'])} recent executions:")
    
    now = datetime.now(executions['executions'][0]['startDate'].tzinfo) if executions['executions'] else datetime.now()
    
    for i, execution in enumerate(executions['executions']):
        execution_name = execution['name']
        status = execution['status']
        start_time = execution['startDate']
        
        # Calculate time ago
        time_ago = now - start_time
        time_ago_str = f"{time_ago.total_seconds():.0f}s ago"
        
        print(f"\n{i+1}. Execution: {execution_name}")
        print(f"   Status: {status}")
        print(f"   Started: {start_time} ({time_ago_str})")
        
        # Check if this might be our PDF execution
        if time_ago.total_seconds() < 300:  # Last 5 minutes
            print(f"   🔍 Checking details for recent execution...")
            
            try:
                details = stepfunctions.describe_execution(
                    executionArn=execution['executionArn']
                )
                
                # Check input for our filename
                import json
                input_data = json.loads(details['input'])
                bucket = input_data.get('bucket', '')
                key = input_data.get('key', '')
                run_id = input_data.get('runId', '')
                
                print(f"   📄 File: s3://{bucket}/{key}")
                print(f"   🆔 Run ID: {run_id}")
                
                # Check if this is our medical case study
                if 'medical_case_study_20250524_083401' in key:
                    print(f"   ✅ FOUND OUR EXECUTION!")
                    
                    if status == 'SUCCEEDED':
                        duration = details['stopDate'] - details['startDate']
                        print(f"   🎉 Status: COMPLETED SUCCESSFULLY")
                        print(f"   ⏱️  Duration: {duration}")
                        print(f"   📧 Email notification should have been sent!")
                        
                    elif status == 'FAILED':
                        print(f"   ❌ Status: FAILED")
                        print(f"   Error: {details.get('error', 'Unknown')}")
                        print(f"   Cause: {details.get('cause', 'Unknown')}")
                        
                    elif status == 'RUNNING':
                        print(f"   🔄 Status: STILL RUNNING")
                        print(f"   ⏳ Execution in progress...")
                        
            except Exception as e:
                print(f"   ❌ Error checking execution details: {str(e)}")
                
except Exception as e:
    print(f"❌ Error listing executions: {str(e)}")

# Also check if S3 event notification is configured
print(f"\n🔧 CHECKING S3 EVENT NOTIFICATION:")
s3 = boto3.client('s3')
bucket_name = 'rag-demo-raw-pdf-v2'

try:
    notification_config = s3.get_bucket_notification_configuration(Bucket=bucket_name)
    
    if 'LambdaConfigurations' in notification_config:
        lambda_configs = notification_config['LambdaConfigurations']
        print(f"   ✅ Found {len(lambda_configs)} Lambda notification(s)")
        
        for config in lambda_configs:
            function_arn = config['LambdaFunctionArn']
            events = config['Events']
            print(f"   📋 Function: {function_arn.split(':')[-1]}")
            print(f"   📋 Events: {events}")
            
    else:
        print(f"   ⚠️  No Lambda configurations found")
        
except Exception as e:
    print(f"   ❌ Error checking S3 notifications: {str(e)}")

print(f"\n💡 NEXT STEPS:")
print(f"   1. If execution found and succeeded, check email for notification")
print(f"   2. If no execution found, S3 event notification may not be working") 
print(f"   3. PDF file should be: medical_case_study_20250524_083401.pdf") 