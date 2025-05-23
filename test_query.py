#!/usr/bin/env python3
"""
Test script for the query Lambda function
"""

import boto3
import json

def test_query_function():
    """Test the query Lambda function"""
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda')
    
    # Get the function name
    function_name = None
    try:
        functions = lambda_client.list_functions()
        for func in functions['Functions']:
            if 'QueryFn' in func['FunctionName']:
                function_name = func['FunctionName']
                break
        
        if not function_name:
            print("❌ Query function not found!")
            return
            
        print(f"✅ Found query function: {function_name}")
        
        # Test query
        test_query = {
            "query": "patient medical history",
            "limit": 3
        }
        
        print(f"🔍 Testing query: '{test_query['query']}'")
        
        # Invoke the function
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(test_query)
        )
        
        # Parse response
        result = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            print("✅ Function invoked successfully!")
            
            # Parse the response body
            if 'body' in result:
                body = json.loads(result['body'])
                print(f"📊 Query: {body.get('query')}")
                print(f"📈 Results count: {body.get('count')}")
                
                if body.get('results'):
                    for i, result_item in enumerate(body['results'][:3]):
                        print(f"\n🔍 Result {i+1}:")
                        print(f"   📄 Document ID: {result_item.get('documentId')}")
                        print(f"   📝 Chunk ID: {result_item.get('chunkId')}")
                        if 'similarity' in result_item:
                            print(f"   📊 Similarity: {result_item['similarity']:.4f}")
                        if 'text' in result_item:
                            text_preview = result_item['text'][:100] + "..." if len(result_item['text']) > 100 else result_item['text']
                            print(f"   📄 Text: {text_preview}")
                else:
                    print("ℹ️  No results found - this is expected if pipeline hasn't completed embedding yet")
            else:
                print("📄 Raw response:", result)
        else:
            print(f"❌ Function failed with status {response['StatusCode']}")
            print("📄 Error:", result)
            
    except Exception as e:
        print(f"❌ Error testing query function: {str(e)}")

if __name__ == "__main__":
    print("🚀 Testing Query Function")
    print("=" * 50)
    test_query_function() 