/**
 * agentClient.ts — LangGraph client (with Supabase auth threading)
 *
 * Each call to createClient takes an optional `jwt` — when present, it is sent
 * as `Authorization: Bearer <jwt>` so the deployment's @auth.authenticate
 * handler can validate it.  Otherwise the LangSmith API key is used (and the
 * request fails @auth.authenticate, since that handler only accepts bearer
 * tokens).
 *
 * Documentation:
 *   LangGraph SDK (TypeScript): https://langchain-ai.github.io/langgraphjs/reference/
 */

import { Client } from "@langchain/langgraph-sdk";
import dotenv from "dotenv";
dotenv.config({ override: true });

export const MODULES = [
  { id: "module-1", label: "deployment architecture", active: true },
  { id: "module-2", label: "using your deployment", active: true },
  { id: "module-3", label: "dashboard", active: true },
  { id: "module-4", label: "storage", active: true },
  { id: "module-5", label: "auth", active: true },
  { id: "module-6", label: "deepagents cli", active: true },
];

// ---------------------------------------------------------------------------
// 1. Create a client connected to a LangGraph deployment
// ---------------------------------------------------------------------------

export function createClient(deploymentUrl: string, jwt?: string): Client {
  if (jwt) {
    return new Client({
      apiUrl: deploymentUrl,
      defaultHeaders: { Authorization: `Bearer ${jwt}` },
    });
  }
  const apiKey = process.env.LANGSMITH_API_KEY ?? "";
  return new Client({ apiUrl: deploymentUrl, apiKey });
}


// ---------------------------------------------------------------------------
// 2. Send a message and stream the response
// ---------------------------------------------------------------------------

export async function* streamResponse(
  client: Client,
  threadId: string,
  assistantId: string,
  message: string,
): AsyncGenerator<string> {
  const eventStream = client.runs.stream(threadId, assistantId, {
    input: { messages: [{ role: "user", content: message }] },
    streamMode: "messages-tuple",
  });

  for await (const event of eventStream) {
    if (event.event !== "messages") continue;
    const [messageChunk] = event.data as [Record<string, unknown>, unknown];
    if (messageChunk.type !== "ai") continue;  // skip tool calls / tool results — show only the agent's reply
    let content = messageChunk.content;

    if (Array.isArray(content)) {
      content = (content as Array<unknown>)
        .filter((b): b is Record<string, unknown> => !!b && typeof b === "object" && (b as Record<string, unknown>).type === "text")
        .map((b) => (b.text as string) ?? "")
        .join("");
    }

    if (typeof content === "string" && content) {
      yield content;
    }
  }
}


// ---------------------------------------------------------------------------
// 3. Student setup — assistants and threads
// ---------------------------------------------------------------------------

export interface Session {
  module_id: string;
  assistant_id: string;
  thread_id: string;
}

export async function createStudentSessions(
  client: Client,
  namespace: string,
  studentName = "Student",
): Promise<Session[]> {
  const sessions: Session[] = [];
  for (const mod of MODULES) {
    const assistant = await client.assistants.create({
      graphId: "tutor",
      name: `${studentName} — ${mod.id}`,
      context: {
        module_id: mod.id,
        store_namespace: namespace,
      },
    });
    const thread = await client.threads.create();
    sessions.push({
      module_id: mod.id,
      assistant_id: assistant.assistant_id,
      thread_id: thread.thread_id,
    });
  }
  return sessions;
}
