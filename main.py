from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os

# Add the inference directory to the sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'inference'))

from react_agent import MultiTurnReactAgent
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

class InvestigateRequest(BaseModel):
    question: str
    deepseek_api_key: str
    openrouter_api_key: str
    brave_api_key: str

# Use a ThreadPoolExecutor to run synchronous code in an async context
executor = ThreadPoolExecutor(max_workers=10)

@app.post("/investigate")
async def investigate(request: InvestigateRequest):
    loop = asyncio.get_event_loop()

    # This is a simplified instantiation for the refactored agent
    llm_config = {
        "model": None # model path is not strictly needed anymore for token counting
    }
    agent = MultiTurnReactAgent(llm=llm_config)

    data = {'item': {'question': request.question, 'answer': ''}}
    api_keys = {
        'deepseek': request.deepseek_api_key,
        'openrouter': request.openrouter_api_key,
        'brave': request.brave_api_key,
    }

    try:
        # Run the synchronous _run method in a separate thread
        result = await loop.run_in_executor(
            executor,
            agent._run,
            data,
            api_keys
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount the frontend directory to serve static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
