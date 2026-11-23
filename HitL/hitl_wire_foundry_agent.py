# # 1. Define a sensitive tool - Decorate sensitive tools to trigger approval requests
@tool(approval_mode="always_require")
def send_wire_transfer(amount: float, recipient: str) -> str:
    return f"Successfully transferred ${amount} to {recipient}."

# Check for pending approvals during agent execution and pass the decision back
if response.user_input_requests:
    approval_messages = [req.create_response(approved=user_decision) for req in response.user_input_requests]
    final_response = await agent.run(approval_messages, thread=thread)