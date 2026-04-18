/**
 * app.ts — Hono custom routes app
 *
 * Serves index.html and provides endpoints that proxy requests to the agent
 * via agent_client.ts.
 *
 * Registered as a custom route in langgraph.json via the http.app field.
 * The deployment URL is derived from the incoming request — see deployment.ts.
 *
 * Run locally with:
 *   npx @langchain/langgraph-cli dev
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { Hono } from "hono";
import { stream } from "hono/streaming";

import {
  LESSONS,
  createClient,
  createStudentSessions,
  getStudentProfile,
  streamResponse,
  writeStudentProfile,
} from "./agent_client.js";
import { getDeploymentUrl } from "./deployment.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const indexHtml = readFileSync(join(__dirname, "index.html"), "utf-8");

export const app = new Hono();

// Cache clients per deployment URL
const clients: Record<string, ReturnType<typeof createClient>> = {};

function getClient(deploymentUrl: string) {
  if (!clients[deploymentUrl]) {
    clients[deploymentUrl] = createClient(deploymentUrl);
  }
  return clients[deploymentUrl];
}

app.get("/", (c) => c.html(indexHtml));

app.get("/lessons", (c) => c.json({ lessons: LESSONS }));


// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

app.post("/chat", async (c) => {
  const { message, assistant_id, thread_id } = await c.req.json<{
    message: string;
    assistant_id: string;
    thread_id: string;
  }>();

  let client;
  try {
    client = getClient(getDeploymentUrl(c));
  } catch (e) {
    return c.json({ error: String(e) }, 500);
  }

  return stream(c, async (s) => {
    try {
      for await (const chunk of streamResponse(client, thread_id, assistant_id, message)) {
        await s.write(chunk);
      }
    } catch (e) {
      await s.write(`\n[error: ${String(e)}]`);
    }
  });
});


// ---------------------------------------------------------------------------
// Student
// ---------------------------------------------------------------------------

app.post("/student/start", async (c) => {
  const { first_name, last_name, goals = "", preferences = "" } = await c.req.json<{
    first_name: string;
    last_name: string;
    goals?: string;
    preferences?: string;
  }>();

  const namespace = `${first_name.toLowerCase()}_${last_name.toLowerCase()}`;

  let client;
  try {
    client = getClient(getDeploymentUrl(c));
  } catch (e) {
    return c.json({ error: String(e) }, 500);
  }

  const sessions = await createStudentSessions(client, namespace, first_name);

  const profile = { first_name, last_name, namespace, goals, preferences };
  await writeStudentProfile(client, namespace, profile);

  return c.json({ namespace, sessions });
});

app.post("/student/update", async (c) => {
  const { namespace, goals = "", preferences = "" } = await c.req.json<{
    namespace: string;
    goals?: string;
    preferences?: string;
  }>();

  let client;
  try {
    client = getClient(getDeploymentUrl(c));
  } catch (e) {
    return c.json({ error: String(e) }, 500);
  }

  const existing = (await getStudentProfile(client, namespace)) ?? {};
  const updated = { ...existing, goals, preferences };
  await writeStudentProfile(client, namespace, updated);

  return c.json({ status: "updated" });
});
