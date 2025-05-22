import boto3
import json

def test_bedrock_access():
    # Use bedrock client for listing models
    bedrock = boto3.client('bedrock')
    # Use bedrock-runtime client for invoking models
    runtime = boto3.client('bedrock-runtime')
    
    # Test text
    test_text = "This is a test document for the RAG demo pipeline."
    
    # List available models first
    print("Listing available models...")
    try:
        models = bedrock.list_foundation_models()
        print("\nAvailable models:")
        for model in models['modelSummaries']:
            if 'embed' in model['modelId'].lower():
                print(f"- {model['modelId']}")
    except Exception as e:
        print(f"Error listing models: {str(e)}")
    
    print("\nTrying model invocations...")
    
    # Try with the exact model ID from the list
    try:
        response = runtime.invoke_model(
            modelId='cohere.embed-english-v3',
            body=json.dumps({
                'texts': [test_text],
                'input_type': 'search_document'
            })
        )
        print("\nSuccess with base model ID!")
        result = json.loads(response['body'].read())
        print(f"Embedding dimension: {len(result['embeddings'][0])}")
        print(f"First few values: {result['embeddings'][0][:5]}")
        
    except Exception as e:
        print(f"\nError with base model: {str(e)}")
        
        # Try with the full model ARN
        try:
            response = runtime.invoke_model(
                modelId='arn:aws:bedrock:us-east-1::foundation-model/cohere.embed-english-v3',
                body=json.dumps({
                    'texts': [test_text],
                    'input_type': 'search_document'
                })
            )
            print("\nSuccess with full ARN!")
            result = json.loads(response['body'].read())
            print(f"Embedding dimension: {len(result['embeddings'][0])}")
            print(f"First few values: {result['embeddings'][0][:5]}")
            
        except Exception as e:
            print(f"\nError with full ARN: {str(e)}")

if __name__ == "__main__":
    test_bedrock_access() 