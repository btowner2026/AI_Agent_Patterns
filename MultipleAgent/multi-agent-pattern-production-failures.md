# Where Multi-Agent Systems Fail in Production

A multi-agent system splits work across several LLM agents, each with its own role, instructions, tools, and context. The agents then coordinate to produce one result. The common layouts are:

```
Orchestrator–worker (supervisor)        Peer-to-peer / handoff           Debate / review
                                                                         
        Orchestrator                     Agent A ──► Agent B             Proposer ──► Critic
       /     |      \                       ▲           │                    ▲          │
  Worker   Worker   Worker                  └── Agent C ◄┘                    └── revise ◄┘
       \     |      /                                                         
        Synthesizer                                                    
```

The appeal is real: specialization, parallel work, separate contexts, and smaller prompts that are easier to maintain. But a multi-agent system is a distributed system made of unreliable parts that communicate in natural language. Each agent can fail the same ways a single agent does, and the system adds new failures *between* agents: lost information, conflicting assumptions, duplicated or missing work, and nobody clearly in charge of whether the result is right. In production, most failures are coordination failures rather than failures of any one agent.

## Failure modes

### 1. Unclear or overlapping roles
Role definitions are often written loosely ("the researcher," "the analyst," "the writer"), and the boundaries between them are unclear. Two agents both think a task belongs to them, or both think it belongs to the other. Agents also step outside their role, for example a reviewer that starts rewriting, or a worker that starts re-planning. Vague role definitions are one of the most common root causes of multi-agent failures.

### 2. Duplicated work and gaps
Without a precise division of labor, parallel workers cover the same ground (three subagents all research the same obvious source) while parts of the task go untouched. The orchestrator often can't tell the difference between "covered thoroughly" and "covered three times," so the final result looks complete but has holes.

### 3. Information lost between agents
Every handoff is a natural-language message, and every message loses something. An agent passes on a summary, the next agent summarizes that summary, and by the third hop the important constraint, caveat, or number is gone. Details the user stated at the start rarely reach the agent that actually needs them.

### 4. Fragmented context and incompatible work
Each agent sees only its own piece. Subagents working in parallel make reasonable but incompatible assumptions. One uses metric units and another imperial. One writes an API expecting a list and another sends a dict. Two sections of a report contradict each other. Each piece passes its own check, and the system fails when the pieces are combined. The isolation that makes multi-agent systems scalable is the same thing that causes this.

### 5. Poor delegation by the orchestrator
The orchestrator decides how to split the work, and this is often where the system's quality is decided. Common problems: tasks broken up so they're too large or too small, instructions to subagents that are too short to act on ("research the market"), work handed to the wrong specialist, or a simple query sent to ten subagents when one would do. A bad split can't be fixed by good workers.

### 6. Agents talking in circles
Agents that talk freely can loop. Two agents keep handing a task back and forth, a critic and a proposer never converge, or agents spend turns politely agreeing and asking each other to confirm. Without a firm limit on turns or a clear end condition, these conversations go on until something forces them to stop.

### 7. Groupthink and shared blind spots
When every agent runs on the same model, they share the same blind spots. Debate and review setups often agree on the wrong answer, because the critic finds the proposer's reasoning convincing for the same reasons the proposer did. Agents also tend to defer to each other. A confident claim from one agent is accepted by the next, and the disagreement that review was supposed to provide never happens.

### 8. Guesses turning into "facts"
One agent's guess or hallucination becomes another agent's input, which it treats as established fact. By the time the claim reaches the final output, it has passed through several agents and looks confirmed, but nobody ever checked the original source. Errors grow as they pass along instead of getting caught.

### 9. Everyone assumes someone else verified it
In a single-agent system it's clear who owns correctness. In a multi-agent system, each agent assumes another one checked. Workers assume the reviewer will catch problems. The reviewer only checks what it was shown, and approves output that reads well. The synthesizer assumes the inputs were verified. The end result is that nobody actually checked whether the final output meets the original goal.

### 10. No clear decision about when the task is done
Who decides the task is finished? Often it's unclear. The orchestrator stops when workers report back, even if their reports are incomplete. A peer-to-peer system stops when one agent says "done," even if another agent's part is still unfinished. Or nobody stops, and the system runs until it hits its budget.

### 11. Conflicts over shared state
Agents that write to shared resources, such as the same file, database, document, or memory store, overwrite each other's changes, act on outdated reads, or depend on an order that was never enforced. Shared "scratchpad" memory gets cluttered with contradictory notes from different agents. These are classic concurrency bugs, made worse because the agents can't see each other working.

### 12. Injection spreading and privilege escalation
Prompt injection becomes more dangerous here because it can spread. A worker that reads a malicious web page passes the injected instructions along in its output, and the orchestrator or a more privileged agent acts on them. Delegation can also become an escalation path. A low-privilege agent asks a high-privilege agent to "please run this," and the high-privilege agent treats the request as trusted because it came from inside the system.

### 13. Cost and latency growth
Every agent re-reads its instructions and context, every handoff adds tokens, and every round of review or debate repeats work. Multi-agent systems commonly use several times the tokens of a single agent on the same task. Parallel work saves wall-clock time, but serial handoffs, review loops, and waiting on the slowest worker can make the system slower overall.

### 14. A single orchestrator becomes a bottleneck
Everything goes through the orchestrator: delegation, collecting results, combining them. Its context fills with worker reports, it becomes the slowest step, and when it makes a mistake, every worker's effort is wasted. Supervisor designs remove ambiguity but put all the risk in one agent.

### 15. Hard to debug and assign blame
A bad final output could come from bad delegation, a worker's mistake, information lost in a handoff, a missed review, or the combining step. Without tracing across agents, with linked message IDs and each agent's inputs and outputs, figuring out where it went wrong becomes guesswork. Teams end up changing the prompts of agents that weren't at fault.

### 16. Agents drifting out of sync
Agents are maintained separately. Someone updates one agent's prompt, model, or output format, and the agents downstream that depended on the old behavior break without any error. The interfaces between agents are informal natural-language agreements with no versioning or tests.

### 17. Compounding nondeterminism and hard evaluation
Each agent's randomness multiplies with the others'. The same request can lead to different delegation, different worker results, and different final answers from one run to the next. Evaluating each agent alone misses interaction failures, and evaluating only end to end makes it hard to find which component regressed.

### 18. Using multiple agents when one would do
Often the biggest failure is the decision itself. Many tasks that are split across agents would work better with one capable agent and good tools: fewer handoffs, one coherent context, and much lower cost. Multiple agents add complexity, and that complexity has to be justified by a real need, such as work that can truly run in parallel, separate contexts, or different permissions.

## What works in practice

- **Start with one agent and split only when there's a reason.** Good reasons include genuinely parallel subtasks, context that would overflow one agent, different permission boundaries, or specialized tools. Measure whether the multi-agent version actually beats a single agent.
- **Define roles precisely.** For each agent, write down what it owns, what it must not do, what it receives, what it returns, and who it hands off to. Check for overlaps and gaps the way you would with an org chart.
- **Make delegation detailed.** Orchestrator instructions to workers should include the goal, the scope, the output format, what *not* to cover (to prevent overlap), and the relevant constraints from the original request.
- **Use structured handoffs.** Pass messages between agents in a defined schema: results, sources, assumptions, confidence, open issues. Send the original user request along unchanged with every handoff instead of relying on summaries.
- **Set shared conventions up front.** Agree on units, formats, interfaces, and key decisions before parallel work starts, and give them to every worker so their outputs fit together.
- **Assign one owner for final correctness.** One component, ideally a check in code or a dedicated verifier with fresh context, checks the combined output against the original goal before anything is returned.
- **Make reviewers independent.** Give critics a different model, different instructions, or access to ground truth (tests, sources, data) so review catches real errors rather than just approving reasoning that sounds good.
- **Require sources for claims.** Facts passed between agents should carry where they came from, so later agents and verifiers can tell checked facts from guesses.
- **Limit conversations firmly.** Cap turns per exchange, require clear end conditions, and detect loops in handoffs or debates. Escalate to a human or a single decision-maker when agents can't converge.
- **Control shared state.** Prefer each agent writing to its own workspace and merging results explicitly. Where state is shared, use locks, versioning, or a single writer.
- **Enforce trust boundaries between agents.** Treat messages from other agents as untrusted data, scope each agent's permissions narrowly, and never let a request from one agent stand in for authorization of an action.
- **Trace across agents.** Use linked trace IDs so you can follow a request through every delegation, handoff, and review, with each agent's full input and output recorded.
- **Version and test the interfaces between agents.** Treat each agent's input and output format as a contract, and run integration tests when any agent's prompt or model changes.
- **Budget at the system level.** Set total token, cost, and time limits for the whole run, not just per agent, and decide in advance what to return when the budget runs out.
- **Evaluate at several levels.** Test individual agents, specific handoffs, and the full pipeline, using real traffic and especially cases where the agents' outputs conflict.
