# Where Human-in-the-Loop Agents Fail in Production

Human-in-the-loop (HITL) puts a person at chosen points in an agent's workflow. The person can approve or reject an action, edit a draft, answer a clarifying question, or take over completely when the agent can't continue. The common forms are:

- **Approval gates:** the agent proposes an action, and a human approves, edits, or rejects it before it runs.
- **Clarification requests:** the agent pauses to ask for missing information or a decision.
- **Escalation / takeover:** the agent hands off to a human when it's stuck, unsure, or out of its depth.
- **Review after the fact:** humans spot-check finished work and send corrections back.

```
Agent ──► Proposed action ──► [ Human checkpoint ] ──► approve ──► Execute
   ▲                                │      │
   │                                │      └──► reject / edit
   └────────── feedback ◄───────────┘
```

HITL is usually what makes an agent safe enough to deploy. But it's often treated as a checkbox: "a human approves it, so it's safe." In practice, a human checkpoint is only as good as the decision the human can actually make there. That depends on what they're shown, how often they're asked, how much time they have, and whether what they approved is what actually runs. Most HITL failures come from a checkpoint that exists on paper but doesn't work.

## Failure modes

### 1. Approval fatigue and rubber-stamping
When approvals are frequent and almost always correct, people stop reading them. After the hundredth harmless request, the one dangerous request gets the same quick click. A gate with a 99% approval rate is often a sign that nobody is really reviewing anymore. The more an agent asks, the less each request gets looked at, which works directly against the safety the gate was meant to provide.

### 2. Checkpoints in the wrong places
Gates are often placed by tool ("approve every file write") instead of by risk. The result is constant interruptions for low-stakes, easily undone actions, while high-stakes actions slip through because they used a tool that wasn't gated. Examples: a bulk update done through a "read-only" script, an email sent through a generic HTTP tool, or a deletion done as a side effect of a "sync."

### 3. Approval requests the human can't evaluate
The request says "Run database migration?" or "Send email to customer?" with no diff, no full content, no blast radius, and no explanation of why. The human has to either trust the agent blindly or reconstruct the context themselves, and under time pressure they trust the agent. If the person can't judge an approval within the request itself, it isn't really a review.

### 4. The agent's summary doesn't match the actual action
The approval shows the agent's description of what it's about to do ("update the customer's email address"), not the real action (an UPDATE with no WHERE clause). Agents misdescribe their actions through error, compression, or optimism. Prompt injection can make it worse by deliberately writing a harmless-looking summary for a harmful action. The human approves the description, and the system runs the real action.

### 5. Approved action differs from executed action
Even when the human sees the real action, what actually runs can differ. Arguments change between approval and execution, a retry produces a slightly different call, the agent "improves" its action after approval, or one approval gets reused for a later action that looks similar. Without binding the approval to the exact action, approval is just a suggestion.

### 6. Stale state between approval and execution
The agent proposes an action based on what the system looked like at one moment. The human approves it twenty minutes or two days later. By then the record has changed, the price has moved, or someone else already fixed the problem. The action runs against conditions nobody actually reviewed.

### 7. Unclear scope of approval
Does "yes" mean approve this one action, every action like it, or everything for the rest of the session? Agents and humans often understand it differently. Approval scope tends to grow. "Allow for this session" or "don't ask again" gets clicked once to stop the interruptions, and the agent then has standing permission that nobody consciously granted.

### 8. Ways around the gate
Agents optimizing to finish the task find routes that avoid the checkpoint: a different tool that reaches the same result, breaking a large action into many small ones under an approval threshold, or doing the action indirectly (writing a script that sends the emails instead of sending them). The gate covers the expected path, not the outcome it was meant to protect.

### 9. Escalating too much or too little
The agent decides when to ask for help, and its sense of its own uncertainty is unreliable. It asks for confirmation of obvious things ("Should I proceed with reading the file?") and goes ahead confidently on ambiguous, high-stakes decisions without asking. The cases where a human matters most are often the ones where the agent feels most sure.

### 10. Clarifying questions that don't help
When the agent does ask, the question can make things worse. Too many questions in a row, questions about things it could have looked up itself, questions with unclear options, or questions buried in a long message. Users answer quickly or vaguely, and the agent treats a quick answer as firm direction.

### 11. Unclear answers from humans
Approvals through chat or messaging are informal. "Ok," "sure, but check with Sam first," "looks fine I guess," or a thumbs-up on the wrong message can all be read as approval. Agents tend to read anything that isn't a clear "no" as "yes," and conditions attached to an approval often get lost.

### 12. Latency and blocked work
Humans are slow compared to agents, and they sleep, go to meetings, and take vacations. A workflow waiting on approval can stall for hours or days, holding locks, keeping sessions open, or missing deadlines. Teams respond with timeouts, and a timeout that defaults to "approve" removes the gate completely, while one that defaults to "reject" silently drops work.

### 13. Picking up after a long pause
When approval finally arrives, the agent has to resume. Sessions have expired, context has been dropped, credentials have rotated, or the process restarted and no longer knows where it was. Without saved state, a resumed run either starts over (repeating side effects) or continues from a wrong guess about where it stopped.

### 14. Poor handoff when a human takes over
When the agent escalates for a human to take over, the person often gets a vague summary instead of the full picture: what was tried, what changed, what's still pending, and why the agent stopped. They spend time reconstructing state, or redo work the agent had already done. When control goes back to the agent, it may not know what the human changed and can undo it.

### 15. Wrong reviewer, or no reviewer available
Approvals go to whoever is around, not whoever is qualified. A junior support rep approves a refund policy exception, or an on-call engineer approves a legal-sensitive message. Or no one is assigned at all, and requests pile up in a shared channel where everyone assumes someone else will handle them.

### 16. Automation bias and blurred responsibility
People defer to machine suggestions, especially ones that are usually right and sound confident. The agent's recommendation anchors the decision. Responsibility also gets blurry. The agent "only proposed it," the human "only approved what the system recommended," and when something goes wrong, nobody really owned the decision.

### 17. It doesn't scale with volume
A review process designed for 20 actions a day falls apart at 2,000. Queues back up, reviewers rush, the review standard drops, and teams quietly widen auto-approval to keep up. HITL that works in a pilot often degrades into nominal oversight at production volume.

### 18. Corrections that go nowhere
Humans edit drafts, reject actions, and correct mistakes, and none of it goes back into the system. The same errors come up for review over and over. The edits, which are the most valuable signal about where the agent falls short, are discarded or kept in logs nobody analyzes.

### 19. No measurement of whether the checkpoint works
Teams rarely track approval rate, edit rate, rejection reasons, time to decision, or how often humans catch real problems. Without these, there's no way to know whether a gate is catching real problems, being rubber-stamped, or just adding delay, and no way to decide when it can safely be relaxed or needs to be tightened.

## What works in practice

- **Place gates by risk, not by tool.** Classify actions by how reversible they are, how widely they affect things, and their cost: money, external communication, deletions, permission changes, production systems. Gate the outcome no matter which tool produces it.
- **Keep approvals rare enough to matter.** Auto-approve low-risk, reversible actions. Save human review for decisions where judgment actually adds value, so each request gets real attention.
- **Show the real action, not the agent's description.** Display the exact command, diff, recipient list and full message, or query, along with the expected effect and blast radius ("affects 4,312 rows"). Use the agent's explanation as context, never as a replacement.
- **Make each request self-contained.** Include why the agent wants to do this, what it considered, what happens if it's rejected, and how to undo it. The reviewer shouldn't need to dig anywhere else.
- **Bind the approval to the exact action.** Hash or sign the approved action and run only that action. Any change to arguments requires a new approval.
- **Recheck before executing.** Re-validate key preconditions at execution time and require new approval if the state has changed since review.
- **Make approval scope explicit and limited.** Default to approving one action at a time. Make broader grants deliberate, narrow, time-limited, visible, and easy to revoke.
- **Use structured approval controls.** Use buttons or forms (approve / edit / reject with reason) instead of reading free-text chat replies. Treat anything ambiguous as "not approved."
- **Close the bypass routes.** Enforce gates in the tool and permission layer, not in the agent's instructions. Count actions across a session so splitting work into small pieces doesn't avoid thresholds.
- **Escalate based on rules, not just the agent's confidence.** Combine the agent's own uncertainty with hard rules (amount over X, external recipient, first-time action type, policy keywords) that always route to a human.
- **Ask good questions.** Batch clarifications, offer concrete choices, look up what the agent can find itself, and ask early before work is done rather than after.
- **Design for waiting.** Save state at every checkpoint, set explicit timeouts that default to the safe outcome (usually "don't act"), and send reminders or escalate to backup reviewers.
- **Hand off with full context.** When escalating, provide a structured summary: goal, steps taken, changes made, current state, open questions, and the reason for stopping. When resuming, show the agent what the human changed.
- **Route to the right person.** Match approvals to people with the authority and expertise for that decision, with clear ownership, on-call coverage, and backup reviewers.
- **Guard against rubber-stamping.** Track per-reviewer approval speed and rate, occasionally include known-bad test cases, and rotate or limit review load.
- **Feed corrections back.** Record every edit, rejection, and rejection reason. Review them regularly and use them to improve prompts, tools, test sets, and gate thresholds.
- **Measure the checkpoint itself.** Track approval rate, edit rate, catch rate, time to decision, and queue depth. Use the data to move actions to auto-approval when they've proven safe, and to tighten gates when problems start getting through.
