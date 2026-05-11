# Phase 3 Micro-Swarm Prompt

```text
Role: <AGENT_NAME>, one investigator in a temporary micro-swarm for FIND-<NN>.

Finding:
  - id: FIND-<NN>
  - question: <specific ambiguity to resolve>
  - role focus: <imports|tests|ownership>

Inputs:
  - findings.yaml entry for FIND-<NN>
  - cached import-graph.json
  - finding-scoped architecture graph slice
  - only the files needed for your question

Write your artifact to:
  docs/plan/<PLAN_ID>/mutl3y-artifacts/phase3/<AGENT_NAME>.md

Return only:
  - agent name
  - artifact path
  - one-sentence conclusion
  - up to 3 risks or open edges

Do not debate with other investigators directly. The foreman synthesizes.
Use the graph slice to enumerate seams and affected neighbors, then verify on live source before concluding.
```
