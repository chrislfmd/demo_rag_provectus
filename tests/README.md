# RAG Pipeline Tests

This directory contains all test scripts and debugging utilities for the RAG (Retrieval-Augmented Generation) pipeline system.

## Main Test Scripts

### `test_complete_pipeline.py`
**Complete End-to-End Pipeline Test**
- Creates a medical case study PDF with timestamp
- Uploads PDF to S3 and monitors pipeline execution
- Tests entire flow: S3 → Textract → Embed → Load → Notify
- Includes real-time execution monitoring
- **Usage**: `python test_complete_pipeline.py`

### `test_email_fix.py`
**Quick Pipeline Test**
- Simple text file upload test
- Manually triggers Step Functions execution
- Tests email notification system
- **Usage**: `python test_email_fix.py`

### `test_lambda_message_format.py`
**Email Format Testing**
- Tests exact message format sent by Lambda
- Validates SNS email delivery with pipeline data
- Compares Lambda output with expected email content
- **Usage**: `python test_lambda_message_format.py`

## Monitoring & Debug Scripts

### `check_recent_executions.py`
**Pipeline Execution Monitoring**
- Lists recent Step Functions executions
- Identifies specific pipeline runs by filename
- Shows execution status, duration, and run IDs
- Checks S3 event notification configuration
- **Usage**: `python check_recent_executions.py`

### `check_queue_status.py`
**SQS Queue Monitoring**
- Monitors all RAG pipeline SQS queues
- Shows message counts (visible and processing)
- Tracks success, error, and notification queues
- **Usage**: `python check_queue_status.py`

### `check_email_logs.py`
**Email Lambda Logs**
- Retrieves recent logs from email forwarder Lambda
- Shows message processing and SNS delivery status
- **Usage**: `python check_email_logs.py`

### `check_lambda_logs.py`
**Comprehensive Lambda Log Analysis**
- Detailed log analysis for all pipeline Lambda functions
- Searches for specific run IDs and error patterns
- Multi-function log correlation
- **Usage**: `python check_lambda_logs.py`

## Specific Debug Utilities

### `debug_email_delivery.py`
**Email Delivery Debugging**
- Checks SNS topic configuration and subscriptions
- Sends direct test emails to verify delivery
- Validates email subscription status
- **Usage**: `python debug_email_delivery.py`

### `check_dlq_messages.py`
**Dead Letter Queue Analysis**
- Examines failed messages in DLQ
- Shows message content and failure reasons
- Helps debug notification issues
- **Usage**: `python check_dlq_messages.py`

### `email_timing_analysis.py`
**Email Delivery Timing**
- Analyzes expected email delivery timeframes
- Explains SQS batching and SNS delivery delays
- **Usage**: `python email_timing_analysis.py`

## Status Check Scripts

### `check_current_execution.py`
**Single Execution Status**
- Checks status of a specific pipeline execution
- Shows duration and success/failure details
- **Usage**: `python check_current_execution.py`

### `check_execution.py`
**Basic Execution Check**
- Simple execution status verification
- **Usage**: `python check_execution.py`

### `check_document.py`
**Document Processing Verification**
- Checks if documents are properly stored in DynamoDB
- Verifies vector embeddings and metadata
- **Usage**: `python check_document.py`

### `check_specific_run.py`
**Run-Specific Analysis**
- Detailed analysis of a specific pipeline run
- Tracks execution across all Lambda functions
- **Usage**: `python check_specific_run.py`

### `test_summary.py`
**Test Results Summary**
- Comprehensive summary of pipeline test results
- Shows execution status, queue status, and email delivery
- **Usage**: `python test_summary.py`

## Quick Testing Guide

**For a complete pipeline test:**
```bash
python test_complete_pipeline.py
```

**To check if notifications are working:**
```bash
python debug_email_delivery.py
python check_queue_status.py
```

**To monitor a running pipeline:**
```bash
python check_recent_executions.py
python check_email_logs.py
```

**To debug issues:**
```bash
python check_lambda_logs.py
python check_dlq_messages.py
```

## Expected Email Notifications

When pipeline completes successfully, you should receive:
- **Subject**: "RAG Pipeline Notification - SUCCESS"
- **Content**: Processing metadata, chunk count, timing, next steps
- **Delivery Time**: 1-6 minutes after pipeline completion

## Pipeline Architecture

The tests validate this complete flow:
1. **S3 Upload** → Automatic trigger
2. **InitDB** → Document registration  
3. **Validate** → Text extraction simulation
4. **Embed** → Vector generation with Bedrock
5. **Load** → Storage in DynamoDB
6. **Notify** → Success/error notifications via SNS

All tests are designed to work with the RAG pipeline's notification system and provide comprehensive monitoring capabilities. 