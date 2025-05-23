#!/usr/bin/env python3
"""
Create sample embedded data for testing RAG functionality without Textract costs
"""

import boto3
import json
import uuid
from datetime import datetime
from decimal import Decimal

def create_sample_embeddings():
    """Create sample medical document chunks with embeddings"""
    
    # Initialize clients
    dynamodb = boto3.resource('dynamodb')
    bedrock = boto3.client('bedrock-runtime')
    table = dynamodb.Table('Documents')
    
    # Sample medical text chunks
    sample_chunks = [
        {
            "text": "Patient presents with acute chest pain and shortness of breath. Vital signs show elevated heart rate and blood pressure. ECG reveals ST-segment elevation consistent with myocardial infarction.",
            "metadata": {"section": "chief_complaint", "page": 1}
        },
        {
            "text": "Medical history includes hypertension, diabetes mellitus type 2, and previous coronary artery disease. Patient takes metformin, lisinopril, and aspirin daily.",
            "metadata": {"section": "medical_history", "page": 1}
        },
        {
            "text": "Laboratory results show elevated troponin levels at 15.2 ng/mL (normal <0.04). Creatinine is 1.8 mg/dL indicating mild kidney dysfunction. Blood glucose is 245 mg/dL.",
            "metadata": {"section": "lab_results", "page": 2}
        },
        {
            "text": "Treatment plan includes immediate cardiac catheterization with percutaneous coronary intervention. Patient will be started on dual antiplatelet therapy and high-intensity statin.",
            "metadata": {"section": "treatment_plan", "page": 2}
        },
        {
            "text": "Patient education provided regarding medication compliance, dietary modifications, and follow-up care. Scheduled for cardiology follow-up in 2 weeks and primary care in 1 week.",
            "metadata": {"section": "patient_education", "page": 3}
        }
    ]
    
    # Generate embeddings for each chunk
    document_id = str(uuid.uuid4())
    
    print(f"🚀 Creating sample data for document: {document_id}")
    
    for i, chunk in enumerate(sample_chunks):
        try:
            # Generate embedding using Bedrock
            request_body = {
                "inputText": chunk["text"],
                "dimensions": 1024,
                "normalize": True
            }
            
            response = bedrock.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body['embedding']
            
            # Convert float embeddings to Decimal for DynamoDB
            embedding_decimal = [Decimal(str(float(x))) for x in embedding]
            
            # Store in DynamoDB
            chunk_id = f"chunk_{i+1:03d}"
            
            item = {
                'documentId': document_id,
                'chunkId': chunk_id,
                'text': chunk["text"],
                'embedding': embedding_decimal,
                'metadata': chunk["metadata"],
                'filename': 'sample_medical_case.pdf',
                'createdAt': datetime.now().isoformat(),
                'chunkIndex': i,
                'tokenCount': len(chunk["text"].split())
            }
            
            table.put_item(Item=item)
            print(f"✅ Created chunk {i+1}/5: {chunk_id}")
            
        except Exception as e:
            print(f"❌ Error creating chunk {i+1}: {str(e)}")
    
    print(f"🎉 Sample data created successfully!")
    print(f"📄 Document ID: {document_id}")
    print(f"📊 Total chunks: {len(sample_chunks)}")
    
    return document_id

if __name__ == "__main__":
    print("🏥 Creating Sample Medical Data for RAG Demo")
    print("=" * 50)
    document_id = create_sample_embeddings()
    print(f"\n🔍 Test the query function now with medical queries!")
    print(f"Example: 'chest pain', 'diabetes treatment', 'lab results'") 