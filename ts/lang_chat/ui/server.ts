/**
 * server.ts — Express UI server
 *
 * Serves index.html. The HTML connects directly to LangGraph Cloud from the browser.
 *
 * Run with:
 *   pnpm tsx ui/server.ts
 */

import path from "node:path";
import { fileURLToPath } from "node:url";

import express, { Request, Response } from "express";

const app = express();
const __dirname = path.dirname(fileURLToPath(import.meta.url));

app.get("*", (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

const PORT = process.env.PORT ?? 3000;
app.listen(PORT, () => {
  console.log(`UI server running at http://localhost:${PORT}`);
});
