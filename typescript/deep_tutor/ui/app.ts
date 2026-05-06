/**
 * app.ts — Hono custom routes app
 *
 * Serves index.html and provides endpoints that proxy requests to the agent
 * via agentClient.ts.
 *
 * Registered as a custom route in langgraph.json via the http.app field.
 * The deployment URL is derived from the incoming request — see deployment.ts.
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { Hono } from "hono";
import { stream } from "hono/streaming";

import {
  MODULES,
  createClient,
  createStudentSessions,
  getStudentProfile,
  getStudentSessions,
  streamResponse,
  writeStudentProfile,
  writeStudentSessions,
} from "./agentClient.js";
import { getDeploymentUrl } from "./deployment.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const indexHtml = readFileSync(join(__dirname, "index.html"), "utf-8");

export const app = new Hono();

const clients: Record<string, ReturnType<typeof createClient>> = {};

function getClient(deploymentUrl: string) {
  if (!clients[deploymentUrl]) clients[deploymentUrl] = createClient(deploymentUrl);
  return clients[deploymentUrl];
}

function emailToNamespace(email: string): string {
  return email.replace(/\./g, "_");
}

// ---------------------------------------------------------------------------
// Static
// ---------------------------------------------------------------------------

app.get("/", (c) => c.html(indexHtml));
app.get("/modules", (c) => c.json({ modules: MODULES }));

// ---------------------------------------------------------------------------
// Register — new students
// ---------------------------------------------------------------------------

app.post("/register", async (c) => {
  const { first_name, last_name, email, goals = "" } = await c.req.json<{
    first_name: string;
    last_name: string;
    email: string;
    goals?: string;
  }>();

  const namespace = emailToNamespace(email);
  const client = getClient(getDeploymentUrl(c));

  await writeStudentProfile(client, namespace, {
    first_name,
    last_name,
    email,
    goals,
  });

  const studentName = `${first_name} ${last_name}`.trim();
  const sessions = await createStudentSessions(client, namespace, studentName);
  await writeStudentSessions(client, namespace, sessions);

  return c.json({ sessions, profile: { first_name, last_name } });
});

// ---------------------------------------------------------------------------
// Login — returning students
// ---------------------------------------------------------------------------

app.post("/login", async (c) => {
  const { email } = await c.req.json<{ email: string }>();

  const namespace = emailToNamespace(email);
  const client = getClient(getDeploymentUrl(c));

  const profile = await getStudentProfile(client, namespace);
  if (!profile) return c.json({ error: "user not found" }, 404);

  const sessions = await getStudentSessions(client, namespace);
  if (!sessions) return c.json({ error: "sessions not found" }, 404);

  return c.json({ sessions, profile });
});

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

app.post("/chat", async (c) => {
  const { message, assistant_id, thread_id } = await c.req.json<{
    message: string;
    assistant_id: string;
    thread_id: string;
  }>();

  const client = getClient(getDeploymentUrl(c));

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
// Resources
// ---------------------------------------------------------------------------

app.get("/resources", async (c) => {
  const client = getClient(getDeploymentUrl(c));
  const [assistants, threads] = await Promise.all([
    client.assistants.search({ limit: 100 }),
    client.threads.search({ limit: 100 }),
  ]);
  return c.json({ assistants, threads });
});
