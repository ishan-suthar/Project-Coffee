# Model Routing and House Blend Guide

Status: Brew 9 / 9H  
Date: 2026-07-06

## Purpose

This guide explains how Project Coffee chooses Beans for work, what the current provisional House Blend is, how fallbacks work, and when Roastery evidence should be refreshed.

It summarizes recorded Project Coffee evidence only. It does not update model availability, name a permanent winner, or replace human judgment.

## Coffee Core Concept

Coffee Core is the local routing layer that lets Project Coffee compare and use replaceable model providers without making any one provider the identity of the project.

Coffee Core should:

- keep Project Coffee model-independent;
- support repeatable Roastery Cup Tests;
- record enough evidence to compare Beans honestly;
- preserve local-first safety rules;
- avoid sending secrets or sensitive data to remote models.

## Current Coffee Core

The current Coffee Core is the local OpenRouter client and Cup Test runner.

OpenRouter is the current routing layer because it made local same-Order comparisons possible during Brew 5. It is not a permanent dependency. If a better local routing layer appears later, Project Coffee can evaluate it through Roastery evidence before changing the House Blend.

The runner helps compare Beans on the same Order, but it does not make policy decisions by itself. Humans review the evidence, update House Blend deliberately, and keep the recommendation provisional until enough work has been measured.

## Beans

A Bean is a specific model route that can be used for a Project Coffee task.

Beans are replaceable. A Bean can be promoted, demoted, or removed when evidence changes. Provider availability, latency, cost, and quality can all shift over time, so Project Coffee treats routing as an evidence trail rather than a permanent ranking.

## Current Provisional House Blend

| Role | Bean | Current reason |
| --- | --- | --- |
| Default Bean | `nvidia/nemotron-3-ultra-550b-a55b:free` | Succeeded in recorded Cup Tests and had the fastest, lowest-token result in the 8J rerun. |
| Fallback Bean | `cohere/north-mini-code:free` | Succeeded on the same Order and is the first fallback when the default Bean fails or is unavailable. |
| Secondary fallback / comparison Bean | `poolside/laguna-m.1:free` | Succeeded on the same Order and remains useful for comparison or second fallback coverage. |

This House Blend is provisional. It is based on limited Roastery evidence, not on broad production usage.

## Failed Candidates

These Beans are not defaults because the recorded Cup Tests did not produce usable successful results.

| Bean | Recorded issue | Routing decision |
| --- | --- | --- |
| `qwen/qwen3-coder:free` | Provider or rate-limit failure was recorded during Cup Test work. | Do not use as default until a future Cup Test succeeds. |
| `deepseek/deepseek-r1:free` | Recorded as unavailable. | Do not use as default until availability changes and a future Cup Test succeeds. |
| `deepseek/deepseek-r1-0528-qwen3-8b:free` | Recorded with no usable endpoints. | Do not use as default until endpoint availability changes and a future Cup Test succeeds. |

Failures are useful evidence. They prevent Project Coffee from routing work to a Bean that looked good on paper but did not work locally.

## What Provisional Means

Provisional means the current House Blend is the best recorded choice for now, not a permanent recommendation.

The current recommendation is limited because:

- the successful comparisons used a small Order;
- full outputs were not preserved for complete quality scoring;
- actual costs were unknown or not exposed in the recorded evidence;
- free endpoints and provider routing can change;
- more task types need to be tested before broad confidence is earned.

Project Coffee should keep using the provisional House Blend for low-risk local work while recording new evidence and staying ready to change it.

## Task Routing Guidance

| Task type | Recommended routing |
| --- | --- |
| Decaf planning, repo maps, read-only reviews, and documentation plans | No remote Bean is required unless the human explicitly approves one. |
| Tiny local implementation or focused documentation work | Use the default Bean if model assistance is approved; fall back to Cohere if the default fails. |
| Comparison, fallback coverage, or a second opinion | Use Poolside as the secondary comparison Bean. |
| Security-sensitive, private, regulated, production, firmware, medical, legal, or financial work | Stay in Decaf first and ask for human approval before any remote model use. |
| Broad architecture, high-risk changes, or uncertain tasks | Plan first, use the smallest safe step, and route only after approval. |

The routing habit is simple: local-first, evidence-first, and human-approved when risk rises.

## Premium Escalation Rule

Premium Beans require explicit human approval before use.

Use premium escalation only when the work justifies the cost or quality need, such as:

- a high-value implementation where free Beans are failing;
- a complex review where a second high-quality opinion is worth the spend;
- a Roastery comparison designed to measure whether a paid Bean should enter the House Blend.

Record the reason, route, outcome, tokens, cost, and human fixes when available. If any value is unavailable, record it as `unknown`.

## Failure Handling

When a Bean fails:

1. Record the failure honestly in Roastery.
2. Note the route, provider/model, error class, and whether retrying is reasonable.
3. Try the fallback Bean only if the task still needs remote model assistance.
4. Keep Decaf Mode as the safe fallback for planning, review, and documentation.
5. Do not promote a failed Bean because it is popular, familiar, or theoretically strong.

Never send secrets or sensitive data to a remote Bean. If the task needs private context, reduce the prompt to non-sensitive facts or keep the work local.

## When To Rerun Cup Tests

Rerun Roastery Cup Tests when:

- a default or fallback Bean starts failing;
- provider availability changes;
- a new candidate Bean looks useful;
- a premium Bean is being considered;
- Project Coffee starts a new task class that the current evidence does not cover;
- latency, quality, token use, or cost becomes noticeably worse;
- the House Blend has not been checked for a meaningful stretch of work.

Use the same Order across Beans when comparing candidates. Do not change the Order mid-test unless the test is explicitly measuring a different task.

## Evidence To Capture Next Time

Future Cup Tests should capture:

- full output;
- route, provider, and model;
- latency;
- input, output, and total tokens;
- actual cost;
- quality score;
- human fixes needed;
- failure details;
- whether the output was accepted, edited, or rejected.

Unknown values are acceptable when the tool does not expose them. Guessing is not.

## Future Note

OmniRoute may be evaluated later as a possible Coffee Core replacement or wrapper.

OpenRouter remains the current plan until Project Coffee records enough evidence to justify changing the Coffee Core. Any future routing layer should be judged by the same standard: repeatable tests, honest failures, clear costs, and human-reviewed quality.

## Closeout Rule

Do not update House Blend from vibes, marketing copy, or a single impressive answer. Update it when Roastery evidence shows a better routing decision and the human approves the change.
