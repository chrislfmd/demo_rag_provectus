import boto3
import json
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import time

def create_test_pdf():
    """Create a test PDF with medical content"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 100, "Medical Case Study - Pipeline Test Document")
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica", 10)
    c.drawString(100, height - 120, f"Generated: {timestamp}")
    
    # Medical content
    c.setFont("Helvetica", 12)
    y_position = height - 160
    
    medical_content = [
        "PATIENT CASE SUMMARY",
        "",
        "Patient ID: RAG-TEST-001",
        "Date of Admission: 2025-05-24",
        "",
        "CHIEF COMPLAINT:",
        "Patient presents with symptoms requiring comprehensive analysis",
        "through the RAG (Retrieval-Augmented Generation) pipeline system.",
        "",
        "MEDICAL HISTORY:",
        "- Previous documentation processed successfully",
        "- Vector embeddings created for medical terminology",
        "- Semantic search capabilities demonstrated",
        "",
        "TREATMENT PLAN:",
        "1. Process document through automated pipeline",
        "2. Extract text using Textract service", 
        "3. Generate vector embeddings using Bedrock",
        "4. Store in DynamoDB for retrieval",
        "5. Send success notification via SNS",
        "",
        "EXPECTED OUTCOMES:",
        "- Document successfully ingested into vector database",
        "- Full-text search capabilities enabled",
        "- Email notification confirming completion",
        "",
        "NOTES:",
        "This document serves as a test case for the RAG pipeline",
        "demonstrating end-to-end processing of medical documents",
        "with comprehensive monitoring and notification systems.",
        "",
        "Document processing should complete within 30-60 seconds",
        "with all pipeline steps (InitDB, Validate, Embed, Load, Notify)",
        "executing successfully and generating appropriate notifications."
    ]
    
    for line in medical_content:
        if line == "":
            y_position -= 20
        else:
            if line.isupper() and ":" in line:
                c.setFont("Helvetica-Bold", 12)
            else:
                c.setFont("Helvetica", 11)
            c.drawString(100, y_position, line)
            y_position -= 15
            
        if y_position < 100:  # Start new page if needed
            c.showPage()
            y_position = height - 100
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def upload_and_monitor():
    """Upload PDF and monitor pipeline execution"""
    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"medical_case_study_{timestamp}.pdf"
    
    print("COMPLETE PIPELINE TEST")
    print("=" * 60)
    print(f"Creating test PDF: {filename}")
    
    # Create PDF content
    pdf_content = create_test_pdf()
    print(f"PDF created ({len(pdf_content)} bytes)")
    
    # Upload to S3
    s3 = boto3.client('s3')
    bucket_name = 'rag-demo-raw-pdf-v2'
    
    print(f"\nUploading to S3: s3://{bucket_name}/{filename}")
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=pdf_content,
            ContentType='application/pdf'
        )
        print(f"PDF uploaded successfully!")
        print(f"S3 event notification should trigger pipeline automatically...")
        
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return
    
    # Monitor for Step Functions execution
    print(f"\nMONITORING PIPELINE EXECUTION:")
    stepfunctions = boto3.client('stepfunctions')
    
    # Wait a moment for S3 event to trigger
    print("   Waiting 10 seconds for S3 event to trigger...")
    time.sleep(10)
    
    # Look for recent executions
    state_machine_arn = "arn:aws:states:us-east-1:702645448228:stateMachine:StateMachineEtlStateMachine241248B6-nmg8xN9bET1J"
    
    try:
        executions = stepfunctions.list_executions(
            stateMachineArn=state_machine_arn,
            statusFilter='RUNNING',
            maxResults=5
        )
        
        if executions['executions']:
            # Found running execution
            execution = executions['executions'][0]
            execution_arn = execution['executionArn']
            execution_name = execution['name']
            
            print(f"   Found running execution: {execution_name}")
            print(f"   Execution ARN: {execution_arn}")
            
            # Monitor execution progress
            print(f"\nMONITORING EXECUTION PROGRESS:")
            start_time = datetime.now()
            max_wait_time = 120  # 2 minutes
            
            while True:
                response = stepfunctions.describe_execution(executionArn=execution_arn)
                status = response['status']
                
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"   [{elapsed:5.1f}s] Status: {status}")
                
                if status in ['SUCCEEDED', 'FAILED', 'ABORTED']:
                    break
                    
                if elapsed > max_wait_time:
                    print(f"   Timeout after {max_wait_time} seconds")
                    break
                    
                time.sleep(5)
            
            # Final status
            final_response = stepfunctions.describe_execution(executionArn=execution_arn)
            final_status = final_response['status']
            
            if final_status == 'SUCCEEDED':
                duration = final_response['stopDate'] - final_response['startDate']
                print(f"\nPIPELINE COMPLETED SUCCESSFULLY!")
                print(f"   Total Duration: {duration}")
                print(f"   Email notification should arrive within 1-6 minutes")
                
                # Extract run ID if possible
                try:
                    input_data = json.loads(final_response['input'])
                    run_id = input_data.get('runId', 'Unknown')
                    print(f"   Run ID: {run_id}")
                except:
                    print(f"   Run ID: Check execution input")
                    
            elif final_status == 'FAILED':
                print(f"\nPIPELINE FAILED!")
                print(f"   Error: {final_response.get('error', 'Unknown')}")
                print(f"   Cause: {final_response.get('cause', 'Unknown')}")
            else:
                print(f"\nPIPELINE STATUS: {final_status}")
                
        else:
            print(f"   No running executions found")
            print(f"   Check if S3 event notification is configured correctly")
            
    except Exception as e:
        print(f"   Error monitoring execution: {str(e)}")
    
    print(f"\nTEST SUMMARY:")
    print(f"   Test file: {filename}")
    print(f"   Uploaded to: s3://{bucket_name}/{filename}")
    print(f"   Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Expected email: 'RAG Pipeline Notification - SUCCESS'")
    print(f"\nNEXT STEPS:")
    print(f"   1. Wait for email notification (1-6 minutes)")
    print(f"   2. Check email subject: 'RAG Pipeline Notification - SUCCESS'")
    print(f"   3. Verify processing details in email body")

if __name__ == "__main__":
    upload_and_monitor() 