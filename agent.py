from blinkit_tool_original import run_blinkit
from tool_original import run_zepto
from blinkit_tool_original import set_blinkit_otp
from tool_original import set_zepto_otp
from langchain_core.tools import tool
import json
import requests
import time
import random
from typing import Dict, Any, List, Optional, Tuple, Annotated
from pydantic import BaseModel, Field
import os
import threading
import concurrent.futures

from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()

from typing import List

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

tools = [run_zepto, run_blinkit, set_zepto_otp, set_blinkit_otp]

from getpass import getpass

if not os.environ.get("GOOGLE_API_KEY"):
  os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")

from langchain.chat_models import init_chat_model

llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

# Enhanced system prompt to encourage parallel tool calls
system_prompt = """You are a grocery comparison shopping assistant. When a user asks you to compare prices or search for products, you should ALWAYS call BOTH run_blinkit AND run_zepto tools simultaneously to provide a comprehensive comparison.

Key instructions:
1. For any product search request, call BOTH run_blinkit and run_zepto tools in the same response
2. Use the same phone number and search items for both tools
3. For run_blinkit, include the address parameter
4. For run_zepto, include the phone number and search items and address parameter
5. Always aim to provide parallel execution for better user experience

OTP HANDLING - CRITICAL:
6. After calling the search tools (run_blinkit/run_zepto), ALWAYS check the tool responses
7. If ANY tool response mentions "OTP", "verification", "code", or similar authentication terms, IMMEDIATELY ask the user:
   "I've initiated the search on both platforms. Please provide the OTP codes you receive:
   - For Zepto OTP, I'll use set_zepto_otp
   - For Blinkit OTP, I'll use set_blinkit_otp
   Please share the OTP codes when you receive them."

8. When user provides OTPs (in any format), immediately call the appropriate set_otp tools:
   - set_zepto_otp(otp) for Zepto
   - set_blinkit_otp(otp) for Blinkit

9. Be proactive about OTP requests - don't wait for explicit user mention of OTPs

Example flow:
User: "Search for milk"
You: Call run_blinkit + run_zepto
Tool responses: [check for OTP mentions]
You: "Search initiated! Please provide OTP codes for verification..."
User: "Zepto: 1234, Blinkit: 5678"
You: Call set_zepto_otp(1234) + set_blinkit_otp(5678)
"""

llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    messages = state["messages"]
    # Add system prompt if this is the first message
    if len(messages) == 1 and messages[0].get("role") == "user":
        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message] + messages
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

graph_builder.add_node("chatbot", chatbot)

import json
from langchain_core.messages import ToolMessage

class ParallelToolNode:
    """A node that runs tools in parallel for better performance."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        
        outputs = []
        tool_calls = message.tool_calls
        
        if not tool_calls:
            return {"messages": outputs}
        
        # Execute tools in parallel using ThreadPoolExecutor
        def execute_tool(tool_call):
            try:
                tool_result = self.tools_by_name[tool_call["name"]].invoke(
                    tool_call["args"]
                )
                return ToolMessage(
                    content=json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            except Exception as e:
                return ToolMessage(
                    content=f"Error executing {tool_call['name']}: {str(e)}",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
            # Submit all tool calls for parallel execution
            future_to_tool = {executor.submit(execute_tool, tool_call): tool_call for tool_call in tool_calls}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_tool):
                tool_result = future.result()
                outputs.append(tool_result)
        
        return {"messages": outputs}

tool_node = ParallelToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "END" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "tools", END: END},
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile()
graph = graph_builder.compile(checkpointer=memory)

def _safe_preview(text: str) -> str:
    """Redact likely phone numbers from console output (basic)."""
    import re
    return re.sub(r"(?<!\d)(\d{3})\d{3}(\d{4})(?!\d)", r"\1***\2", text)

# Enhanced system context for better tool calling
def stream_graph_updates(user_input: str, system_context: str | None = None):
    initial_messages: list[tuple[str, str]] = []
    
    # Add enhanced system context for comparison shopping
    enhanced_context = system_prompt
    if system_context:
        enhanced_context += f"\n\nAdditional context: {system_context}"
    
    initial_messages.append(("system", enhanced_context))
    initial_messages.append(("user", user_input))

    for event in graph.stream({"messages": initial_messages}, stream_mode="values"):
        for value in event.values():
        # value is a partial state update like {"messages": [<Message>]}
            msg = value["messages"][-1]
            role = getattr(msg, "type", getattr(msg, "role", ""))
            if role == "ai":
                print("Assistant:", _safe_preview(msg.content))
            elif role == "tool":
                # show which tool produced output
                name = getattr(msg, "name", "tool")
                content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                print(f"[{name}] ->", _safe_preview(content))

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    user_input = "run blinkit tool with phone number is 9334727093 and address is 560102 and search items ['AMUL toned MIlk 500ml']"

    # The config is the **second positional argument** to stream() or invoke()!
    events = graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
        stream_mode="values",
    )
    for event in events:
        event["messages"][-1].pretty_print()