from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph


def chat(state: MessagesState, config: RunnableConfig) -> dict:
    user = config["configurable"].get("langgraph_auth_user", {})
    user_info = ", ".join(f"{k}={v}" for k, v in user.items())
    last = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"[{user_info}] {last}")]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
graph = graph.compile()
