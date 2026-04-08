/**
 * LangChat Tutor Agent — TypeScript
 *
 * This file defines the tutor agent using Deep Agents.
 * It is the main entry point for LangGraph Cloud deployment.
 *
 * The agent uses:
 * - Gemini (default) via initChatModel — swap to any supported provider by uncommenting below
 * - readLessonMaterial tool — reads lesson content from the tutor_l1/ directory
 * - LangChain MCP docs server — for documentation lookups beyond the lesson material
 */

import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

import { createDeepAgent } from "deepagents";
import { initChatModel } from "langchain/chat_models/universal";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { MultiServerMCPClient } from "@langchain/mcp-adapters";

import { SYSTEM_PROMPT } from "./systemPrompt.js";

// ---------------------------------------------------------------------------
// Model — uncomment the provider you want to use
// All provider packages are installed; set the matching API key in .env
// ---------------------------------------------------------------------------
const model = await initChatModel("google_genai:gemini-2.5-flash");    // Gemini (default — generous free tier)
// const model = await initChatModel("openai:gpt-4o");                 // OpenAI
// const model = await initChatModel("anthropic:claude-sonnet-4-6");   // Anthropic
// const model = await initChatModel("ollama:llama3.2");               // Ollama (local)

// ---------------------------------------------------------------------------
// Lesson material tool
// Reads tutor_l1_information.md from the tutor_l1/ directory next to agent/
// ---------------------------------------------------------------------------
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LESSON_DIR = path.join(__dirname, "..", "tutor_l1");

const readLessonMaterial = tool(
  async () => {
    const infoFile = path.join(LESSON_DIR, "tutor_l1_information.md");
    if (!fs.existsSync(infoFile)) {
      return "Lesson material not found.";
    }
    return fs.readFileSync(infoFile, "utf-8");
  },
  {
    name: "read_lesson_material",
    description:
      "Read the lesson material for the current lesson. " +
      "Use this tool when you need to answer a student's question or quiz them. " +
      "Always check the lesson material before falling back to the MCP docs server.",
    schema: z.object({}),
  }
);

// ---------------------------------------------------------------------------
// MCP tools — LangChain documentation server
// Loaded once at startup; used as fallback when lesson material isn't enough
// ---------------------------------------------------------------------------
const mcpClient = new MultiServerMCPClient({
  "langchain-docs": {
    url: "https://docs.langchain.com/mcp",
    transport: "streamable_http",
  },
});

const mcpTools = await mcpClient.getTools();

// ---------------------------------------------------------------------------
// Agent
// ---------------------------------------------------------------------------
export const graph = await createDeepAgent({
  model,
  tools: [readLessonMaterial, ...mcpTools],
  systemPrompt: SYSTEM_PROMPT,
});
