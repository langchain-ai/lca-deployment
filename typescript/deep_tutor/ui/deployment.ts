/**
 * deployment.ts — Self-discovery of the deployment's public URL.
 *
 * When the UI app runs as a custom route inside a LangSmith deployment, it needs
 * to know its own public URL to create a LangGraph SDK client. It can't know this
 * at deploy time (chicken-and-egg), so we derive it from the incoming HTTP request.
 *
 * In cloud deployments, TLS is terminated at the load balancer, so we check
 * X-Forwarded-Proto and X-Forwarded-Host before falling back to the raw request URL.
 *
 * This is isolated here so it's easy to swap out with alternate approaches.
 */

import type { Context } from "hono";

export function getDeploymentUrl(c: Context): string {
  const host = c.req.header("x-forwarded-host") || c.req.header("host") || "";
  const scheme =
    c.req.header("x-forwarded-proto") ||
    new URL(c.req.url).protocol.replace(":", "");
  return `${scheme}://${host}`;
}
