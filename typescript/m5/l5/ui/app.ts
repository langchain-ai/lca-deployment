/**
 * app.ts — Hono custom routes app (m5/l5 — with Supabase auth)
 *
 * Wires the deep_tutor UI to Supabase for real authentication:
 *   - /register signs up a new user with Supabase, stores their profile, returns JWT
 *   - /login exchanges email + password for a Supabase JWT
 *   - /chat and /resources accept the JWT (Authorization: Bearer <jwt>) and
 *     forward it to the LangGraph deployment so @auth.authenticate validates
 *     every call
 *
 * Registered as a custom route in langgraph.json via the http.app field.
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { Hono } from "hono";
import { stream } from "hono/streaming";
import type { Context } from "hono";

import {
  MODULES,
  createClient,
  createStudentSessions,
  streamResponse,
} from "./agentClient.js";
import { getDeploymentUrl } from "./deployment.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const indexHtml = readFileSync(join(__dirname, "index.html"), "utf-8");

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY!;

export const app = new Hono();

function emailToNamespace(email: string): string {
  return email.replace(/\./g, "_");
}

/** Pull the bearer token out of an Authorization header, or throw. */
function extractJwt(c: Context): string {
  const authorization = c.req.header("Authorization");
  if (!authorization) {
    throw new Error("Missing Authorization header");
  }
  const [scheme, token] = authorization.split(" ");
  if (scheme?.toLowerCase() !== "bearer" || !token) {
    throw new Error("Invalid Authorization header");
  }
  return token;
}

// ---------------------------------------------------------------------------
// Static
// ---------------------------------------------------------------------------

app.get("/", (c) => c.html(indexHtml));
app.get("/modules", (c) => c.json({ modules: MODULES }));
app.get("/healthz", (c) => c.json({ status: "ok" }));

// ---------------------------------------------------------------------------
// Register — new students
// ---------------------------------------------------------------------------

app.post("/register", async (c) => {
  const { first_name, last_name, email, password, goals = "" } = await c.req.json<{
    first_name: string;
    last_name: string;
    email: string;
    password: string;
    goals?: string;
  }>();

  // 1. Sign up with Supabase, receive a JWT.
  const r = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
    method: "POST",
    headers: { apiKey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    return c.json({ error: await r.text() }, r.status as 400 | 401 | 403 | 404 | 500);
  }
  const { access_token: jwt } = await r.json() as { access_token: string };

  // 2. Use that JWT to call the deployment — every SDK call now passes
  //    through @auth.authenticate on the way in.
  const client = createClient(getDeploymentUrl(c), jwt);
  const namespace = emailToNamespace(email);

  await client.store.putItem([namespace], "profile", {
    first_name,
    last_name,
    email,
    goals,
  });

  const studentName = `${first_name} ${last_name}`.trim();
  const sessions = await createStudentSessions(client, namespace, studentName);
  await client.store.putItem([namespace], "sessions", { sessions });

  return c.json({ jwt, sessions, profile: { first_name, last_name } });
});

// ---------------------------------------------------------------------------
// Login — returning students
// ---------------------------------------------------------------------------

app.post("/login", async (c) => {
  const { email, password } = await c.req.json<{ email: string; password: string }>();

  // 1. Ask Supabase for a JWT.
  const r = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apiKey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    return c.json({ error: await r.text() }, r.status as 400 | 401 | 403 | 404 | 500);
  }
  const { access_token: jwt } = await r.json() as { access_token: string };

  // 2. Read the existing profile + sessions using the JWT.
  const client = createClient(getDeploymentUrl(c), jwt);
  const namespace = emailToNamespace(email);

  const profileItem = await client.store.getItem([namespace], "profile");
  if (!profileItem) return c.json({ error: "user not found" }, 404);

  const sessionsItem = await client.store.getItem([namespace], "sessions");
  if (!sessionsItem) return c.json({ error: "sessions not found" }, 404);

  return c.json({
    jwt,
    sessions: (sessionsItem.value as { sessions: unknown }).sessions,
    profile: profileItem.value,
  });
});

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

app.post("/chat", async (c) => {
  let jwt: string;
  try {
    jwt = extractJwt(c);
  } catch (e) {
    return c.json({ error: String(e) }, 401);
  }

  const { message, assistant_id, thread_id } = await c.req.json<{
    message: string;
    assistant_id: string;
    thread_id: string;
  }>();

  const client = createClient(getDeploymentUrl(c), jwt);

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
// Resources — threads and assistants for the calling user
// ---------------------------------------------------------------------------

app.get("/resources", async (c) => {
  let jwt: string;
  try {
    jwt = extractJwt(c);
  } catch (e) {
    return c.json({ error: String(e) }, 401);
  }

  const client = createClient(getDeploymentUrl(c), jwt);
  const [assistants, threads] = await Promise.all([
    client.assistants.search({ limit: 100 }),
    client.threads.search({ limit: 100 }),
  ]);
  return c.json({ assistants, threads });
});
