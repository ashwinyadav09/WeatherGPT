"""Conversation Agent shim pointing to Orchestrator (Ticket R2.3).

Per remediation plan (Section 3 & 4), conversation/agent.py is replaced
by services/api/app/agent/orchestrator.py.
"""
from __future__ import annotations

from services.api.app.agent.orchestrator import ChatRequest, Orchestrator

# Re-export Orchestrator as ConversationAgent for backward compatibility
ConversationAgent = Orchestrator

__all__ = ["ChatRequest", "ConversationAgent", "Orchestrator"]
