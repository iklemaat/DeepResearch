import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Construct the absolute path to the frontend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Add the inference subdirectory to the Python path
sys.path.append(os.path.join(BASE_DIR, 'inference'))

from react_agent import MultiTurnReactAgent

app = FastAPI()

# Mount the frontend directory to serve static files
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

class RunRequest(BaseModel):
    question: str
    openrouter_api_key: str
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    serper_api_key: str
    jina_api_key: str

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))

@app.post("/api/run")
async def run_agent(request: RunRequest):
    # Set API keys as environment variables for the tools to use
    os.environ['SERPER_KEY_ID'] = request.serper_api_key
    os.environ['JINA_API_KEYS'] = request.jina_api_key

    llm_cfg = {
        'model': 'alibaba/tongyi-deepresearch-30b-a3b',
        'generate_cfg': {
            'temperature': 0.6,
            'top_p': 0.95,
            'presence_penalty': 1.1,
        }
    }

    agent = MultiTurnReactAgent(
        llm=llm_cfg,
        function_list=["search", "visit", "google_scholar", "PythonInterpreter", "parse_file"]
    )

    try:
        result = agent._run(
            question=request.question,
            openrouter_api_key=request.openrouter_api_key,
            openrouter_api_base=request.openrouter_api_base
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
