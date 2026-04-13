/**
 * agent_client.ts — LangGraph client
 *
 * This is the interesting file for students learning how to connect to a deployed
 * LangGraph agent. It shows how to:
 *
 *   1. Create a client connected to a LangGraph deployment
 *   2. Create and manage threads
 *   3. Send a message and stream the response back
 *   4. Create assistants (one per lesson, per student)
 *   5. Read and write student profiles via the LangGraph Store
 *
 * The deployment URL comes from the UI (students paste their URL in).
 * The API key comes from .env — it never touches the browser.
 *
 * Documentation:
 *   LangGraph SDK (TypeScript): https://langchain-ai.github.io/langgraphjs/reference/
 */

import { Client } from "@langchain/langgraph-sdk";
import "dotenv/config";

// Lessons available in this course
export const LESSONS = [
  { id: "tutor_l1", label: "deployment architecture", active: true },
  { id: "tutor_l2", label: "connecting to a deployment", active: true },
  { id: "tutor_l3", label: "lesson 3", active: false },
  { id: "tutor_l4", label: "lesson 4", active: false },
  { id: "tutor_l5", label: "lesson 5", active: false },
  { id: "tutor_l6", label: "lesson 6", active: false },
  { id: "tutor_l7", label: "lesson 7", active: false },
];

// ---------------------------------------------------------------------------
// 1. Create a client connected to a LangGraph deployment
//    URL comes from the UI; API key comes from .env
// ---------------------------------------------------------------------------

export function createClient(deploymentUrl: string): Client {
  const apiKey = process.env.LANGSMITH_API_KEY ?? "";
  return new Client({ apiUrl: deploymentUrl, apiKey });
}


// ---------------------------------------------------------------------------
// 2. Thread management
// ---------------------------------------------------------------------------

export async function createThread(client: Client): Promise<string> {
  /** Create a new conversation thread. Returns the thread_id. */
  const thread = await client.threads.create();
  return thread.thread_id;
}


// ---------------------------------------------------------------------------
// 3. Send a message and stream the response
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
   * Yields text chunks from the agent's response.
   *
   * Gemini 2.5 Flash uses extended thinking: content is a list with two blocks —
   * block[0] is the thinking block (dict with extras.signature — skip it),
   * block[1] is the actual response (plain string — include it).
   */
  const printed: Record<string, number> = {}; // track cumulative content per message ID

  const stream = client.runs.stream(threadId, assistantId, {
    input: { messages: [{ role: "user", content: message }] },
    streamMode: "messages",
  });

  for await (const event of stream) {
    if (!Array.isArray(event.data)) continue;
    for (const item of event.data as Array<unknown>) {
      const msg = Array.isArray(item) ? item[0] : item;
      if (!msg || typeof msg !== "object") continue;
      const m = msg as Record<string, unknown>;
      if (m.type !== "AIMessageChunk" && m.type !== "AIMessage" && m.type !== "ai") continue;

      const msgId = (m.id as string) ?? "";
      let content = m.content;

      if (Array.isArray(content)) {
        // Normalize list content blocks — skip Gemini thinking blocks
        const parts: string[] = [];
        for (const block of content as Array<unknown>) {
          if (typeof block === "string") {
            parts.push(block);
          } else if (block && typeof block === "object") {
            const b = block as Record<string, unknown>;
            const extras = b.extras as Record<string, unknown> | undefined;
            if (b.type === "text" && !extras?.signature) {
              parts.push((b.text as string) ?? "");
            }
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
// 4. Student setup — assistants and threads
//
// Called once when a student hits Start. Creates one assistant and one thread
// per lesson, each with the student's store namespace in the assistant context.
// ---------------------------------------------------------------------------

export interface Session {
  lesson_id: string;
  assistant_id: string;
  thread_id: string;
}

export async function createStudentSessions(
  client: Client,
  namespace: string,
  studentName = "Student",
): Promise<Session[]> {
  /**
   * Create one assistant + thread per lesson for a student.
   *
   * @param client - LangGraph client
   * @param namespace - Student namespace (first_last), used as Store key prefix
   * @param studentName - Student's display name, included in assistant context
   * @returns List of session objects: [{lesson_id, assistant_id, thread_id}, ...]
   */
  const sessions: Session[] = [];
  for (const lesson of LESSONS) {
    const assistant = await client.assistants.create({
      graphId: "tutor",
      name: `${namespace} — ${lesson.id}`,
      context: {
        lesson_id: lesson.id,
        store_namespace: namespace,
        student_name: studentName,
      },
    });
    const thread = await client.threads.create();
    sessions.push({
      lesson_id: lesson.id,
      assistant_id: assistant.assistant_id,
      thread_id: thread.thread_id,
    });
  }
  return sessions;
}


// ---------------------------------------------------------------------------
// 5. Student profile — LangGraph Store
//
// The Store provides persistent, cross-thread memory keyed by namespace.
// We use it to store the student's profile (name, goals, preferences).
// The deployed agent reads this at runtime to personalize responses.
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
