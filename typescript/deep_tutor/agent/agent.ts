/**
 * Deep Tutor Agent — TypeScript
 *
 * Tutor agent using createDeepAgent with FilesystemBackend.
 *
 * Personality and teaching guidelines are loaded from AGENTS.md via MemoryMiddleware.
 * Module skills are loaded from /skills/ via SkillsMiddleware (progressive disclosure).
 * A custom middleware injects per-session context: student name, module, and goals.
 *
 * Assistant context (set per assistant in LangSmith):
 * - module_id:       which module to load (e.g. "module-1")
 * - store_namespace: student's Store namespace (derived from email, e.g. "jane@example_com")
 */

import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

import { createDeepAgent, FilesystemBackend } from "deepagents";
import { createMiddleware } from "langchain";
import { getConfig, getStore } from "@langchain/langgraph";
// import { ChatGoogleGenerativeAI } from "@langchain/google-genai";  // NOTE: Gemini 2.5 Flash returns empty output with multi-block system messages — use Anthropic or OpenAI
// import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";
import { MultiServerMCPClient } from "@langchain/mcp-adapters";

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------
const model = new ChatAnthropic({ model: "claude-sonnet-4-6" });
// const model = new ChatOpenAI({ model: "gpt-4o" });
// const model = new ChatGoogleGenerativeAI({ model: "gemini-2.5-flash" }); // see note above

// ---------------------------------------------------------------------------
// Context schema
// ---------------------------------------------------------------------------
const contextSchema = z.object({
  module_id: z.string().default("module-1"),
  store_namespace: z.string().default(""), // derived from student email
});

// ---------------------------------------------------------------------------
// Dynamic system prompt middleware
//
// Uses createMiddleware + wrapModelCall to APPEND to the system message
// rather than replace it, so memory and skills layers built by createDeepAgent
// are preserved.
// ---------------------------------------------------------------------------
const tutorPrompt = createMiddleware({
  name: "TutorPrompt",

  async wrapModelCall(request: any, handler: any) {
    const ctx = (getConfig().context ?? {}) as Record<string, string>;
    const moduleId = ctx.module_id ?? "module-1";
    const storeNamespace = ctx.store_namespace ?? "";
    let studentName = "Student";
    let goals = "";

    if (storeNamespace) {
      const store = getStore();
      if (store) {
        const item = await store.get([storeNamespace], "profile");
        if (item) {
          const profile = item.value as Record<string, string>;
          const fullName = `${profile.first_name ?? ""} ${profile.last_name ?? ""}`.trim();
          if (fullName) studentName = fullName;
          if (profile.goals) goals = profile.goals;
        }
      }
    }

    const goalsLine = goals ? `\n\nThe student's goals: ${goals}` : "";
    const promptText =
      `Your student's name is ${studentName}. ` +
      `They are working on ${moduleId}.${goalsLine}\n\n` +
      `On your first response, read /skills/${moduleId}/SKILL.md. ` +
      `That file contains your teaching instructions — follow them. ` +
      `When you need to answer a factual question, read /skills/${moduleId}/information.md.`;

    return handler({
      ...request,
      systemMessage: request.systemMessage.concat(promptText),
    });
  },
});

// ---------------------------------------------------------------------------
// MCP tools
// ---------------------------------------------------------------------------
const mcpClient = new MultiServerMCPClient({
  docs: {
    url: "https://docs.langchain.com/mcp",
    transport: "http",
  },
});

const mcpTools = await mcpClient.getTools();

// ---------------------------------------------------------------------------
// Agent
// ---------------------------------------------------------------------------
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const backend = new FilesystemBackend({
  rootDir: path.join(__dirname, ".."),
  virtualMode: true,
});

export const graph = await createDeepAgent({
  model,
  tools: mcpTools,
  middleware: [tutorPrompt],
  backend,
  memory: ["/AGENTS.md"],
  skills: ["/skills/"],
  permissions: [
    { operations: ["write"], paths: ["/skills/**"], mode: "deny" },
  ],
  contextSchema,
});
