/**
 * agent_client.ts — LangGraph Cloud client
 *
 * This is the interesting file for students learning how to connect to a deployed
 * LangGraph agent. It shows how to:
 *
 *   1. Create a client connected to a LangGraph Cloud deployment
 *   2. Create and manage threads
 *   3. Send a message and stream the response back
 *
 * Documentation:
 *   LangGraph SDK (TypeScript): https://langchain-ai.github.io/langgraphjs/reference/
 */

import { Client } from "@langchain/langgraph-sdk";

// ---------------------------------------------------------------------------
// 1. Create a client connected to your LangGraph Cloud deployment
// ---------------------------------------------------------------------------

export function createLangGraphClient(): Client {
  const url = process.env.LANGGRAPH_URL;
  const apiKey = process.env.LANGSMITH_API_KEY;

  if (!url || !apiKey) {
    throw new Error("LANGGRAPH_URL and LANGSMITH_API_KEY must be set in .env");
  }

  return new Client({ apiUrl: url, apiKey });
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
  message: string
): AsyncGenerator<string> {
  /**
   * Send a message to the agent and yield response text chunks as they arrive.
   *
   * @param client - LangGraph Cloud client
   * @param threadId - The thread to send the message on
   * @param assistantId - Which assistant (agent graph) to use — e.g. "tutor"
   * @param message - The user's message
   *
   * Yields text chunks from the agent's response.
   */
  const stream = client.runs.stream(threadId, assistantId, {
    input: { messages: [{ role: "user", content: message }] },
    streamMode: "messages",
  });

  for await (const event of stream) {
    if (event.event === "messages/partial") {
      for (const msg of event.data as Array<Record<string, unknown>>) {
        if (msg.type === "AIMessageChunk" || msg.type === "AIMessage" || msg.type === "ai") {
          const content = msg.content;
          if (typeof content === "string") {
            yield content;
          } else if (Array.isArray(content)) {
            for (const block of content as Array<Record<string, unknown>>) {
              if (block.type === "text" && typeof block.text === "string") {
                yield block.text;
              }
            }
          }
        }
      }
    }
  }
}
