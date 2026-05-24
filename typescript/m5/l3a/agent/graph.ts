import { END, START, MessagesAnnotation, StateGraph, type LangGraphRunnableConfig } from "@langchain/langgraph";
import { AIMessage } from "@langchain/core/messages";

function chat(
  state: typeof MessagesAnnotation.State,
  config: LangGraphRunnableConfig,
): typeof MessagesAnnotation.Update {
  const user = (config.configurable?.langgraph_auth_user ?? {}) as Record<string, unknown>;
  const identity = (user.identity as string) ?? "unknown";
  const last = state.messages[state.messages.length - 1];
  const content = typeof last.content === "string" ? last.content : "";
  return { messages: [new AIMessage(`[${identity}] ${content}`)] };
}

export const graph = new StateGraph(MessagesAnnotation)
  .addNode("chat", chat)
  .addEdge(START, "chat")
  .addEdge("chat", END)
  .compile();
