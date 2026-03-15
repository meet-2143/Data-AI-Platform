from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from handlers.streaming import create_agent_stream
from services.agent_service import create_bedrock_model, create_conversation_manager
import time

from models.request_models import InvokeStrandsAgentBodyDetails
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/invoke_strands_agent/")
async def invoke_strands_agent(body: InvokeStrandsAgentBodyDetails):
    """
    End Point for invoking strands agent
    """
    start_time = time.time()
    try:

        if not body.prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "Prompt cannot be empty"}
            )   

        async def agent_stream():
            try:
                async for chunk in create_agent_stream(body=body):
                    yield chunk
            except Exception as e:
                print(e)

            finally:
                end_time = time.time()
                print(f"Total Execution Time: {end_time - start_time:.3f} seconds")

        return StreamingResponse(agent_stream(), media_type="text/event-stream")

    except Exception as e:
        print(e)
        end_time = time.time()
        print(f"Total Execution Time (FAILED): {end_time - start_time:.3f} seconds")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to initialize agent", "details": str(e)}
        )