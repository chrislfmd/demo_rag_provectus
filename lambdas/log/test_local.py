import os
import json
from datetime import datetime, timezone
from handler import handler

def test_log():
    # Set environment variable
    os.environ['TABLE_NAME'] = 'ExecLog'
    
    # Create test event
    event = {
        "runId": "test-run-001",
        "s3Key": "incoming/test.pdf",
        "status": "SUCCEEDED",
        "startTs": datetime.now(timezone.utc).isoformat(),
        "endTs": datetime.now(timezone.utc).isoformat(),
        "rowCount": 5
    }
    
    # Call handler
    result = handler(event, None)
    
    # Print results
    print("\nStatus Code:", result['statusCode'])
    if result['statusCode'] == 200:
        print("\nRun ID:", result['runId'])
        print("\nMessage:", result['message'])
    else:
        print("\nError:", result.get('error', 'Unknown error'))

if __name__ == "__main__":
    test_log() 