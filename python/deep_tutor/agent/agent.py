"""
Deep Chat Tutor Agent

Tutor agent using create_deep_agent with StoreBackend.
Module content is stored as skills in /modules/ in the LangGraph Store.

Assistant context (set per assistant in LangSmith):
- module_id:       which module to load (e.g. "module-1")
- store_namespace: student namespace (first_last), used to look up store data
- student_name:    student's first name, used to personalize responses
"""

import asyncio
from dataclasses import dataclass

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.permissions import FilesystemPermission
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
model = init_chat_model("google_genai:gemini-2.5-flash")
# model = init_chat_model("openai:gpt-4o")
# model = init_chat_model("anthropic:claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# Context schema
# ---------------------------------------------------------------------------
@dataclass
class ContextSchema:
    module_id: str = "module-1"
    student_name: str = "Student"
    store_namespace: str = ""
    goals: str = ""


# ---------------------------------------------------------------------------
# Dynamic system prompt
# ---------------------------------------------------------------------------
@dynamic_prompt
async def tutor_prompt(request: ModelRequest) -> str:
    module_id = request.runtime.context.module_id
    student_name = request.runtime.context.student_name
    store_namespace = request.runtime.context.store_namespace
    goals = request.runtime.context.goals

    # Read the latest profile from the Store so data stays current across logins.
    # store_namespace is the only thing needed from context — it's the key to the student's data.
    if store_namespace and request.runtime.store:
        item = await request.runtime.store.aget((store_namespace,), key="profile")
        if item is not None:
            profile = item.value
            student_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or student_name
            goals = profile.get("goals", goals)

    goals_line = f"\n\nThe student's goals: {goals}" if goals else ""
    return (
        f"You are a tutor agent. Your student's name is {student_name}. "
        f"They are working on {module_id}.{goals_line}\n\n"
        f"On your first response, read the SKILL.md for {module_id} from /skills/{module_id}/SKILL.md. "
        f"That file contains your teaching instructions — follow them. "
        f"When you need to answer a factual question, read /skills/{module_id}/information.md."
    )


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------
_mcp_client = MultiServerMCPClient({
    "docs": {
        "url": "https://docs.langchain.com/mcp",
        "transport": "http",
    }
})
mcp_tools = asyncio.run(_mcp_client.get_tools())


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
# TODO: swap to StoreBackend + cron sync when content management is ready
backend = FilesystemBackend(
    root_dir=Path(__file__).parent.parent,
    virtual_mode=True,
)

graph = create_deep_agent(
    model=model,
    tools=[*mcp_tools],
    middleware=[tutor_prompt],
    backend=backend,
    skills=["/skills/"],
    permissions=[
        FilesystemPermission(operations=["write"], paths=["/skills/**"], mode="deny"),
    ],
    context_schema=ContextSchema,
)
