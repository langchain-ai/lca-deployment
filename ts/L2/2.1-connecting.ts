/**
 * 2.1 — Connecting an Assistant to a Deployment
 *
 * This file shows the steps to connect a LangSmith assistant to a deployed
 * LangGraph agent.
 *
 * An assistant is a configuration layer on top of a deployed graph. It lets you:
 * - Set a custom system prompt
 * - Configure model and tool settings
 * - Create multiple variants of the same graph
 *
 * Steps:
 *   1. Connect to your deployment
 *   2. List available graphs (to find the graph_id)
 *   3. Create an assistant pointing to your graph
 *   4. Update the assistant with a system prompt (context)
 *   5. Run a thread using the assistant
 *   6. Delete the assistant when done
 *
 * Once you have created a client and set up an assistant:
 * - Context (system prompt, model config) is stored server-side on the assistant.
 *   You do NOT resend it on every call — the server applies it automatically
 *   whenever you use that assistant_id.
 * - Config (e.g. thread_id) is passed per run. It is ephemeral — you pass it
 *   each time to identify the conversation thread.
 * - Assistants are configuration records only — deleting one does not affect
 *   compute resources or running containers.
 *
 * Documentation:
 *   LangSmith Assistants:       https://docs.langchain.com/langsmith/assistants
 *   Create Assistant API:       https://docs.langchain.com/langsmith/agent-server-api/assistants/create-assistant
 *   Patch Assistant API:        https://docs.langchain.com/langsmith/agent-server-api/assistants/patch-assistant
 *   Delete Assistant API:       https://docs.langchain.com/langsmith/agent-server-api/assistants/delete-assistant
 *   SDK examples:               https://docs.langchain.com/langsmith/configuration-cloud
 *   LangGraph SDK (TypeScript): https://langchain-ai.github.io/langgraphjs/reference/
 */

import "dotenv/config";
import { Client } from "@langchain/langgraph-sdk";

const DEPLOYMENT_URL = process.env.LANGGRAPH_URL ?? "http://127.0.0.1:2024";
const API_KEY = process.env.LANGSMITH_API_KEY ?? "";

async function main() {

  // ---------------------------------------------------------------------------
  // Step 1: Connect to your deployment
  // ---------------------------------------------------------------------------

  const client = new Client({ apiUrl: DEPLOYMENT_URL, apiKey: API_KEY });

  // ---------------------------------------------------------------------------
  // Step 2: List available assistants/graphs
  // ---------------------------------------------------------------------------

  const assistants = await client.assistants.search();
  console.log("Available assistants/graphs:");
  for (const a of assistants) {
    console.log(`  graph_id=${a.graph_id}  assistant_id=${a.assistant_id}  name=${a.name}`);
  }

  // ---------------------------------------------------------------------------
  // Step 3: Create an assistant for a graph
  //
  // A default assistant is created automatically for each graph when you deploy.
  // Use this step if you want a named assistant with custom configuration.
  // ---------------------------------------------------------------------------

  let assistant = await client.assistants.create({
    graphId: "tutor",
    name: "Tutor — Lesson 1",
    context: {},
  });
  console.log(`\nCreated assistant: ${assistant.assistant_id}  name=${assistant.name}`);

  // ---------------------------------------------------------------------------
  // Step 4: Update the assistant with a system prompt
  //
  // The system prompt is passed via the `context` field.
  // NOTE: When updating, include ALL context fields — not just the ones changing.
  // ---------------------------------------------------------------------------

  assistant = await client.assistants.update(assistant.assistant_id, {
    context: {
      lesson_id: "tutor_l1",
      student_name: "Student",
    },
  });
  console.log(`Updated assistant: ${assistant.assistant_id}`);

  // ---------------------------------------------------------------------------
  // Step 5: Run a thread using the assistant
  // ---------------------------------------------------------------------------

  const thread = await client.threads.create();
  console.log(`\nThread: ${thread.thread_id}`);

  let printed = 0; // track cumulative content already printed
  const stream = client.runs.stream(thread.thread_id, assistant.assistant_id, {
    input: { messages: [{ role: "user", content: "What is the Agent Server?" }] },
    streamMode: "messages",
  });

  for await (const event of stream) {
    if (Array.isArray(event.data)) {
      for (const item of event.data as Array<unknown>) {
        const msg = Array.isArray(item) ? item[0] : item;
        if (msg && typeof msg === "object") {
          const m = msg as Record<string, unknown>;
          if (m.type === "AIMessageChunk" || m.type === "AIMessage" || m.type === "ai") {
            if (typeof m.content === "string" && m.content.length > printed) {
              process.stdout.write(m.content.slice(printed));
              printed = m.content.length;
            }
          }
        }
      }
    }
  }
  console.log();

  // ---------------------------------------------------------------------------
  // Step 6: Delete the assistant
  //
  // Frees the configuration record. Does not affect compute resources.
  // ---------------------------------------------------------------------------

  await client.assistants.delete(assistant.assistant_id);
  console.log(`\nDeleted assistant: ${assistant.assistant_id}`);
}

main().catch(console.error);
