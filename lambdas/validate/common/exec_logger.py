"""
Common execution logging utility for RAG pipeline Lambda functions
"""

import boto3
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
import time

class ExecutionLogger:
    """Utility class for logging execution metadata to DynamoDB"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.exec_log_table = os.environ.get('EXEC_LOG_TABLE')
        
        if self.exec_log_table:
            self.table = self.dynamodb.Table(self.exec_log_table)
        else:
            self.table = None
            print("⚠️ EXEC_LOG_TABLE not configured - logging disabled")
    
    def log_step(self, run_id, step, status, **kwargs):
        """
        Log a pipeline step execution
        
        Args:
            run_id (str): Unique execution identifier
            step (str): Step name (init_db, validate, embed, load)
            status (str): Status (STARTED, IN_PROGRESS, SUCCESS, FAILED)
            **kwargs: Additional metadata to log
        """
        
        if not self.table:
            print(f"⚠️ Logging disabled for: {run_id} - {step} - {status}")
            return
            
        try:
            # Create timestamp
            timestamp = datetime.utcnow().isoformat()
            
            # TTL for 30 days (optional cleanup)
            ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            
            # Prepare log entry
            log_entry = {
                'runId': run_id,
                'timestamp': timestamp,
                'status': status,
                'step': step,
                'ttl': ttl
            }
            
            # Add additional metadata
            for key, value in kwargs.items():
                if value is not None:
                    if isinstance(value, float):
                        log_entry[key] = Decimal(str(value))
                    else:
                        log_entry[key] = value
            
            # Write to DynamoDB
            self.table.put_item(Item=log_entry)
            
            print(f"✅ Logged: {run_id} - {step} - {status}")
            
        except Exception as e:
            print(f"❌ Error logging {run_id} - {step}: {str(e)}")
    
    def log_start(self, run_id, step, **kwargs):
        """Log step start"""
        self.log_step(run_id, step, "STARTED", **kwargs)
    
    def log_success(self, run_id, step, **kwargs):
        """Log step success"""
        self.log_step(run_id, step, "SUCCESS", **kwargs)
    
    def log_error(self, run_id, step, error_message, **kwargs):
        """Log step error"""
        self.log_step(run_id, step, "FAILED", error=str(error_message), **kwargs)
    
    def log_document_start(self, run_id, filename, s3_key, **kwargs):
        """Log document processing start"""
        document_info = {
            'filename': filename,
            's3Key': s3_key,
            'startTime': datetime.utcnow().isoformat()
        }
        document_info.update(kwargs)
        
        self.log_step(run_id, "document_start", "STARTED", documentInfo=document_info)
    
    def log_document_complete(self, run_id, chunk_count, processing_time=None, **kwargs):
        """Log document processing completion"""
        metadata = {
            'chunkCount': chunk_count,
            'endTime': datetime.utcnow().isoformat()
        }
        
        if processing_time:
            metadata['processingTimeSeconds'] = processing_time
            
        metadata.update(kwargs)
        
        self.log_step(run_id, "document_complete", "SUCCESS", 
                     chunkCount=chunk_count,
                     processingTime=processing_time,
                     **kwargs)

# Create a global instance for easy import
logger = ExecutionLogger() 