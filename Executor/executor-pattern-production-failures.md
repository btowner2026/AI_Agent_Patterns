# Where Executor-Pattern Agents Fail in Production

In the executor pattern (often called plan-and-execute), one component decides *what* to do and another carries it out. A planner breaks the goal into steps, and an executor runs each step by calling tools, writing code, or taking actions. It then reports the results back so the planner can continue, replan, or finish.

```
Goal ──► Planner ──► [Step 1, Step 2, Step 3 ...]
             ▲                │
             │                ▼
             └── results ◄── Executor ──► Tools / APIs / Systems
```

The pattern makes complex tasks manageable, but it creates a gap between the plan and the real world. The executor is the part of the system that touches real systems, so it's where errors become actual side effects. Most production failures happen at one of three points: the handoff from planner to executor, the execution itself, or the report going back.

## Failure modes

### 1. The plan doesn't survive contact with reality
The planner writes steps based on assumptions: the file exists, the API returns a list, the user has an account. When step 3 finds that an assumption is false, the remaining steps no longer make sense, but the executor keeps working through them anyway. Plans made up front are only as good as what the planner knew at planning time, which is usually not much.

### 2. Executors follow plans too literally, or improvise too much
A literal executor carries out a step even when it's obviously wrong in context ("delete the temp directory" when the path turns out to be the project root). An overly autonomous executor goes the other way. It "helpfully" does extra work, chooses a different approach, or quietly skips a step it decided was unnecessary, and the planner's picture of the world stops matching reality. Tuning how much discretion the executor has is one of the hardest parts of this pattern.

### 3. Lossy handoffs from planner to executor
Steps are often short instructions ("update the customer record") without the context needed to do them correctly: which customer, which fields, the user's constraints, what "done" looks like. The planner had that context, but the executor only sees the step. The result is plausible work that's subtly off.

### 4. False success reports
Executors are optimistic. They report "done" because the tool call returned 200, the code ran without throwing, or the command exited cleanly. None of those mean the intended outcome actually happened. An API can accept a request and process it asynchronously, then fail. A script can run and write to the wrong place. A test suite can "pass" because no tests were collected. The planner trusts the report and builds on a failure.

### 5. Lossy reports from executor to planner
The reverse handoff causes problems too. Raw tool output is too large to pass back, so the executor summarizes it, and the summary leaves out the warning, the partial failure, or the edge case that should have triggered a replan. The planner makes decisions based on a cleaned-up version of events.

### 6. Unsafe retries and non-idempotent actions
When a step fails or times out, the executor retries it. That's fine for reads, but dangerous for writes: two emails sent, two charges, two tickets, two database rows. Timeouts are the worst case, because the action may have succeeded even though the executor never got a response.

### 7. Partial failure with no rollback
A five-step plan that fails at step 4 leaves the system half-changed: a record created but not linked, a branch pushed but no PR, a resource allocated but not configured. Few executor implementations track what they changed or know how to undo it, so failures leave messes that someone has to clean up by hand.

### 8. Tool-calling errors and schema drift
Executors pass wrong argument types, invented IDs, or outdated parameter names. The APIs underneath also change. A field gets renamed, pagination is added, or an error format changes, and an executor that worked last month starts failing in ways that look like model mistakes but are actually integration rot.

### 9. Replanning loops and thrashing
When execution fails, the planner replans, and the new plan often runs into the same obstacle in a slightly different way. Without loop detection, the system cycles through variations of a failed approach, burning time and money until a step limit stops it with nothing to show.

### 10. Parallel execution problems
To save time, independent steps get run in parallel. But steps the planner considered independent often aren't. They write to the same file, depend on the same rate limit, or require a particular order that the plan never stated. The results are race conditions, overwritten work, and failures that can't be reproduced.

### 11. Context overflow in the executor
Long-running executors gather tool output step after step. Eventually the context fills up and the executor loses track of the original instruction or the constraints from earlier steps, so its behavior drifts partway through a long task.

### 12. Permissions and prompt injection
The executor is the component with real access, like write permissions, credentials, and the ability to send things. It also reads the most untrusted content: web pages, file contents, API responses, emails. Instructions hidden in that content can redirect what the executor does. The planner never sees the injected text, so it can't catch it.

### 13. Long-running state and resumption
Real tasks get interrupted by timeouts, deploys, crashes, and rate-limit backoffs. If the executor doesn't save progress, a restart either starts over (repeating side effects) or resumes from a guess about where it stopped. Neither is safe.

### 14. Hard-to-assign blame
When the end result is wrong, it's hard to tell whether the planner made a bad plan, the executor carried out a good plan badly, or the tool did something unexpected. Without traces that capture the plan, each step's input and output, and the replanning decisions, debugging turns into guesswork, and fixes get applied to the wrong component.

### 15. Cost and latency stacking
Each step means at least one model call plus tool latency, and each replan adds another planning call. A task that looks like five steps can easily become thirty calls. Without budgets, the expensive edge cases dominate the bill.

## What works in practice

- **Verify outcomes, not tool responses.** After every step that changes state, check the result: read back the record, run the tests and confirm they actually ran, query the resource. Make "done" mean "confirmed."
- **Give each step a contract.** Pass the executor the step plus the context it needs, explicit success criteria, and what it's allowed and not allowed to do.
- **Let the executor stop and report.** When an assumption is broken, the executor should halt and return a structured "plan invalid because X" signal instead of pushing on. Replan from that, not from a summary.
- **Use structured results, not prose summaries.** Return status, what changed, warnings, and key data in a fixed schema so important details aren't summarized away.
- **Make writes idempotent.** Use idempotency keys, check before acting, and treat timeouts as "unknown," not "failed."
- **Track side effects and plan for rollback.** Keep a log of every change the executor makes, and define compensating actions for steps that can be reversed.
- **Checkpoint progress.** Save state after each step so a restart resumes exactly where it stopped without repeating side effects.
- **Detect loops.** Cap replans, notice when a new plan matches a failed one, and escalate to a human instead of thrashing.
- **Declare dependencies before parallelizing.** Only run steps concurrently when the plan explicitly marks them as independent and they touch no shared resources.
- **Use least privilege per step.** Give the executor only the permissions the current step needs, treat all tool output as untrusted data, and require human approval for irreversible actions.
- **Trace everything.** Log the plan, each step's input, tool calls, raw output, verification result, and every replan decision, so failures can be traced to the right component.
- **Set budgets.** Use step limits, token and cost caps, and wall-clock timeouts, with a defined fallback when they're hit.
