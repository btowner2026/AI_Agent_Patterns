from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt


# 1. Define a sensitive tool
@tool
def send_email(recipient: str, body: str) -> str:
  """Send an email to a recipient."""
  return f"Email sent to {recipient}: '{body}'"


# 2. Define graph state
class State(TypedDict):
  messages: Annotated[list[AnyMessage], add_messages]


llm = ChatOpenAI(model="gpt-4o-mini").bind_tools([send_email])


def call_model(state: State):
  return {"messages": [llm.invoke(state["messages"])]}


# 3. Node that pauses for human review before executing tools
def human_approval_node(state: State):
  last_message = state["messages"][-1]
  tool_call = last_message.tool_calls[0]

  # Pause execution and surface tool details to the caller
  decision = interrupt({
      "action": tool_call["name"],
      "args": tool_call["args"],
      "prompt": "Approve this action? (yes/no)",
  })

  if decision.lower() in {"y", "yes"}:
    result = send_email.invoke(tool_call["args"])
    return {
        "messages": [ToolMessage(tool_call_id=tool_call["id"], content=result)]
    }
  else:
    return {
        "messages": [
            ToolMessage(
                tool_call_id=tool_call["id"],
                content="Action rejected by human reviewer.",
            )
        ]
    }


def route_after_model(state: State):
  last_message = state["messages"][-1]
  if last_message.tool_calls:
    return "human_approval"
  return END


# 4. Build and compile the graph with a checkpointer (required for interrupt)
builder = StateGraph(State)
builder.add_node("agent", call_model)
builder.add_node("human_approval", human_approval_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_after_model)
builder.add_edge("human_approval", "agent")

graph = builder.compile(checkpointer=MemorySaver())

# 5. Run the workflow
config = {"configurable": {"thread_id": "session-1"}}
initial_input = {
    "messages": [
        HumanMessage(
            content="Email alice@example.com saying the report is ready."
        )
    ]
}

# Step A: Runs until it hits `interrupt()`
for event in graph.stream(initial_input, config):
  if "__interrupt__" in event:
    interrupt_info = event["__interrupt__"][0].value
    print(f"\n[PAUSED] Pending Action: {interrupt_info}")

# Step B: Collect human input and resume with Command(resume=...)
user_input = input("Approve? (yes/no): ")
for event in graph.stream(Command(resume=user_input), config):
  if "agent" in event:
    print("\n[FINAL RESPONSE]:", event["agent"]["messages"][-1].content)