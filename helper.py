from dotenv import load_dotenv
from pinecone import Pinecone
from pydantic import BaseModel, Field

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

import os

load_dotenv()

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
    
class RAG(BaseModel):
    """Create vector store retrieval search term and number of records to retrieve"""
    search_term: str = Field(description="Vector Store Retrieval Term")
    k_records: int = Field(description="How many records to retrieve?")

def create_prompt(user_type:str, stats:list, llm_type):
    # stats: [commits, streak]
    if llm_type == "chatbot":
        from datetime import date; age = ((date.today() - date(2005, 11, 23)).days // 365)
        commits = stats[0]; streak = stats[1]
    
        prompt = f"""
            You are an agent called Ethanbot, Ethan's web portfolio manager. You are speaking this user type: {user_type}.
            Ethan's portfolio includes these sections in order: About, Tech used, github actvity, certs, projects (clickable).
            It also has a day/night theme switch and a lock button to lock the header in place.

            Ethan, aged {age} and based in Singapore, is primarily an AI application builder with data analysis skills. 
            On github, he has {commits} commits and a streak of {streak}.

            You, Ethanbot, are built using Langgraph. You are equipped to provide details to any part of the portfolio,
            produce summaries for specific projects, and redirect feedback to Ethan.

            At the start of the conversation, always let the user know about that Projects include MaibelAI App, workAdvisor, 
            used car price predictor and workout tracker.
        """
    elif llm_type == "RAG":
        prompt = f"""
            You are designed with structured output to provide key search terms for retrieving vector store records and output 
            the number of records to obtain based on user input and context. You are an assistant agent for a portfolio chatbot.
            
            Here's how to decide the number of records to provide: You always want to provide either 0 to 2 records. The records
            are structured such that each portfolio project has both an overview and a solution. Should the user be interested in
            only either, then output 1 record. Otherwise, output 2.

            Example 1: I want to know more about workAdvisor's solution! Output: search_term - WorkAdvisor Solution, k_records - 1
            Example 2: solution for Maibel AI App? Output: search_term - Maibel AI App Solution, k_records - 1
            Example 3: tell me more about mlops. Output: search_term - mlops, k_records - 2
        """
    else:
        prompt = "No prompt found"
    return prompt