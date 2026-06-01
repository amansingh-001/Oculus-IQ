"""Agent router — Autonomous agent status, toggle, and log endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from core.responses import success_response
from services.autonomous_agent import autonomous_agent


router = APIRouter()


@router.get("/status")
async def agent_status():
    return success_response(autonomous_agent.get_status())


@router.post("/toggle")
async def toggle_agent():
    result = autonomous_agent.toggle()
    return success_response(result)


@router.get("/log")
async def agent_log():
    log = autonomous_agent.get_log()
    return success_response(log, meta={"total": len(log)})
