import json
from handler import handler

def test_embed():
    # Load test event
    with open('test_event.json', 'r') as f:
        event = json.load(f)
    
    # Call handler
    result = handler(event, None)
    
    # Print results
    print("\nStatus Code:", result['statusCode'])
    
    if result['statusCode'] == 200:
        print("\nNumber of chunks:", len(result['chunks']))
        print("\nFirst chunk:", result['chunks'][0])
        print("\nEmbedding dimension:", len(result['embeddings'][0]))
        print("\nFirst few values of first embedding:", result['embeddings'][0][:5])
    else:
        print("\nError:", result.get('error', 'Unknown error'))

if __name__ == "__main__":
    test_embed() 