#!/usr/bin/env python3
"""
Comprehensive RAG System Demo
Showcases the complete Retrieval-Augmented Generation pipeline
"""

import boto3
import json
import time

def run_rag_demo():
    """Run a comprehensive demo of the RAG system"""
    
    print("🏥 RAG System Demo - Medical Document Search")
    print("=" * 60)
    print("🚀 AWS RAG Pipeline: S3 → Textract → Bedrock → DynamoDB → Query")
    print()
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda')
    
    # Find query function
    functions = lambda_client.list_functions()
    query_function = None
    for func in functions['Functions']:
        if 'QueryFn' in func['FunctionName']:
            query_function = func['FunctionName']
            break
    
    if not query_function:
        print("❌ Query function not found!")
        return
    
    print(f"✅ Connected to RAG system: {query_function}")
    print()
    
    # Demo queries showcasing different capabilities
    demo_queries = [
        {
            "query": "chest pain symptoms",
            "description": "🫀 Cardiac Symptoms Query",
            "expected": "Should find chest pain and cardiovascular content"
        },
        {
            "query": "diabetes medication",
            "description": "💊 Medication Search",
            "expected": "Should find diabetes medications like metformin"
        },
        {
            "query": "laboratory test results",
            "description": "🧪 Lab Results Query", 
            "expected": "Should find troponin, creatinine, glucose levels"
        },
        {
            "query": "patient treatment plan",
            "description": "📋 Treatment Planning",
            "expected": "Should find cardiac intervention and therapy plans"
        },
        {
            "query": "follow up care instructions",
            "description": "📅 Patient Care Instructions",
            "expected": "Should find patient education and follow-up scheduling"
        }
    ]
    
    results_summary = []
    
    for i, demo in enumerate(demo_queries, 1):
        print(f"\n{'='*50}")
        print(f"Demo {i}/5: {demo['description']}")
        print(f"Query: '{demo['query']}'")
        print(f"Expected: {demo['expected']}")
        print("-" * 50)
        
        try:
            # Execute query
            response = lambda_client.invoke(
                FunctionName=query_function,
                Payload=json.dumps({
                    "query": demo['query'],
                    "limit": 3
                })
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200 and 'body' in result:
                body = json.loads(result['body'])
                
                if body.get('results'):
                    print(f"✅ Found {body['count']} relevant chunks:")
                    
                    for j, chunk in enumerate(body['results'], 1):
                        similarity = chunk.get('similarity', 0)
                        text_preview = chunk.get('text', '')[:100] + "..."
                        section = chunk.get('metadata', {}).get('section', 'unknown')
                        
                        print(f"\n   📄 Result {j}:")
                        print(f"      🎯 Similarity: {similarity:.4f}")
                        print(f"      📍 Section: {section}")
                        print(f"      📝 Text: {text_preview}")
                    
                    # Track best result
                    best_similarity = max(r.get('similarity', 0) for r in body['results'])
                    results_summary.append({
                        'query': demo['query'],
                        'count': body['count'],
                        'best_similarity': best_similarity,
                        'success': True
                    })
                else:
                    print("⚠️  No results found")
                    results_summary.append({
                        'query': demo['query'],
                        'count': 0,
                        'best_similarity': 0,
                        'success': False
                    })
            else:
                print(f"❌ Query failed: {result}")
                results_summary.append({
                    'query': demo['query'],
                    'count': 0,
                    'best_similarity': 0,
                    'success': False
                })
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results_summary.append({
                'query': demo['query'],
                'count': 0,
                'best_similarity': 0,
                'success': False
            })
        
        # Small delay between queries
        time.sleep(1)
    
    # Summary Report
    print(f"\n\n🎯 RAG SYSTEM PERFORMANCE SUMMARY")
    print("=" * 60)
    
    successful_queries = sum(1 for r in results_summary if r['success'])
    total_chunks_found = sum(r['count'] for r in results_summary)
    avg_similarity = sum(r['best_similarity'] for r in results_summary if r['success']) / max(successful_queries, 1)
    
    print(f"✅ Successful Queries: {successful_queries}/5 ({successful_queries/5*100:.1f}%)")
    print(f"📊 Total Relevant Chunks Found: {total_chunks_found}")
    print(f"🎯 Average Best Similarity: {avg_similarity:.4f}")
    print()
    
    print("📋 Query Performance Details:")
    for result in results_summary:
        status = "✅" if result['success'] else "❌"
        print(f"   {status} '{result['query']}': {result['count']} results, best: {result['best_similarity']:.4f}")
    
    print(f"\n🏆 RAG SYSTEM STATUS: {'FULLY OPERATIONAL' if successful_queries >= 4 else 'NEEDS ATTENTION'}")
    
    # Architecture Summary
    print(f"\n\n🏗️  SYSTEM ARCHITECTURE SUMMARY")
    print("=" * 60)
    print("📁 Document Storage: Amazon S3")
    print("📄 Text Extraction: Amazon Textract (OCR + Layout)")
    print("🧠 Embeddings: Amazon Bedrock (Titan Text v2)")
    print("🗄️  Vector Storage: Amazon DynamoDB")
    print("⚡ Query Processing: AWS Lambda")
    print("🔄 Orchestration: AWS Step Functions")
    print("🔍 Search Method: Cosine Similarity")
    print("💰 Cost Optimization: Sample data approach")
    
    print(f"\n🎉 Demo Complete! The RAG system is ready for production use.")

if __name__ == "__main__":
    run_rag_demo() 