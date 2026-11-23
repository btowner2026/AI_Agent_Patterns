# Where ReAct-Pattern Agents Fail in Production

ReAct (Reason + Act) is the simplest and most widely used agent loop. The model reasons about what to do next, takes one action (usually a tool call), reads the result, and repeats until it decides it's finished. There's no separate planner. The plan is rebuilt one step at a time as the agent goes.

```
          ┌──────────────────────────────────────┐
          ▼                                      │
Goal ──► Thought ──► Action (tool call) ──► Observation
          │
          └──► Final Answer (when the model decides it's done)
```

Most modern agents are ReAct loops underneath, whether they print the "Thought / Action / Observation" format or use native tool calling. That flexibility is the pattern's strength. Its weakness is that nothing outside the model is in charge. The model decides what to do, judges what happened, and decides when to stop, all inside one growing context. Most production failures come from that: no global plan, no outside check, and a context that keeps growing.

## Failure modes

### 1. Loops and repeated actions
The agent runs the same search, reads the same file, or calls the same failing API over and over, each time with a slightly different "thought" justifying it. It has no memory of having already tried that beyond what's in the context, and once the context is long, it doesn't reliably notice the repetition. Without loop detection, the run ends only when it hits the iteration cap.

### 2. Giving up or finishing too early
The model decides it's done when the result looks plausible, not when the task is actually complete. Common signs: answering from the first search result, declaring a bug fixed without running anything, or returning a partial answer as if it were complete. The stopping decision is the model's own judgment, so it inherits all of the model's optimism.

### 3. Fabricated observations
In text-based ReAct, the model sometimes writes the "Observation" itself instead of waiting for the tool, and then reasons from results it made up. Native tool calling mostly prevents this, but a quieter version persists. The model "remembers" what a tool returned earlier in a different way than it actually did, or fills in fields the tool never returned.

### 4. Parsing and format failures
Text-based ReAct depends on the model producing exact syntax: the right action name, valid JSON arguments, correct delimiters. Under long contexts or unusual inputs, the format slips. Arguments get truncated, two actions get emitted at once, or prose gets mixed into JSON. Each slip either crashes the loop or gets fed back as an error that sends the agent off course.

### 5. Short-sighted, greedy behavior
Each step optimizes for what looks best right now. There's no plan to keep the agent on track, so it chases side paths, fixates on the first approach it tried, or solves a nearby easier problem instead of the one asked. This gets worse as tasks get longer. ReAct does well on 5-step tasks and noticeably worse on 50-step ones.

### 6. Losing the goal as the context grows
Every thought, action, and observation gets appended to the context. On long runs, the original instructions and constraints end up buried under pages of tool output, and the model gradually loses track of them. It forgets a constraint from the first message, reformats output it was told not to touch, or changes the goal altogether.

### 7. Observation overload
One tool call returns a 2,000-line file, a giant JSON payload, or a full web page. The important detail is buried, the context fills up, and later steps get worse. If the output is truncated to fit, the agent may not know it's looking at partial data and will draw conclusions from an incomplete view.

### 8. Trusting observations too much or too little
Sometimes the agent takes whatever a tool returns as truth, including stale cache entries, wrong search results, and error pages that look like content. Other times it does the opposite: it ignores a tool result that contradicts what it already believed and answers from its prior knowledge anyway. Both happen, sometimes in the same run.

### 9. Thoughts that don't match actions
The stated reasoning and the action taken don't line up. The thought says "I should check the config first" and the action edits the code. Or the reasoning is written after the fact to justify an action already decided. That makes the visible "thoughts" unreliable for debugging, because they may not reflect what actually drove the behavior.

### 10. Tool selection errors with large toolsets
ReAct gives the model all of its tools at every step. With a handful of tools, choosing works well. With dozens of tools, many of them with overlapping descriptions, the model picks the wrong tool, misses the right one, or makes up arguments for a tool it mixed up with another.

### 11. Poor error recovery
Tool errors come back as observations, and the model has to figure out what they mean. It often reads a permission error as "try again," a rate limit as "this approach doesn't work," or a vague 500 as a reason to give up on the whole task. The error message itself, if it's unclear, can steer the next several steps wrong.

### 12. Prompt injection through observations
Every observation goes straight into the model's context. A web page, file, email, or API response containing instructions ("ignore previous instructions and...") is read by the same model that decides the next action, with no separate component in between to filter it. ReAct agents that both read untrusted content and have write-capable tools are the most exposed.

### 13. Side effects in the middle of the loop
Actions run as soon as the model chooses them, with no review step. If the agent is partway through a reasoning mistake when it calls a write tool, the side effect has already happened by the time it realizes. Retries on unclear outcomes can repeat non-idempotent actions, and an interrupted run leaves the system half-changed with no record of what was done.

### 14. Slow, sequential execution
The classic loop runs one action per step and waits for each result before thinking again. Tasks that could run in parallel, like reading five files or checking three APIs, happen one after another, each with a full model call in between. Latency grows with task length, and users notice.

### 15. Rising cost on long runs
The whole history is sent again on every step, so per-step token cost grows as the run goes on, and total cost grows faster than the step count. A 40-step run costs far more than 4 times a 10-step run. The long-tail tasks that loop or wander end up dominating the bill.

### 16. Hitting the iteration cap with nothing to show
Teams set a maximum step count to prevent runaway loops, which is correct. But when the cap is reached, many implementations simply stop and return nothing or an error. All the partial progress and useful findings from the run are lost.

### 17. Nondeterminism and hard evaluation
The same input can produce very different paths through the loop. One run takes 6 steps and succeeds, the next takes 25 and fails. Checking only the final answer misses expensive or risky paths that happened to end well. Checking the steps themselves is hard because many different paths can all be valid.

## What works in practice

- **Use native tool calling, not text parsing.** Structured tool-call APIs largely remove format errors and fabricated observations. Validate arguments against a schema before running anything.
- **Detect repetition.** Track recent actions and arguments, flag exact or near-exact repeats, and inject a "you already tried this, and here's what happened" note or force a different approach.
- **Make "done" checkable.** Require a verification step before the final answer: run the tests, re-read the changed record, confirm the output matches the requested format. Where possible, check completion in code rather than leaving it to the model.
- **Add light planning.** Have the agent write a short plan or checklist first and refer back to it, or re-insert the goal and key constraints into the context every N steps. This brings back the overall direction that pure ReAct lacks.
- **Manage the context on purpose.** Truncate or summarize old observations, keep the original instructions pinned, and compress completed sub-tasks into short records of results.
- **Shape tool outputs.** Return concise, structured results with pagination and search instead of raw dumps. Always tell the model when output was truncated.
- **Write clear errors for the model.** Tool errors should say what went wrong and what to do next ("rate limited, retry after 30s"; "permission denied, this tool can't access X").
- **Keep the toolset small and clearly described.** Show only the tools relevant to the current task, and make sure their descriptions don't overlap.
- **Gate side effects.** Separate read tools from write tools, require confirmation or human approval for irreversible actions, use idempotency keys, and log every change.
- **Treat observations as data, not instructions.** Mark untrusted content clearly, limit what write tools can do while untrusted content is in context, and keep credentials scoped narrowly.
- **Allow parallel tool calls** for independent reads to cut latency.
- **Set budgets and degrade gracefully.** Use step, token, and time limits. When a limit is hit, have the agent summarize what it found and what's left instead of returning nothing.
- **Trace and evaluate paths.** Log every thought, action, and observation. Evaluate on final correctness and on path quality (step count, cost, risky actions), using test cases built from real traffic and real failures.
- **Know when to move on from plain ReAct.** For long, multi-stage, or high-stakes work, pair ReAct with a planner-executor structure, outside verifiers, or checkpoints, and keep plain ReAct for short, exploratory tasks where it works best.
