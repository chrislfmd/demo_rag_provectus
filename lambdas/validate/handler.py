import json, boto3, os

s3 = boto3.client("s3")

def validate_blocks(blocks):
    """Simple validation to check if blocks have non-empty text"""
    for block in blocks:
        if "Text" in block and not block["Text"].strip():
            return False
    return True

def handler(event, _ctx):
    # event will contain bucket/key written by Textract in next steps
    bucket = event["bucket"]
    key = event["key"]

    # Read and parse the JSON file
    obj = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    data = json.loads(obj)

    # Simple validation - check for empty text blocks
    if not validate_blocks(data["Blocks"]):
        raise ValueError("Validation failed: Found empty text blocks")

    return event  # pass-through
