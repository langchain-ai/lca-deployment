/**
 * LangChat Tutor Agent — TypeScript
 *
 * This file defines the tutor agent using LangChain's createAgent.
 * It is the main entry point for LangGraph Cloud deployment.
 *
 * The agent uses:
 * - Gemini (default) via initChatModel — swap to any supported provider by uncommenting below
 * - readLessonMaterial tool — reads lesson content from the tutor_lx/ directory
 * - LangChain MCP docs server — for documentation lookups beyond the lesson material
 *
 * Assistant context (set per assistant in LangSmith):
 * - lessonId:       which lesson to load instructions and material for (e.g. "tutor_l1")
 * - storeNamespace: student namespace (first_last), used to look up store data
 * - studentName:    student's first name, used to personalize responses
 */

import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import * as z from "zod";

import { createAgent, dynamicSystemPromptMiddleware, tool, type ToolRuntime } from "langchain";
import { initChatModel } from "langchain/chat_models/universal";
import { MultiServerMCPClient } from "@langchain/mcp-adapters";

import { SYSTEM_PROMPT as BASE_SYSTEM_PROMPT } from "./systemPrompt.js";

// ---------------------------------------------------------------------------
// Model — uncomment the provider you want to use
// All provider packages are installed; set the matching API key in .env
// ---------------------------------------------------------------------------
const model = await initChatModel("google_genai:gemini-2.5-flash");    // Gemini (default — generous free tier)
// const model = await initChatModel("openai:gpt-4o");                 // OpenAI
// const model = await initChatModel("anthropic:claude-sonnet-4-6");   // Anthropic
// const model = await initChatModel("ollama:llama3.2");               // Ollama (local)

const LESSONS_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");


// ---------------------------------------------------------------------------
// Context schema — injected by LangGraph Cloud from assistant context dict
// ---------------------------------------------------------------------------
const contextSchema = z.object({
  lessonId: z.string().default("tutor_l1"),
  studentName: z.string().default("Student"),
  storeNamespace: z.string().default(""),
});

type Context = z.infer<typeof contextSchema>;


function loadLessonInstructions(lessonId: string): string {
  const instructionsFile = path.join(LESSONS_DIR, lessonId, `${lessonId}_instructions.md`);
  if (!fs.existsSync(instructionsFile)) {
    return `(No instructions file found for lesson '${lessonId}')`;
  }
  return fs.readFileSync(instructionsFile, "utf-8");
}


// ---------------------------------------------------------------------------
// Dynamic system prompt — reads lessonId and studentName from assistant context
// ---------------------------------------------------------------------------
const lessonPrompt = dynamicSystemPromptMiddleware<Context>((state, runtime) => {
  const lessonId = runtime.context.lessonId;
  const studentName = runtime.context.studentName;
  const instructions = loadLessonInstructions(lessonId);
  return (
    `${BASE_SYSTEM_PROMPT}\n\n` +
    `## Current session\n` +
    `Student: ${studentName}\n` +
    `Lesson: ${lessonId}\n\n` +
    `## Lesson instructions\n\n` +
    instructions
  );
});


// ---------------------------------------------------------------------------
// Lesson material tool
// Reads the information file for the current lesson from assistant context
// ---------------------------------------------------------------------------
const readLessonMaterial = tool(
  async (_: object, runtime: ToolRuntime<Context>) => {
    const lessonId = runtime.context.lessonId;
    const infoFile = path.join(LESSONS_DIR, lessonId, `${lessonId}_information.md`);
    if (!fs.existsSync(infoFile)) {
      return `Lesson material not found for '${lessonId}'.`;
    }
    return fs.readFileSync(infoFile, "utf-8");
  },
  {
    name: "read_lesson_material",
    description:
      "Read the reference material for the current lesson. " +
      "Use this tool when you need to answer a student's question or quiz them. " +
      "Always check the lesson material before answering.",
    schema: z.object({}),
  }
);


// ---------------------------------------------------------------------------
// MCP tools — LangChain/LangGraph/LangSmith docs search
// ---------------------------------------------------------------------------
const mcpClient = new MultiServerMCPClient({
  "docs": {
    url: "https://docs.langchain.com/mcp",
    transport: "streamable_http",
  },
});

const mcpTools = await mcpClient.getTools();


// ---------------------------------------------------------------------------
// Agent
// ---------------------------------------------------------------------------
export const graph = createAgent({
  model,
  tools: [readLessonMaterial, ...mcpTools],
  middleware: [lessonPrompt],
  contextSchema,
});
