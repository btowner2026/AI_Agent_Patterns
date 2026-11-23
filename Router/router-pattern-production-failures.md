# Where Router-Pattern Agents Fail in Production

With a router pattern, the most common failure is not the specialist agents themselves. It's the routing decision and the handoffs around it. A router is a single point of failure: once a request goes down the wrong branch, every later step can run perfectly and still produce the wrong result.

## Failure modes

### 1. Misrouting on ambiguous or multi-intent requests
Routers are usually built around clean, single-intent categories, but real users write things like "cancel my order and tell me why I was charged twice." That's two intents, so the router picks one and the other is quietly dropped. A borderline query ("Can I change my plan?" could be billing or account settings) gets routed by whatever phrasing happens to tip the classifier. Most routers can only pick one route, so there's no way to split or combine.

### 2. Overlapping route definitions
Routes often start out distinct and then blur together as more are added. When two route descriptions overlap ("billing questions" vs. "subscription management"), the router's choices become close to random between them, and the behavior changes with small prompt edits. This is the most common slow-burn failure. Accuracy looks fine at launch with 4 routes and gets worse at 15.

### 3. The catch-all route turns into a dumping ground
The "general" or "other" route ends up handling everything the router is unsure about. It's usually the least specialized and least tested path, yet it often carries a large share of traffic. Teams tend to look only at accuracy on the named routes and miss this.

### 4. No recovery after a wrong route
In most implementations, the specialist that receives a request has no way to say "this isn't mine." It tries its best with the wrong tools and the wrong instructions, and returns a confident but irrelevant answer. Without a reject-and-reroute path, a misroute is a dead end.

### 5. Context lost in the handoff
The router sees the full conversation, but the specialist often gets only the latest message, a summary, or a rewritten query. Constraints the user stated earlier ("I'm on the enterprise plan," "don't email me") disappear. If the router rewrites the query to be "cleaner," it can strip exactly the nuance the specialist needed.

### 6. Follow-ups in multi-turn conversations
"What about the other one?" or "Yes, do that" makes no sense on its own. If the router classifies each turn independently, follow-ups get bounced to the wrong agent mid-conversation. The opposite problem also happens: the router stays stuck on the first route when the user has genuinely changed topics.

### 7. Miscalibrated confidence
LLM routers rarely give you a reliable confidence score, so there's no good signal for when to ask a clarifying question or escalate. Classifier-based routers do give scores, but they're often overconfident on inputs unlike their training data, such as new products, new slang, or other languages.

### 8. Model routing: misjudging difficulty
When the router chooses between cheap and expensive models, it has to predict how hard a task is from the prompt alone, and that's hard. Short prompts can be deceptively difficult, so hard tasks get sent to the small model and fail. Teams then raise the threshold to compensate, and the cost savings that justified the router disappear.

### 9. Adversarial steering
If untrusted input reaches the router, a user or an injected document can push the request toward a more privileged route, like an admin tool or a route with write access. The router acts as an authorization boundary even though nobody designed it as one.

### 10. Evaluation blind spots
Teams usually evaluate either the router (classification accuracy) or each specialist in isolation, and rarely the whole pipeline end to end. A router that's 92% accurate in front of specialists that are 90% accurate gives you roughly 83% end to end, before counting any damage from bad handoffs. Changes to one specialist's prompt can also shift what the router should send to it, and nothing catches that.

### 11. Latency and cost of the extra hop
Every request pays for a routing call before any real work starts. If the router is a large model, this can add noticeable latency and cost to every interaction, including trivial ones.

## What works in practice

- **Write route descriptions that are mutually exclusive**, with examples of edge cases and of what does *not* belong in each route. Re-check for overlap every time you add a route.
- **Let the router return multiple routes or a "clarify" action**, not just a single label.
- **Let specialists reject a request** and send it back to the router, with a cap on retries to avoid loops.
- **Pass the full relevant context to the specialist**, not a rewritten query. Route on conversation state, not just the latest message.
- **Log every routing decision along with the outcome.** Review the catch-all route and any rerouted requests regularly, since that's where new categories show up.
- **Use cheap, fast routing first** (rules, embeddings, a small classifier) and fall back to an LLM only for ambiguous cases.
- **Enforce permissions in the specialists and tools themselves**, never in the router.
- **Run end-to-end evals built from real traffic**, including multi-intent and follow-up cases.
