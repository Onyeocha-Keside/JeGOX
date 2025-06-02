import os
import asyncio
import httpx
from typing import List
#import backoff  # Add this import

async def process_all_documents():
    BASE_URL = "http://localhost:8000"
    RAW_DATA_DIR = "data/raw"
    
    documents = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(('.pdf', '.docx', '.doc', '.txt'))]
    print(f"Found {len(documents)} documents to process")
    
    # Increase timeout and limits
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout
        for doc in documents:
            try:
                file_path = os.path.join(RAW_DATA_DIR, doc)
                data = {
                    "file_path": file_path,
                    "metadata": {
                        "filename": doc,
                        "type": os.path.splitext(doc)[1][1:],
                        "source": "batch_upload"
                    }
                }
                
                print(f"\nProcessing {doc}...")
                response = await client.post(
                    f"{BASE_URL}/api/documents/process",
                    json=data
                )
                
                # Wait between requests
                await asyncio.sleep(2)
                
                if response.status_code == 200:
                    print(f"Successfully processed {doc}")
                else:
                    print(f"Error processing {doc}: {response.text}")
                
            except Exception as e:
                print(f"Error processing {doc}: {str(e)}")
                continue

if __name__ == "__main__":
    asyncio.run(process_all_documents())