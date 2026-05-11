# Start Here: Node 1 Execution

**Ready to run Node 1?** Follow these 5 simple steps.

---

## Step 1: Open the Prompt File

Open: **WAVE2_CLUSTER_PLAN.md**

Location: `/raid5/source/test/prism/docs/plan/g84-10-model-gilfoyle-comparison-20260508/WAVE2_CLUSTER_PLAN.md`

---

## Step 2: Find Node 1 Prompt

In WAVE2_CLUSTER_PLAN.md, search for:

```
### NODE 1 PROMPT — GPT-4o
```

---

## Step 3: Copy the Prompt

Copy everything from:

```
## Gilfoyle Code Review: Architecture & DI Focus (Node 1 of 3-Node Cluster)
```

Through the end of the prompt (look for `### Token Limit` as the end marker).

**Make sure you copy the ENTIRE section** — from the title all the way to "### Token Limit UNLIMITED".

---

## Step 4: Launch the Run

Send to runSubagent with these exact parameters:

```
Agent: Gilfoyle Code Review God Mode
Model: GPT-4o (copilot)
Prompt: [PASTE THE PROMPT YOU JUST COPIED]
```

---

## Step 5: Wait & Monitor

- Expected runtime: 15-18 minutes
- Look for YAML output with findings
- When complete, copy all findings to clipboard

---

## After Node 1 Completes

1. **Save results** to: `/artifacts/node1-gpt4o-findings.yaml`
2. **Record metrics** from the YAML:
   - Quality score (0-100)
   - Finding count
   - Module coverage (X/3)
3. **Wait 5 minutes** (let Gilfoyle reset for other users)
4. **Start Node 2** using NODE 2 PROMPT from same file

---

## Expected Node 1 Output

| Metric | Expected |
|--------|----------|
| Quality Score | 85-88/100 |
| Finding Count | 12-15 |
| Modules Covered | 3/3 (di.py, scanner_context.py, di_helpers.py) |
| Format | YAML with id, severity, category, location, issue, root_cause |

---

## Troubleshooting

**Q: Can't find NODE 1 PROMPT?**  
A: Search WAVE2_CLUSTER_PLAN.md for "NODE 1 PROMPT" (exact string)

**Q: Not sure where prompt ends?**  
A: Look for "### Token Limit" line - copy up to and including the paragraph after it

**Q: Got error from runSubagent?**  
A: Verify you're using:
- Agent: "Gilfoyle Code Review God Mode" (exact name)
- Model: "GPT-4o (copilot)" (exact name)

**Q: Prompt is too long to copy?**  
A: That's normal! It's ~50 lines. Copy all of it at once.

---

## Next Steps

After Node 1 is saved:
1. Read: SEQUENTIAL_QUICK_REFERENCE.txt
2. Wait 5 minutes
3. Start Node 2 (same process, different prompt)
4. Repeat for Nodes 3A and 3B
5. Merge and analyze all results

---

## Timeline

- Node 1: ~18 min
- Node 2: ~18 min (after 5 min wait)
- Node 3A: ~18 min (after 5 min wait)
- Node 3B: ~18 min (after 5 min wait)
- Merge & Analysis: ~15 min

**Total: ~115 minutes (~2 hours)**

---

## Ready?

You have everything you need. Let's go! 🚀

**Next action:** Open WAVE2_CLUSTER_PLAN.md and copy NODE 1 PROMPT
