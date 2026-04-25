from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph


def chat(state: MessagesState, config: RunnableConfig) -> dict:
    user = config["configurable"].get("langgraph_auth_user", {})
    identity = user.get("identity", "unknown")
    last = state["messages"][-1].content
    return {"messages": [AIMessage(content=f"[{identity}] {last}")]}


graph = StateGraph(MessagesState)
graph.add_node("chat", chat)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)
graph = graph.compile()
