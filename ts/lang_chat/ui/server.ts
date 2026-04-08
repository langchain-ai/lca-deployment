/**
 * server.ts — Express UI server
 *
 * Serves index.html and provides endpoints that proxy requests to the LangGraph
 * deployment via agent_client.ts.
 *
 * Run with:
 *   npx tsx ui/server.ts
 */

import path from "node:path";
import { fileURLToPath } from "node:url";

import express, { Request, Response } from "express";
import "dotenv/config";

import {
  LESSONS,
  createClient,
  createStudentSessions,
  getStudentProfile,
  streamResponse,
  writeStudentProfile,
} from "./agent_client.js";

const app = express();
app.use(express.json());

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Cache clients per deployment URL
const clients: Record<string, ReturnType<typeof createClient>> = {};

function getClient(deploymentUrl: string) {
  if (!clients[deploymentUrl]) {
    clients[deploymentUrl] = createClient(deploymentUrl);
  }
  return clients[deploymentUrl];
}

app.get("/", (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

app.get("/lessons", (_req: Request, res: Response) => {
  res.json({ lessons: LESSONS });
});


// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

app.post("/chat", async (req: Request, res: Response) => {
  const { message, deployment_url, assistant_id, thread_id } = req.body as {
    message: string;
    deployment_url: string;
    assistant_id: string;
    thread_id: string;
  };

  let client;
  try {
    client = getClient(deployment_url);
  } catch (e) {
    res.status(500).json({ error: String(e) });
    return;
  }

  res.setHeader("Content-Type", "text/plain");
  res.setHeader("Transfer-Encoding", "chunked");

  try {
    for await (const chunk of streamResponse(client, thread_id, assistant_id, message)) {
      res.write(chunk);
    }
  } catch (e) {
    res.write(`\n[error: ${String(e)}]`);
  }
  res.end();
});


// ---------------------------------------------------------------------------
// Student
// ---------------------------------------------------------------------------

app.post("/student/start", async (req: Request, res: Response) => {
  const { deployment_url, first_name, last_name, goals = "", preferences = "" } = req.body as {
    deployment_url: string;
    first_name: string;
    last_name: string;
    goals?: string;
    preferences?: string;
  };

  const namespace = `${first_name.toLowerCase()}_${last_name.toLowerCase()}`;

  let client;
  try {
    client = getClient(deployment_url);
  } catch (e) {
    res.status(500).json({ error: String(e) });
    return;
  }

  const sessions = await createStudentSessions(client, namespace, first_name);

  const profile = { first_name, last_name, namespace, goals, preferences };
  await writeStudentProfile(client, namespace, profile);

  res.json({ namespace, sessions });
});

app.post("/student/update", async (req: Request, res: Response) => {
  const { deployment_url, namespace, goals = "", preferences = "" } = req.body as {
    deployment_url: string;
    namespace: string;
    goals?: string;
    preferences?: string;
  };

  let client;
  try {
    client = getClient(deployment_url);
  } catch (e) {
    res.status(500).json({ error: String(e) });
    return;
  }

  const existing = (await getStudentProfile(client, namespace)) ?? {};
  const updated = { ...existing, goals, preferences };
  await writeStudentProfile(client, namespace, updated);

  res.json({ status: "updated" });
});


const PORT = process.env.PORT ?? 3000;
app.listen(PORT, () => {
  console.log(`UI server running at http://localhost:${PORT}`);
});
