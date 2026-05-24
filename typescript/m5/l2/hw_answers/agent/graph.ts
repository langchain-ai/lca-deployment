import { END, START, MessagesAnnotation, StateGraph, type LangGraphRunnableConfig } from "@langchain/langgraph";
import { AIMessage } from "@langchain/core/messages";

// Fields the TS SDK injects automatically — skip them so the output matches
// what the auth handler explicitly returned (identity, name, role).
const SKIP_KEYS = new Set(["permissions", "is_authenticated", "display_name"]);

function chat(
  state: typeof MessagesAnnotation.State,
  config: LangGraphRunnableConfig,
): typeof MessagesAnnotation.Update {
  const user = (config.configurable?.langgraph_auth_user ?? {}) as Record<string, unknown>;
  const userInfo = Object.entries(user)
    .filter(([k]) => !SKIP_KEYS.has(k))
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
  const last = state.messages[state.messages.length - 1];
  const content = typeof last.content === "string" ? last.content : "";
  return { messages: [new AIMessage(`[${userInfo}] ${content}`)] };
}

export const graph = new StateGraph(MessagesAnnotation)
  .addNode("chat", chat)
  .addEdge(START, "chat")
  .addEdge("chat", END)
  .compile();
