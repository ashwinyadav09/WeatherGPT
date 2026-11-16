from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.api.app.conversation.agent import ChatRequest, ConversationAgent

router = APIRouter(prefix="/chat", tags=["chat"])
_agent = ConversationAgent()


@router.post("")
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
    async def event_generator():
        async for event in _agent.run_chat(req):
            event_type = event["event"]
            data_str = json.dumps(event["data"], ensure_ascii=False)
            yield f"event: {event_type}\ndata: {data_str}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
