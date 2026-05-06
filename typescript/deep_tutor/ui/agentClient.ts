/**
 * agentClient.ts — LangGraph client
 *
 * This is the interesting file for students learning how to connect to a deployed
 * LangGraph agent. It shows how to:
 *
 *   1. Create a client connected to a LangGraph deployment
 *   2. Create and manage threads
 *   3. Send a message and stream the response back
 *   4. Create assistants (one per module, per student)
 *   5. Read and write student profiles and sessions via the LangGraph Store
 *
 * The deployment URL is derived from the incoming request — see deployment.ts.
 * The API key comes from .env — it never touches the browser.
 *
 * Documentation:
 *   LangGraph SDK (TypeScript): https://langchain-ai.github.io/langgraphjs/reference/
 */

import { Client } from "@langchain/langgraph-sdk";
import "dotenv/config";

export const MODULES = [
  { id: "module-1", label: "deployment architecture", active: true },
  { id: "module-2", label: "module 2", active: false },
  { id: "module-3", label: "module 3", active: false },
];

// ---------------------------------------------------------------------------
// 1. Create a client connected to a LangGraph deployment
// ---------------------------------------------------------------------------

export function createClient(deploymentUrl: string): Client {
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
  /**
   * Send a message to the agent and stream the response.
   *
   * Some LLMs return content as a list of typed blocks.
   * We include plain strings and type="text" blocks; skip others
   * (e.g. type="thinking" blocks from extended thinking models).
   */
  const printed: Record<string, number> = {};

  const eventStream = client.runs.stream(threadId, assistantId, {
    input: { messages: [{ role: "user", content: message }] },
    streamMode: "messages",
  });

  for await (const event of eventStream) {
    if (!Array.isArray(event.data)) continue;
    for (const item of event.data as Array<unknown>) {
      const msg = Array.isArray(item) ? item[0] : item;
      if (!msg || typeof msg !== "object") continue;
      const m = msg as Record<string, unknown>;
      if (m.type !== "AIMessageChunk" && m.type !== "AIMessage" && m.type !== "ai") continue;

      const msgId = (m.id as string) ?? "";
      let content = m.content;

      if (Array.isArray(content)) {
        const parts: string[] = [];
        for (const block of content as Array<unknown>) {
          if (typeof block === "string") {
            parts.push(block);
          } else if (block && typeof block === "object") {
            const b = block as Record<string, unknown>;
            if (b.type === "text") parts.push((b.text as string) ?? "");
          }
        }
        content = parts.join("");
      }

      if (typeof content === "string") {
        const already = printed[msgId] ?? 0;
        if (content.length > already) {
          yield content.slice(already);
          printed[msgId] = content.length;
        }
      }
    }
  }
}


// ---------------------------------------------------------------------------
// 3. Student setup — assistants and threads
//
// Called once at registration. Creates one assistant and one thread per module,
// each with the student's store namespace in the assistant context.
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


// ---------------------------------------------------------------------------
// 4. Student profile and sessions — LangGraph Store
//
// The Store provides persistent, cross-thread memory keyed by namespace.
// We use it to store the student's profile (name, goals) and session list.
// The deployed agent reads the profile at runtime to personalize responses.
// ---------------------------------------------------------------------------

export async function writeStudentProfile(
  client: Client,
  namespace: string,
  profile: Record<string, unknown>,
): Promise<void> {
  await client.store.putItem([namespace], "profile", profile);
}

export async function getStudentProfile(
  client: Client,
  namespace: string,
): Promise<Record<string, unknown> | null> {
  try {
    const item = await client.store.getItem([namespace], "profile");
    return item ? (item.value as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export async function writeStudentSessions(
  client: Client,
  namespace: string,
  sessions: Session[],
): Promise<void> {
  await client.store.putItem([namespace], "sessions", { sessions });
}

export async function getStudentSessions(
  client: Client,
  namespace: string,
): Promise<Session[] | null> {
  try {
    const item = await client.store.getItem([namespace], "sessions");
    if (!item) return null;
    return (item.value as { sessions: Session[] }).sessions ?? null;
  } catch {
    return null;
  }
}
