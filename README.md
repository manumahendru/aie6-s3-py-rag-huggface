---
title: Aie S3 A1
emoji: ⚡
colorFrom: indigo
colorTo: green
sdk: docker
pinned: false
license: openrail
short_description: AIE6 Session 3 Activity 1
---

# RAG Application with React and FastAPI

This is a Retrieval Augmented Generation (RAG) application that allows users to upload documents (PDF or TXT) and ask questions about their content. The application uses OpenAI embeddings and models to process and answer queries.

## Project Structure

The project is split into two main parts:

- **Backend**: A FastAPI application that handles file processing, vector database operations, and AI model interactions
- **Frontend**: A React application that provides a user interface for file upload and chat functionality

## Setup and Installation

### Docker (Recommended)

The easiest way to run the application is using Docker:

1. Make sure you have Docker installed on your system
2. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Build the Docker image:
   ```
   docker build -t rag-app-reactfastapi .
   ```
4. Run the Docker container:
   ```
   docker run -p 3000:3000 -p 8000:8000 --env-file .env rag-app-reactfastapi
   ```
5. Access the application at http://localhost:3000

### Manual Setup

#### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the backend directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

5. Start the backend server:
   ```
   python run.py
   ```
   
   The server will be available at http://localhost:8000.

#### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```
   
   The application will be available at http://localhost:3000.

## Usage

1. Open the application in your browser.
2. Upload a PDF or TXT file using the upload interface.
3. Once the file is processed, you can ask questions about its content in the chat interface.
4. The application will provide answers based on the content of your document.

## Technology Stack

- **Backend**:
  - FastAPI
  - OpenAI API
  - Python 3.x
  - PyPDF2 for PDF processing

- **Frontend**:
  - React
  - WebSockets for real-time chat
  - CSS (no frameworks)

# Deploying Pythonic Chat With Your Text File Application

In today's breakout rooms, we will be following the process that you saw during the challenge.

Today, we will repeat the same process - but powered by our Pythonic RAG implementation we created last week. 

You'll notice a few differences in the `app.py` logic - as well as a few changes to the `aimakerspace` package to get things working smoothly with Chainlit.

> NOTE: If you want to run this locally - be sure to use `uv run chainlit run app.py` to start the application outside of Docker.

## Reference Diagram (It's Busy, but it works)

![image](https://i.imgur.com/IaEVZG2.png)

### Anatomy of a Chainlit Application

[Chainlit](https://docs.chainlit.io/get-started/overview) is a Python package similar to Streamlit that lets users write a backend and a front end in a single (or multiple) Python file(s). It is mainly used for prototyping LLM-based Chat Style Applications - though it is used in production in some settings with 1,000,000s of MAUs (Monthly Active Users).

The primary method of customizing and interacting with the Chainlit UI is through a few critical [decorators](https://blog.hubspot.com/website/decorators-in-python).

> NOTE: Simply put, the decorators (in Chainlit) are just ways we can "plug-in" to the functionality in Chainlit. 

We'll be concerning ourselves with three main scopes:

1. On application start - when we start the Chainlit application with a command like `uv run chainlit run app.py`
2. On chat start - when a chat session starts (a user opens the web browser to the address hosting the application)
3. On message - when the users sends a message through the input text box in the Chainlit UI

Let's dig into each scope and see what we're doing!

### On Application Start:

The first thing you'll notice is that we have the traditional "wall of imports" this is to ensure we have everything we need to run our application. 

```python
import os
from typing import List
from chainlit.types import AskFileResponse
from aimakerspace.text_utils import CharacterTextSplitter, TextFileLoader
from aimakerspace.openai_utils.prompts import (
    UserRolePrompt,
    SystemRolePrompt,
    AssistantRolePrompt,
)
from aimakerspace.openai_utils.embedding import EmbeddingModel
from aimakerspace.vectordatabase import VectorDatabase
from aimakerspace.openai_utils.chatmodel import ChatOpenAI
import chainlit as cl
```

Next up, we have some prompt templates. As all sessions will use the same prompt templates without modification, and we don't need these templates to be specific per template - we can set them up here - at the application scope. 

```python
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
```

> NOTE: You'll notice that these are the exact same prompt templates we used from the Pythonic RAG Notebook in Week 1 Day 2!

Following that - we can create the Python Class definition for our RAG pipeline - or *chain*, as we'll refer to it in the rest of this walkthrough. 

Let's look at the definition first:

```python
class RetrievalAugmentedQAPipeline:
    def __init__(self, llm: ChatOpenAI(), vector_db_retriever: VectorDatabase) -> None:
        self.llm = llm
        self.vector_db_retriever = vector_db_retriever

    async def arun_pipeline(self, user_query: str):
        ### RETRIEVAL
        context_list = self.vector_db_retriever.search_by_text(user_query, k=4)

        context_prompt = ""
        for context in context_list:
            context_prompt += context[0] + "\n"

        ### AUGMENTED
        formatted_system_prompt = system_role_prompt.create_message()

        formatted_user_prompt = user_role_prompt.create_message(question=user_query, context=context_prompt)


        ### GENERATION
        async def generate_response():
            async for chunk in self.llm.astream([formatted_system_prompt, formatted_user_prompt]):
                yield chunk

        return {"response": generate_response(), "context": context_list}
```

Notice a few things:

1. We have modified this `RetrievalAugmentedQAPipeline` from the initial notebook to support streaming. 
2. In essence, our pipeline is *chaining* a few events together:
    1. We take our user query, and chain it into our Vector Database to collect related chunks
    2. We take those contexts and our user's questions and chain them into the prompt templates
    3. We take that prompt template and chain it into our LLM call
    4. We chain the response of the LLM call to the user
3. We are using a lot of `async` again!

Now, we're going to create a helper function for processing uploaded text files.

First, we'll instantiate a shared `CharacterTextSplitter`.

```python
text_splitter = CharacterTextSplitter()
```

Now we can define our helper.

```python
def process_file(file: AskFileResponse):
    import tempfile
    import shutil
    
    print(f"Processing file: {file.name}")
    
    # Create a temporary file with the correct extension
    suffix = f".{file.name.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        # Copy the uploaded file content to the temporary file
        shutil.copyfile(file.path, temp_file.name)
        print(f"Created temporary file at: {temp_file.name}")
        
        # Create appropriate loader
        if file.name.lower().endswith('.pdf'):
            loader = PDFLoader(temp_file.name)
        else:
            loader = TextFileLoader(temp_file.name)
            
        try:
            # Load and process the documents
            documents = loader.load_documents()
            texts = text_splitter.split_texts(documents)
            return texts
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file.name)
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}")
```

Simply put, this downloads the file as a temp file, we load it in with `TextFileLoader` and then split it with our `TextSplitter`, and returns that list of strings!

#### ❓ QUESTION #1:

Why do we want to support streaming? What about streaming is important, or useful?

#### ✅ ANSWER #1:

We want to support streaming in an application like this because of how the user interacts with such an application. As the user is waiting for a response in (near) real-time, it is important for the application to respond back with whatever tokens the language model has generated back to the user immediately, instead of waiting for the entire generation to complete. Waiting for the entire generation to complete and NOT streaming will make it seem to be a very slow response for the user.

### On Chat Start:

The next scope is where "the magic happens". On Chat Start is when a user begins a chat session. This will happen whenever a user opens a new chat window, or refreshes an existing chat window.

You'll see that our code is set-up to immediately show the user a chat box requesting them to upload a file. 

```python
while files == None:
        files = await cl.AskFileMessage(
            content="Please upload a Text or PDF file to begin!",
            accept=["text/plain", "application/pdf"],
            max_size_mb=2,
            timeout=180,
        ).send()
```

Once we've obtained the text file - we'll use our processing helper function to process our text!

After we have processed our text file - we'll need to create a `VectorDatabase` and populate it with our processed chunks and their related embeddings!

```python
vector_db = VectorDatabase()
vector_db = await vector_db.abuild_from_list(texts)
```

Once we have that piece completed - we can create the chain we'll be using to respond to user queries!

```python
retrieval_augmented_qa_pipeline = RetrievalAugmentedQAPipeline(
        vector_db_retriever=vector_db,
        llm=chat_openai
    )
```

Now, we'll save that into our user session!

> NOTE: Chainlit has some great documentation about [User Session](https://docs.chainlit.io/concepts/user-session). 

#### ❓ QUESTION #2: 

Why are we using User Session here? What about Python makes us need to use this? Why not just store everything in a global variable?

#### ✅ ANSWER #2:

In the context of web applications, a user's session is the set of information that a server associates with that specific user only. In our application, we save the RAG pipeline (the uploaded document's embeddings + the chat model we will use for the user's questions) in the user's session.
The reason we need to use this when working with Python is that every time the main() method is called on a user's message submission, Python (ie, the stack we have avaliable) cannot associate that incoming message with that user's original document or its embeddings. That association has to be maintained using chainlit's session feature.
Finally, we can't store this session information in a global variable because that would overwrite one user's session information with another users's session information - because the global variables are shared for all method calls.

### On Message

First, we load our chain from the user session:

```python
chain = cl.user_session.get("chain")
```

Then, we run the chain on the content of the message - and stream it to the front end - that's it!

```python
msg = cl.Message(content="")
result = await chain.arun_pipeline(message.content)

async for stream_resp in result["response"]:
    await msg.stream_token(stream_resp)
```

### 🎉

With that - you've created a Chainlit application that moves our Pythonic RAG notebook to a Chainlit application!

## Deploying the Application to Hugging Face Space

Due to the way the repository is created - it should be straightforward to deploy this to a Hugging Face Space!

> NOTE: If you wish to go through the local deployments using `chainlit run app.py` and Docker - please feel free to do so!

<details>
    <summary>Creating a Hugging Face Space</summary>

1.  Navigate to the `Spaces` tab.

![image](https://i.imgur.com/aSMlX2T.png)

2. Click on `Create new Space`

![image](https://i.imgur.com/YaSSy5p.png)

3. Create the Space by providing values in the form. Make sure you've selected "Docker" as your Space SDK.

![image](https://i.imgur.com/6h9CgH6.png)

</details>

<details>
    <summary>Adding this Repository to the Newly Created Space</summary>

1. Collect the SSH address from the newly created Space. 

![image](https://i.imgur.com/Oag0m8E.png)

> NOTE: The address is the component that starts with `git@hf.co:spaces/`.

2. Use the command:

```bash
git remote add hf HF_SPACE_SSH_ADDRESS_HERE
```

3. Use the command:

```bash
git pull hf main --no-rebase --allow-unrelated-histories -X ours
```

4. Use the command: 

```bash 
git add .
```

5. Use the command:

```bash
git commit -m "Deploying Pythonic RAG"
```

6. Use the command: 

```bash
git push hf main
```

7. The Space should automatically build as soon as the push is completed!

> NOTE: The build will fail before you complete the following steps!

</details>

<details>
    <summary>Adding OpenAI Secrets to the Space</summary>

1. Navigate to your Space settings.

![image](https://i.imgur.com/zh0a2By.png)

2. Navigate to `Variables and secrets` on the Settings page and click `New secret`: 

![image](https://i.imgur.com/g2KlZdz.png)

3. In the `Name` field - input `OPENAI_API_KEY` in the `Value (private)` field, put your OpenAI API Key.

![image](https://i.imgur.com/eFcZ8U3.png)

4. The Space will begin rebuilding!

</details>

## 🎉

You just deployed Pythonic RAG!

Try uploading a text file and asking some questions!

#### ❓ Discussion Question #1:

Upload a PDF file of the recent DeepSeek-R1 paper and ask the following questions:

1. What is RL and how does it help reasoning?

    ✅ Answer:
    RL stands for Reinforcement Learning. It is a machine learning paradigm where an agent learns to make decisions by taking actions in an environment to maximize cumulative rewards. In the context of improving reasoning capabilities of language models, RL helps by allowing the model to explore and develop reasoning patterns through trial and error without relying on supervised data. This self-evolution process enables the model to generate chain-of-thought (CoT) reasoning and exhibit complex problem-solving behaviors, ultimately enhancing its reasoning performance on various tasks.


--- 
2. What is the difference between DeepSeek-R1 and DeepSeek-R1-Zero?

    ✅ Answer:
    The main differences between DeepSeek-R1 and DeepSeek-R1-Zero are as follows:

    1. **Capabilities**: DeepSeek-R1 currently has more advanced capabilities compared to DeepSeek-R1-Zero, especially in tasks such as function calling, multi-turn interactions, complex role-playing, and JSON output.

    2. **Performance**: DeepSeek-R1-Zero exhibits improvements in performance during its reinforcement learning (RL) training process, achieving a significant increase in its average pass@1 score on the AIME 2024 benchmark. However, DeepSeek-R1 is suggested to be more capable overall in certain tasks.

    3. **Language Mixing**: DeepSeek-R1 is optimized for Chinese and English, while DeepSeek-R1-Zero may experience language mixing issues when handling queries in languages other than these two.

    4. **Prompt Sensitivity**: DeepSeek-R1 is sensitive to prompts, with few-shot prompting leading to degraded performance. It is recommended to use a zero-shot setting for optimal results. The context does not specify how DeepSeek-R1-Zero responds to prompting, but it is indicated that DeepSeek-R1 has specific sensitivities.

    5. **Output Readability**: DeepSeek-R1-Zero often produces content that is not suitable for reading, due to issues like language mixing or lack of formatting. In contrast, cold-start data for DeepSeek-R1 is designed to be reader-friendly and includes a structured output format with a summary.

    6. **Self-evolution Process**: DeepSeek-R1-Zero has a self-evolution process where it improves its reasoning capabilities autonomously, starting directly from the base model without prior supervised fine-tuning. The context does not provide details on the evolution process for DeepSeek-R1.

    Overall, DeepSeek-R1 appears to be a more polished and capable model, while DeepSeek-R1-Zero showcases a developmental approach to enhance reasoning over time.

--- 

3. What is this paper about?

    ✅ Answer:
    I don't know the answer.
  
--- 
  
4. Does this application pass your vibe check? Are there any immediate pitfalls you're noticing?

    ✅ Answer:
    No. The only context that the language model has are the chunks. The model is not aware of any higher level concept of what the overall paper is about, or even the fact that this is an AI related paper at all, and not the script of a movie.

    The last question shows that the prompt should be updated to reflect that it is being given a paper. May be the paper can be summarized in one or two sentences, and the summary can be stored as part of the system prompt.


## 🚧 CHALLENGE MODE 🚧

For the challenge mode, please instead create a simple FastAPI backend with a simple React (or any other JS framework) frontend.

You can use the same prompt templates and RAG pipeline as we did here - but you'll need to modify the code to work with FastAPI and React.

Deploy this application to Hugging Face Spaces!