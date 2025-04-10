from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from build_graph import graph_builder
from helper import create_prompt
from db import pool

import os, sys, asyncio

load_dotenv()
DB_URI = os.getenv("DB_URI")

graph = None

# Fix for Windows event loop compatibility with psycopg async
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Keep the connection pool open as long as the app is alive."""
    global graph
  
    checkpointer = AsyncPostgresSaver(pool)
    # await checkpointer.setup()
    graph = graph_builder.compile(checkpointer=checkpointer)
    
    # try:
    #     with open("graph_output.png", "wb") as f:
    #         f.write(graph.get_graph().draw_mermaid_png())
    # except Exception as e:
    #     print("Exception while generating graph_output.png:", e)

    print("✅ Connection pool and graph initialized!")
    yield  # Yield control back to FastAPI while keeping the pool open

    await pool.close()
    print("❌ Connection pool closed!")

app = FastAPI(lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://portfolio-phi-mocha-72.vercel.app/", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserInput(BaseModel):
    user_input: str
    num_rewind: int = 0
    fingerprint: str

class ResumeInput(BaseModel):
    action: bool
    fingerprint: str

class WipeInput(BaseModel):
    fingerprint: str

async def stream_graph_updates(user_input: str, fingerprint: str, num_rewind: int, config: dict):
    state = {
        "messages": [SystemMessage(content=create_prompt(info=[], llm_type="chatbot")), {"role": "user", "content": user_input}],
        "fingerprint": fingerprint,
    }
    if num_rewind != 0:
        rewind(int(num_rewind), config, user_input)
    async for event in graph.astream(state, config):
        msg = ""
        if "__interrupt__" in event:
            return {"response":"", "other_name":"interrupt", "other_msg": None} #TODO: Turn other msg into tool name

        elif "tools" in event:
            # For tools that don't require human review
            pass

        elif "chatbot" in event:
            for value in event.values():
                msg = value["messages"][-1].content

        if msg:
            return {"response": msg, "other_name": None, "other_msg": None}

async def resume_graph_updates(action, config):
    msg = ""
    tool_name = None
    tool_msg = None
    try:
        async for resume_event in graph.astream(Command(resume={"action": action}), config):
            # print("Resume Event: ", resume_event)
            is_chatbot = resume_event.get("chatbot", False)
            is_rag = resume_event.get("rag", False)
            is_tool = resume_event.get("tools", False)
            
            if is_tool:
                tool_name = resume_event["tools"]["messages"][-1].get("name", None)
                tool_msg = resume_event["tools"]["messages"][-1].get("content", None)
                continue
            if is_chatbot:
                msg = resume_event["chatbot"]["messages"][-1].content
            elif is_rag:
                msg = resume_event["rag"]["messages"][-1].content
            
            if msg:
                return {"response": msg, "other_name": tool_name, "other_msg": tool_msg}
        
        return {"response": None, "other_name": tool_name, "other_msg": tool_msg}
    
    except Exception as e:
        print(f"❌ Error in resume(): {e}")
        return {"response": False, "other_name": None, "other_msg": None}
        
async def clear_thread(thread_id: str):
    """Deletes all records related to the given thread_id."""
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                await cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                await cursor.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))

                await conn.commit()
                # print(f"✅ Wiped data for thread_id: {thread_id}")
                return {"response": True, "other_name": None, "other_msg": None}

            except Exception as exception:
                await conn.rollback()
                print(f"❌ Error in wipe(): {exception}")
                return {"response": False, "other_name": None, "other_msg": None}

def rewind(num_rewind:int, config, user_input):
    #TODO: fix. essentially need to clear old states instead of appending, which is what update_state seems to do, and also figure out the most effective way to time travel without relying on node type perhaps.
    #? Alternatively, this could also be ignored and we can provide our own logic of checkpoint ids and just use these ids.
    num_encountered = 0
    for state in graph.get_state_history(config):
        if "chatbot" in state.next:
            num_encountered+=1
            if num_rewind == num_encountered:
                config = state.config
                last_message = state.values["messages"][-1]
                print("last message: ", last_message)
                new_message = HumanMessage(
                    content=user_input,
                    id=last_message.id
                )
                graph.update_state(config, {"messages": [new_message]})
                break
    # return config
    
@app.post("/resume")
async def resume_process(input: ResumeInput):
    try:
        action = input.action
        fingerprint = input.fingerprint
        if action is None:
            raise HTTPException(status_code=400, detail="Action is required.")
        if not fingerprint:
            raise HTTPException(status_code=400, detail="Fingerprint is required.")
        config = {"configurable": {"thread_id": fingerprint}}
        result = await resume_graph_updates(action, config)
        print("resume result: ", result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(input: UserInput):
    try:
        user_input = input.user_input
        num_rewind = input.num_rewind
        fingerprint = input.fingerprint
        if not fingerprint:
            raise HTTPException(status_code=400, detail="Fingerprint is required.")
        config = {"configurable": {"thread_id": fingerprint}}
        
        result = await stream_graph_updates(user_input, fingerprint, num_rewind, config)
        # print("chat result: ", result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/wipe")
# Should be used to wipe history when user leaves site or wants to
async def wipe(input: WipeInput):
    try:
        fingerprint = input.fingerprint
        if not fingerprint:
            raise HTTPException(status_code=400, detail="Fingerprint is required.")
        result = await clear_thread(fingerprint)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
