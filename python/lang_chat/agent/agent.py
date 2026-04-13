"""
LangChat Tutor Agent — Python

This file defines the tutor agent using LangChain's create_agent.
It is the main entry point for LangGraph Cloud deployment.

The agent uses:
- Gemini (default) via init_chat_model — swap to any supported provider by uncommenting below
- read_lesson_material tool — reads lesson content from the tutor_lx/ directory

Assistant context (set per assistant in LangSmith):
- lesson_id:       which lesson to load instructions and material for (e.g. "tutor_l1")
- store_namespace: student namespace (first_last), used to look up store data
- student_name:    student's first name, used to personalize responses
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langchain_mcp_adapters.client import MultiServerMCPClient

import sys
sys.path.insert(0, str(Path(__file__).parent))
from system_prompt import BASE_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Model — uncomment the provider you want to use
# All provider packages are installed; set the matching API key in .env
# ---------------------------------------------------------------------------
model = init_chat_model("google_genai:gemini-2.5-flash")        # Gemini (default)
# model = init_chat_model("openai:gpt-4o")                    # OpenAI
# model = init_chat_model("anthropic:claude-sonnet-4-6")      # Anthropic
# model = init_chat_model("ollama:llama3.2")                  # Ollama (local)

LESSONS_DIR = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Context schema — injected by LangGraph Cloud from assistant context dict
# ---------------------------------------------------------------------------
@dataclass
class ContextSchema:
    lesson_id: str = "tutor_l1"
    student_name: str = "Student"
    store_namespace: str = ""


def _load_lesson_instructions(lesson_id: str) -> str:
    instructions_file = LESSONS_DIR / lesson_id / f"{lesson_id}_instructions.md"
    if not instructions_file.exists():
        return f"(No instructions file found for lesson '{lesson_id}')"
    return instructions_file.read_text()


# ---------------------------------------------------------------------------
# Dynamic system prompt — reads lesson_id and student_name from assistant context
# ---------------------------------------------------------------------------
@dynamic_prompt
def lesson_prompt(request: ModelRequest) -> str:
    lesson_id = request.runtime.context.lesson_id
    student_name = request.runtime.context.student_name
    instructions = _load_lesson_instructions(lesson_id)
    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"## Current session\n"
        f"Student: {student_name}\n"
        f"Lesson: {lesson_id}\n\n"
        f"## Lesson instructions\n\n"
        f"{instructions}"
    )


# ---------------------------------------------------------------------------
# Lesson material tool
# Reads the information file for the current lesson from assistant context
# ---------------------------------------------------------------------------
@tool
def read_lesson_material(runtime: ToolRuntime[ContextSchema]) -> str:
    """Read the reference material for the current lesson.

    Use this tool when you need to answer a student's question or quiz them.
    Always check the lesson material before answering.
    """
    lesson_id = runtime.context.lesson_id
    info_file = LESSONS_DIR / lesson_id / f"{lesson_id}_information.md"
    if not info_file.exists():
        return f"Lesson material not found for '{lesson_id}'."
    return info_file.read_text()


# ---------------------------------------------------------------------------
# MCP tools — LangChain/LangGraph/LangSmith docs search
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
graph = create_agent(
    model=model,
    tools=[read_lesson_material, *mcp_tools],
    middleware=[lesson_prompt],
    context_schema=ContextSchema,
)
