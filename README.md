# Agent Patterns
AI agent design patterns are reusable architectures for structuring how single or multiple agents reason, use tools, coordinate tasks, and maintain reliability in production workflows

## [Executor](./Executor)  
Separates high-level task planning from step-by-step action and tool execution in AI agents. Instead of one model reasoning and acting in an ad-hoc loop at every step, a planner breaks a goal into tasks and an executor carries out the individual actions.  

## Router  
Uses choice probabilities or scores to route simple requests to smaller, faster models and complex tasksto frontier models. Dynamically delegate incoming tasks to specialized domain agents based on intent or confidence thresholds. Score candidate documents or passages to rank relevance before passing context to an agent.
 
## ReAct (Reason and Act)
Alternates chain-of-thought reasoning with external tool calls in a continuous loop until a task is finished. The LLM analyzes the goal, current state, and previous results to decide what to do next. The agent selects a tool (such as web search, a database query, code execution, or an API) and provides input arguments. The system runs the tool and feeds the returned output back into the LLM's context window.  The loop continues step by step until the model has enough information to return a final answer.

Best used when tasks are open-ended or multi-step and the exact sequence of actions depends on intermediate tool outputs.
  
## [Reinforcement learning (RL)](./RL-Agents) 
AI agents trained to make multi-step decisions and use tools by optimizing behavior through trial-and-error feedback from an environment.