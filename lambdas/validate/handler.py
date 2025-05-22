import json
import boto3
import os
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def validate_blocks(blocks):
    """Simple validation to check if blocks have non-empty text"""
    for block in blocks:
        if "Text" in block and not block["Text"].strip():
            return False
    return True

def handler(event, _ctx):
    # Log the input event
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Get blocks from the Textract response in the state machine input
        blocks = event["textract"]["status"]["Blocks"]
        logger.info(f"Found {len(blocks)} blocks to validate")
        
        # Simple validation - check for empty text blocks
        if not validate_blocks(blocks):
            logger.error("Validation failed: Found empty text blocks")
            raise ValueError("Validation failed: Found empty text blocks")
        
        logger.info("Validation successful")
        return event  # pass-through
    except KeyError as e:
        logger.error(f"Failed to access required field: {str(e)}")
        logger.error(f"Event structure: {json.dumps(event)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
