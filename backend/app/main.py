import os
import tempfile
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import traceback

from app.utils.text_utils import CharacterTextSplitter, TextFileLoader, PDFLoader
from app.utils.openai_utils.prompts import (
    UserRolePrompt,
    SystemRolePrompt,
)
from app.utils.openai_utils.embedding import EmbeddingModel
from app.utils.vectordatabase import VectorDatabase
from app.utils.openai_utils.chatmodel import ChatOpenAI

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine the static files directory relative to this script
static_files_dir = os.path.join(os.path.dirname(__file__), "static")

# The React build process creates a nested 'static' folder within the build output.
# When we copy the build output to our backend 'static' directory, the structure is:
# backend/app/static/
# ├── index.html
# ├── static/
# │   ├── css/
# │   └── js/
# └── ... (other files like favicon.ico)
# Therefore, we need to mount the nested 'static' directory specifically.
react_static_assets_dir = os.path.join(static_files_dir, "static")

# Ensure the main static directory exists (optional, for safety)
os.makedirs(static_files_dir, exist_ok=True)
# Ensure the nested static directory exists (where CSS/JS will be) - might not be strictly necessary
# if the Docker copy creates it, but safe to include.
os.makedirs(react_static_assets_dir, exist_ok=True) 

# Mount the nested static directory from the React build
# Serve files like CSS, JS from 'backend/app/static/static' when requested via '/static' URL path
app.mount("/static", StaticFiles(directory=react_static_assets_dir), name="react_static_assets")

# Serve other frontend routes by returning index.html
# index.html itself resides directly in `static_files_dir` (backend/app/static)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    index_path = os.path.join(static_files_dir, "index.html") # Serve index.html from the root static dir
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    
    # Check if the request is for the root path or explicitly for index.html
    if full_path == "" or full_path == "index.html":
        return FileResponse(index_path)

    # Check if the path looks like an API call or a known static file type not handled by /static mount
    # (e.g., favicon.ico, manifest.json directly in the static root)
    api_prefixes = ['/upload', '/chat', '/query', '/docs', '/openapi.json']
    # Files that might be directly in the static root (not under /static/)
    root_static_files = ['favicon.ico', 'manifest.json', 'logo192.png', 'logo512.png'] # Add others if needed
    
    # If it's an API call, let FastAPI handle it (it should have already if defined)
    # If it reaches here and matches an API prefix, it's likely a 404 for an undefined sub-path.
    if any(full_path.startswith(prefix) for prefix in api_prefixes):
         raise HTTPException(status_code=404, detail="API resource not found")

    # If it's asking for a specific file in the static root (like favicon.ico)
    if full_path in root_static_files:
        file_path = os.path.join(static_files_dir, full_path)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
             raise HTTPException(status_code=404, detail=f"Static file {full_path} not found")

    # If the path does *not* look like a file (no extension in the last part)
    # or it's explicitly asking for a non-static-root file path, serve index.html for React Router.
    # This handles paths like /dashboard, /users/123 etc.
    if '.' not in full_path.split('/')[-1]:
        return FileResponse(index_path)

    # If it looks like a file request but wasn't handled above (e.g., /some/path/file.txt)
    # and isn't caught by the /static mount, return 404.
    raise HTTPException(status_code=404, detail="Resource not found")

# Define prompts
system_template = """\
Use the following context to answer a users question. If you cannot find the answer in the context, say you don't know the answer."""
system_role_prompt = SystemRolePrompt(system_template)

user_prompt_template = """\
Context:
{context}

Question:
{question}
"""
user_role_prompt = UserRolePrompt(user_prompt_template)

class RetrievalAugmentedQAPipeline:
    def __init__(self, llm: ChatOpenAI, vector_db_retriever: VectorDatabase) -> None:
        self.llm = llm
        self.vector_db_retriever = vector_db_retriever

    async def arun_pipeline(self, user_query: str):
        # Retrieve context
        context_list = self.vector_db_retriever.search_by_text(user_query, k=4)

        context_prompt = ""
        for context in context_list:
            context_prompt += context[0] + "\n"

        # Format prompt
        formatted_system_prompt = system_role_prompt.create_message()
        formatted_user_prompt = user_role_prompt.create_message(question=user_query, context=context_prompt)

        # Generate response
        async def generate_response():
            async for chunk in self.llm.astream([formatted_system_prompt, formatted_user_prompt]):
                yield chunk

        return {"response": generate_response(), "context": context_list}

# In-memory storage for user sessions
sessions = {}

class QueryModel(BaseModel):
    query: str
    session_id: str

def process_file(file_path: str, file_name: str):
    """Process uploaded file and return a list of text chunks"""
    print(f"Processing file: {file_name}")
    
    # Create appropriate loader based on file extension
    if file_name.lower().endswith('.pdf'):
        loader = PDFLoader(file_path)
    else:
        loader = TextFileLoader(file_path)
    
    # Load and process the documents
    documents = loader.load_documents()
    text_splitter = CharacterTextSplitter()
    texts = text_splitter.split_texts(documents)
    return texts

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Endpoint to upload and process a file"""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file type
    if not (file.filename.lower().endswith('.txt') or file.filename.lower().endswith('.pdf')):
        raise HTTPException(status_code=400, detail="Only text or PDF files are supported")
    
    temp_file_path = None
    try:
        # Create a temporary file
        suffix = f".{file.filename.split('.')[-1]}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            # Copy uploaded file content to the temporary file
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
        
        # Process the file
        texts = process_file(temp_file_path, file.filename)
        
        # Create vector database and embedding model first
        embedding_model = EmbeddingModel()
        vector_db = VectorDatabase(embedding_model=embedding_model)
        
        # Then build the vector database
        print(f"Building vector database from {len(texts)} text chunks...")
        vector_db = await vector_db.abuild_from_list(texts)
        
        # Create chat model
        chat_openai = ChatOpenAI()
        
        # Create retrieval pipeline
        retrieval_pipeline = RetrievalAugmentedQAPipeline(
            vector_db_retriever=vector_db,
            llm=chat_openai
        )
        
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Store session
        sessions[session_id] = {
            "pipeline": retrieval_pipeline,
            "filename": file.filename
        }
        
        response = {"session_id": session_id, "filename": file.filename, "chunk_count": len(texts)}
        print(f"Returning response: {response}")
        return response
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}")

@app.websocket("/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    print(f"WebSocket connected for session_id: {session_id}")
    await websocket.accept()
    
    if session_id not in sessions:
        await websocket.send_text(json.dumps({"error": "Invalid session ID"}))
        await websocket.close()
        return
    
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received for session_id: {session_id}\nData:{data}")

            query_data = json.loads(data)
            query = query_data.get("query", "")
            
            if not query:
                await websocket.send_text(json.dumps({"error": "Empty query"}))
                continue
                
            # Get the pipeline from the session
            pipeline = sessions[session_id]["pipeline"]
            
            # Run the pipeline
            result = await pipeline.arun_pipeline(query)
            print(f"Result for session_id: {session_id} is {result}")
            
            # Stream the response
            async for chunk in result["response"]:
                await websocket.send_text(json.dumps({"chunk": chunk}))
            
            # Send end of response marker
            await websocket.send_text(json.dumps({"done": True}))
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        try:
            await websocket.send_text(json.dumps({"error": error_message}))
        except:
            pass

@app.post("/query")
async def query(query_data: QueryModel):
    """Endpoint to query the RAG pipeline (non-streaming version)"""
    session_id = query_data.session_id
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get the pipeline from the session
    pipeline = sessions[session_id]["pipeline"]
    
    try:
        # Run the pipeline
        result = await pipeline.arun_pipeline(query_data.query)
        
        # Collect all chunks
        response_chunks = []
        async for chunk in result["response"]:
            response_chunks.append(chunk)
        
        full_response = "".join(response_chunks)
        
        return {"response": full_response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 