# Roastery And Ledger Guide

Status: v0.1 practical guide
Date: 2026-07-06

Use this guide to evaluate Beans, prompts, roles, and workflows without
inventing quality, token, or cost evidence.

## 1. What Roastery Is

Roastery is Project Coffee's evidence system for model and workflow quality. It
records what was tested, what happened, what was measured, what failed, and what
remains unknown.

Roastery is for evidence, not vibes. A model feeling good is not enough to
change routing policy. A workflow seeming smooth is not enough to skip
verification.

## 2. What Coffee Ledger Is

Coffee Ledger records cost, token, time, and value evidence. It answers:

- what model or tool was used;
- what task it supported;
- what token usage or cost was observed;
- what value the work produced;
- what remains unknown.

Unknown cost or token data is acceptable. Guessing is not.

## 3. Model Evaluation Vs Workflow Evaluation

Model evaluation asks how a Bean performed on a task:

- Did it complete the Order?
- Was the answer correct?
- How many tokens were used?
- What latency or cost was observed?
- Would Coffee use this Bean again for that task type?

Workflow evaluation asks how the process performed:

- Was the scope small enough?
- Did Decaf planning help?
- Were tests or checks run?
- Did human review remain explicit?
- Were Brew Log, Roastery, and Ledger updated?
- Was the diff easy to review?

Use model scorecards for Beans. Use workflow scorecards or tasting notes for
process evidence.

## 4. Cup Test Process

A Cup Test compares Beans on the same Order.

Use the same:

- Order;
- repository state;
- constraints;
- Barista role;
- Recipe or prompt;
- evaluation criteria.

Process:

1. Write or reuse a Cup Test plan.
2. Choose Beans.
3. Confirm the Order uses no secrets or private data.
4. Have the human run the local Cup Test tool or approved runtime.
5. Preserve observed output, status, usage, latency, and errors.
6. Record results in Roastery.
7. Record cost/token notes in Ledger.
8. Score quality only when full outputs are available.
9. Update House Blend only when evidence supports it.

The runner should not silently write policy, scorecards, or Ledger entries. The
human and Barista record evidence after reviewing results.

## 5. Tasting Notes Fields

Useful Tasting Notes fields:

- date;
- Brew/Shot;
- Bean or workflow;
- task or Order;
- status;
- latency if observed;
- token usage if observed;
- cost if observed;
- files read or changed;
- validation run;
- output pointer or summary;
- human corrections;
- result or verdict;
- limitations and next evidence needed.

Keep entries short unless the shot needs detailed evidence.

## 6. Ledger Fields

Useful Ledger fields:

- date;
- task;
- model / Bean / runtime;
- task type;
- estimated tokens;
- observed input/output/total tokens;
- actual cost shown;
- estimated cost if genuinely supported;
- value notes;
- unknown fields clearly marked.

Do not infer cost from vibes or from an incomplete pricing memory. If actual
cost is not shown, write `Unknown`.

## 7. When Costs Or Tokens Are Unknown

Use `Unknown` when:

- the runtime did not show usage;
- the human did not capture the usage line;
- only a response preview was recorded;
- pricing is unavailable or uncertain;
- the work happened in an agent context that does not expose token/cost data.

Unknown is honest evidence. It is better than a fake number.

## 8. Recording Failures Honestly

Failures are useful evidence.

Record:

- exact failure type when safe;
- provider errors without secrets;
- unavailable model slugs;
- rate limits;
- missing credentials without exposing values;
- validation failures;
- human corrections needed;
- whether retry is appropriate.

Do not hide failed candidates. Brew 5 kept Qwen and DeepSeek failures visible,
which made the replacement Bean choice more honest.

## 9. Comparing Beans On The Same Order

For a fair comparison:

- same prompt;
- same repo state;
- same constraints;
- same success criteria;
- same output capture process;
- same scoring rubric.

Avoid comparing one Bean's full output against another Bean's preview. Avoid
changing instructions mid-test. If one Bean fails, record the failure and keep
the comparison limitations visible.

## 10. Recording Full Output Quality

Future Cup Tests should preserve full outputs before scoring quality.

Recommended process:

1. Save or point to each full output in a safe local evidence location.
2. Check the output against the original Order.
3. Run any generated code or tests when applicable.
4. Score correctness, completeness, instruction following, risk behavior, and
   supervision required.
5. Record human corrections.
6. Update House Blend only after enough quality evidence exists.

Do not assign final quality scores from response previews alone.

## 11. Lessons From Brew 5

Brew 5 proved that a local Cup Test runner can compare multiple Beans on the
same Order.

What worked:

- same Order across Beans;
- per-Bean status and latency;
- observed token totals when returned;
- failed candidates recorded instead of hidden;
- provisional House Blend updated from evidence.

What still needs improvement:

- full outputs were not captured;
- final output quality was not scored;
- actual cost remained unknown;
- evidence came from one tiny coding Order.

## 12. Lessons From Brew 7

Brew 7 proved the end-to-end Project Coffee workflow.

Useful evidence:

- Decaf Mode was used;
- implementation was small and standard-library only;
- tests ran;
- Brew Log, Roastery, and Ledger were updated;
- human review and manual commit were preserved;
- unknown cost/tokens stayed unknown.

Workflow evidence belongs in Roastery even when no remote model is invoked.

## 13. Lessons From Brew 8

Brew 8 proved first real project onboarding with Coffee Status.

Useful evidence:

- app-local Project Coffee skeleton was added;
- one tiny README improvement was completed;
- tests and syntax checks ran;
- Roastery recorded what worked and what needs improvement;
- Ledger recorded unknown cost/tokens honestly;
- closeout recorded human review and manual commit evidence.

This is the model for future workflow evaluation.

## 14. Closeout Checklist

Before closing a model or workflow evaluation:

- evidence source is named;
- task/Order is clear;
- Beans or workflow roles are listed;
- tests/checks are recorded;
- costs/tokens are recorded or marked unknown;
- failures are recorded honestly;
- limitations are explicit;
- next evidence needed is named;
- House Blend changes are justified or deferred;
- human review and commit state are recorded when relevant.

## 15. Common Mistakes

- Updating House Blend from vibes.
- Scoring quality from response previews.
- Guessing token counts or costs.
- Hiding failed Beans.
- Comparing different prompts or repo states.
- Forgetting to record human corrections.
- Treating unknown cost as zero cost.
- Sending secrets or private data to a model test.
- Letting a runner mutate Roastery, Ledger, or routing policy automatically.
- Skipping workflow evidence when no model API was used.
