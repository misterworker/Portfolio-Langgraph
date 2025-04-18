from pinecone import Pinecone
from pydantic import BaseModel, Field
from psycopg_pool import AsyncConnectionPool
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

import os

#? Langgraph Database Connection Pool
DB_URI = os.getenv("DB_URI")
pool = AsyncConnectionPool(
    conninfo=DB_URI,
    max_size=5,
    kwargs={"autocommit": True, "prepare_threshold": 0},
)

#? Langgraph State
class State(TypedDict):
    """Add attributes that are mutable via nodes, for example if the user type can change from guest to user with the help of
    a node in the graph."""

    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    user_id: str
    fingerprint: str

#? Pinecone Vector Store Setup
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "portfolio"
class VectorStoreManager:
    def __init__(self):
        self._initialize_pinecone()

    def _initialize_pinecone(self):
        Pinecone(api_key=PINECONE_API_KEY)

    def __get_vector_store(self):
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        return PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)

    def retrieve_from_vector_store(self, query: str, top_k: int):
        vector_store = self.__get_vector_store()
        results = vector_store.similarity_search(query, k=top_k)
        return results
    
#? Class for Structured Outputs
class RAG(BaseModel):
    """Create vector store retrieval search term and number of records to retrieve"""
    search_term: str = Field(description="Vector Store Retrieval Term")
    k_records: int = Field(description="How many records to retrieve?")

class Email(BaseModel):
    """Create subject and body"""
    subject: str = Field(description="Email Subject")
    body: str = Field(description="Email Body")

#? Endpoint Inputs
class UserInput(BaseModel):
    fingerprint: str
    user_id: str
    user_input: str
    num_rewind: int = 0

class ResumeInput(BaseModel):
    action: bool
    user_id: str

class WipeInput(BaseModel):
    user_id: str

#? Helper functions
def create_prompt(info:list, llm_type:str):
    # TODO: Add tiktoken counter
    if llm_type == "chatbot":
        from datetime import date; age = ((date.today() - date(2005, 11, 23)).days // 365)
    
        prompt = f"""
            You are an agent called Ethanbot, Ethan's web portfolio manager, built with Langgraph.
            Ethan's portfolio includes these sections in order: About, Tech used, github activity, certs, projects (clickable).
            You are serving visitors of Ethan's Portfolio Website.

            Ethan, aged {age} and based in Singapore, is primarily an AI application builder with data analysis skills and an interest in fitness.

            You are equipped to\\n
            1. Summarise projects\\n
            2. Help user contact Ethan\\n
            3. Fetch Ethan's Github Contribution History
            You can also suspend users for repeated inappropriate behaviour, but be lenient with this. 
            Always utilise the RAG Agent to fetch project details.
            Always utilise email Agent to contact Ethan, but only after they provide the message to send.
            Do not invoke more than one tool at a time.

            Strictly at the start of the conversation, let the user know projects include MaibelAI App, workAdvisor, 
            used car price predictor (MLOps) and workout tracker, and list your full capabilities.
            """
    elif llm_type == "RAG":
        prompt = f"""
            You are an assistant agent for a portfolio chatbot, designed with structured output to provide key search 
            terms for retrieving vector store records and return the number of records to obtain based on user input and context.
            
            Always return 1 or 2 records. Records are structured such that each portfolio project has both an overview and a 
            solution. Should the user be interested in specifically either, then output 1 record. Otherwise, output 2. Overview 
            typically contains the github link, features used and a youtube video and a brief description, while solution specifies the details 
            to resolve the project.\\n

            Example 1: I want to know more about workAdvisor's solution > search_term: Solution - workAdvisor, k_records: 1\\n
            Example 2: overview for Maibel AI App > search_term: Overview - Maibel AI App, k_records: 1\\n
            Example 3: tell me more about mlops > search_term: Overview - Used Car Price Predictor (MLOps), k_records: 2\\n
            Example 4: I'd like to know about the github link for the used car predictor > search_term: Overview - Used Car Predictor (MLOps), k_records: 1
            """
        
    elif llm_type == "RAG_CHATBOT":
        records = info[0]
        prompt = f"""
            Provide only necessary information to the user, for example, if the user requests a github link, only provide that. 
            Do not blast the user with the entire overview or solution of the project.
            Records retrieved: {records}
        """

    elif llm_type == "email":
        prompt = f"""
        You are an assistent agent designed to create a subject and body for an email, based on the message or feedback that the visitor
        wants to send. The recipient is always Ethan, the portfolio owner. Always craft a professional email.
        """

    else:
        prompt = "No prompt found"

    def clean_prompt(prompt: str):
        """Preserve '\n' markers as real line breaks, collapse everything else."""
        # Split on literal \n (not actual newlines)
        parts = prompt.split("\\n")
        # Collapse each part (remove extra spaces and real line breaks)
        cleaned_parts = [" ".join(part.strip().split()) for part in parts]
        # Join with actual newlines
        return "\n".join(cleaned_parts)

    cleaned_prompt = clean_prompt(prompt)

    return cleaned_prompt
