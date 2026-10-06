# Project Coffee Manual

## About This Manual

This is the user manual for Project Coffee, the local AI routing
workstation this knowledge base belongs to. It is the document Coffee
retrieves from when someone asks Coffee about itself: what it is, who
built it, how it routes a request, what the coffee vocabulary means, and
what it does not do well.

Written against **Brew 56**. Update this document and re-run
`python router/tools/index_pantry.py` whenever the system changes
materially - a new Bean, a changed toggle, a fixed limitation. Nothing
re-indexes automatically, so an un-updated manual will keep confidently
answering with last month's system. `router/README.md` and `ROADMAP.md`
in this repository both went stale exactly this way; this note exists so
this document does not join them.

This manual describes only what Coffee is and how it works. It
deliberately contains no strategic, commercial, or personal notes about
its author.

## What Project Coffee Is

Project Coffee is a personal AI routing workstation. It runs on one
machine, sits between you and the OpenRouter model marketplace, and
decides which model should answer each request you send.

The problem Project Coffee solves is that most AI chat tools give you one
model at one price for every question, and show you nothing about what
any of it cost. Asking a frontier model to reformat a list costs the same
as asking it to design a system. Coffee instead classifies each request,
picks a model appropriate to what the request actually needs, and writes
the real dollar cost of every single request to a local log you own.

Coffee exposes two interfaces: a browser chat UI, and an
OpenAI-compatible API endpoint that coding tools such as Cursor or
Continue.dev can point at directly. Everything - the request log, the
knowledge base, the session history, the configuration - stays on the
machine Coffee runs on. There is no Project Coffee account, service, or
server.

## Who Built Project Coffee

Who made Project Coffee, who created it, who wrote it, whose project it
is: Project Coffee was built by Ishan Suthar in July 2026 as a personal
AI routing workstation and portfolio project.

The implementation was AI-assisted, with the architecture, every design
decision, and every commit directed and approved by the author.

It is one person's personal system. It is not a company, a product
launch, or a team effort.

## What Makes Coffee Different From An Ordinary Chat App

Four things distinguish Project Coffee from a normal chat application.

**Evidence-based routing.** Coffee does not send everything to one model.
It classifies each request and selects a Bean - its word for a configured
model - suited to that request. Which Bean wins for which kind of task is
driven by recorded evidence from its own benchmark runs and your own
ratings, not by a hardcoded preference.

**Transparent per-request cost.** Every request Coffee serves writes one
row to a local CSV ledger with its real cost, token counts, and outcome.
Where the model provider reports an authoritative cost, Coffee records
that figure rather than its own estimate. The running cost of the message
being generated is displayed live in the UI as it streams.

**Escalation with consent.** When a cheap Bean's answer looks like a
failure, Coffee can re-run the request against a stronger, more expensive
Bean - but past a configured cost threshold it stops and asks you first,
showing what the re-run would cost. It does not quietly spend more of
your money to rescue an answer.

**Everything local.** The ledger, the knowledge base, the chat history,
and the configuration are files on your own machine.

## How Coffee Handles A Request

This is the end-to-end path a request takes through Project Coffee, from
the moment you send it to the moment it is logged.

**1. Classification.** Coffee reads the prompt and labels it with a task
type (such as code, analysis, documentation, or explanation) and a
complexity - either a quick "espresso shot" or a longer "cold brew". This
is a heuristic pass over the text; it does not call a model.

**2. Routing to a Bean.** Using that classification plus its routing
policy, Coffee selects which Bean will answer. It also applies hard
capability constraints: a request with an image attached must go to a
Bean that can see images, and a request needing web search must go to a
Bean that can call tools. Where several Beans qualify, Coffee generally
prefers the cheapest one that does.

**3. Streaming.** Coffee calls the chosen Bean and streams the answer
back token by token, so text appears as it is generated rather than after
a long wait.

**4. Failure detection.** When the response finishes, Coffee inspects it
for the shapes of failure - truncated mid-sentence, empty, or a refusal.

**5. Escalation with an approval gate.** If the response looks like a
failure, Coffee considers re-running it against a stronger Bean. Below
the configured cost cap it proceeds automatically. At or above the cap it
pauses and shows you an approval card with the estimated cost, and waits
for your decision. The pause survives closing and reopening the page.

**6. The Ledger write.** Every request - escalated or not, successful or
not - writes one row to the ledger with the Bean used, the token counts,
the real cost, and the outcome.

## The Bean Roster And What Each Role Means

A **Bean** is one configured model in Project Coffee. Each Bean has an
alias, a role, price-per-token figures, and capability flags recording
whether it can process images and whether it can call tools. Coffee
refers to Beans by alias everywhere you can see - in the UI, in its API
responses, and in its event stream. The underlying provider model IDs
exist only in the configuration file, the ledger, and the outbound
request itself, and are never shown to a user.

The roles currently in use are:

- **default** - the Bean that handles ordinary requests when nothing
  demands otherwise.
- **fallback** - the Bean used when the default is unsuitable or
  unavailable.
- **comparison** - Beans kept in the roster to be benchmarked against the
  others, rather than to serve as anyone's default.
- **premium** - the strongest and most expensive Bean, used for hard
  requests and as the target of an escalation.
- **specialist** - Beans carrying a capability the cheaper Beans lack,
  most importantly the ability to process images.
- **web_search_primary** and **web_search_fallback** - the tool-calling
  Beans that handle requests where you have turned web search on, with
  the fallback used if the primary is unavailable.

A role is a description of a Bean's intended job, not a lock. Coffee's
selection is driven by capability and price, so adding a cheap, capable
Bean under any role can change which Bean actually gets picked.

## How To Use Coffee

These are the controls Project Coffee gives you in its chat UI.

**Use Pantry.** Off by default. When on, Coffee searches its local
knowledge base for passages relevant to your prompt and includes the best
matches with your request, showing citation chips for the files it drew
from. This is how Coffee answers questions about itself, and how you give
it long reference material to work from.

**Use Web.** Off by default. When on, Coffee routes the request to a
tool-calling Bean that can search the web, and shows citation chips for
the sources it used. Web search costs money per search on top of the
Bean's own token cost.

**Remember chat.** A per-session toggle. When on, Coffee includes earlier
turns of the conversation with each new request, so follow-up questions
work. See the memory section below for how far back that actually goes.

**Projects and sessions.** Chats live inside projects. You can create
projects, and rename or delete individual chat sessions.

**Attachments.** You can drag, drop, or paste files into the composer.
Coffee extracts the text of PDFs and text files and includes it with your
prompt. Images are sent to a Bean capable of processing them.

**Ratings.** You can rate a response. Ratings are recorded and feed into
a rebuild of the routing policy - but that rebuild is a manual action
that shows you a diff of what would change and applies nothing until you
approve it. Rating a response does not silently re-route anything.

**Spend caps.** Coffee enforces a per-user daily spending cap and a
global daily cap across all users, both on real calendar days, and a
per-minute request limit as a guard against runaway loops. When a cap is
reached, Coffee refuses the request rather than spending past it.

**The Tips Jar.** The running dollar total for the message currently
being generated, displayed live in the UI with a coin dropping into a jar
as tokens arrive. It is a cost display, not a payment feature - no money
goes anywhere except to your own model provider account.

## Conversation Memory And Known Limits

**Conversation memory is windowed, and it trims silently.** This is the
most important limitation to understand about Project Coffee.

When Remember chat is on, Coffee includes previous turns with each new
request - but only up to a fixed budget, both a maximum number of
messages and a maximum total number of characters. When a conversation
grows past that budget, Coffee drops the **oldest whole turns first**, and
it does not tell you it has done so.

The practical consequence: if you paste a long document early in a
conversation and keep talking, that document will eventually fall out of
the window. From then on the model genuinely has not been sent it, and
will correctly say so. This reads like the model forgetting or lying, but
it is the windowing doing exactly what it was configured to do. Nothing
in the UI currently warns you when it happens.

**What to do about it.** Long reference material belongs in the Pantry,
not in chat history. Put the document in the `knowledge/` directory, run
`python router/tools/index_pantry.py`, and turn Use Pantry on - retrieved
passages are fetched fresh for every request and are never trimmed away
by conversation length. The alternative, raising the history character
budget in the router's settings, makes the window bigger but does not
make it unbounded, and every extra character is billed on every
subsequent request.

**Other current limits, stated plainly:**

- Image requests do not always land on the cheapest Bean capable of
  handling them, so an attached image can cost more than it needed to.
- If the model provider rate-limits or errors on a request, that request
  fails outright. Coffee does not currently retry it or fall back to a
  different Bean on a transport error - only on a completed-but-bad
  answer.
- Coffee does not display a model's internal reasoning, or break down how
  much of a bill was reasoning versus answer. The reasoning cost is
  correctly included in the total it charges you; it just is not itemised.
- Re-indexing the Pantry and rebuilding the routing policy are both
  manual commands. Neither happens on its own.

## The Coffee Vocabulary

Project Coffee names its parts after coffee. Every term below was checked
against the running system; where a term is development vocabulary rather
than a live component, this says so.

- **Bean** - one configured model, with an alias, a role, pricing, and
  capability flags. Live runtime concept: Beans are what Coffee routes
  between, and the alias is what you see in the UI.
- **Barista** - a role card describing how an AI assistant should work on
  a given kind of task, and the source of the "espresso shot" / "cold
  brew" work-mode vocabulary Coffee's classifier uses. These role cards
  are used by AI assistants working **on** Coffee's own codebase; the
  router does not load a Barista when it answers your request. The
  animated figure in the chat UI is also called the barista.
- **Ledger** - the cost and usage log. One machine-written CSV row per
  request, plus hand-maintained Markdown logs for earlier work predating
  the router.
- **Pantry** - the local knowledge store: the `knowledge/` directory,
  indexed for keyword search, that the Use Pantry toggle searches and
  cites from. This manual lives in the Pantry.
- **Brew Log** - the project's running development diary. Live: Coffee's
  own memory-proposal feature can draft changes to exactly two Brew Log
  files, and never applies them without approval.
- **Cup Test** - a benchmark that runs the same task across several Beans
  for comparison. Live: recorded Cup Test scores are one of the inputs
  the routing policy is rebuilt from.
- **Roastery** - the subsystem holding the Cup Tests and the tasting
  notes, the evidence log of what actually happened on real model runs.
- **Brew** - one unit of development work on Coffee itself, roughly one
  feature or fix, each preceded by a written plan the author approves
  before any code is written. Development-process vocabulary, not a
  runtime component - Brews are how Coffee's own history is numbered.
