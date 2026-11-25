---
name: code-investigator
description: Reverse-engineers an unfamiliar repository into a map of business products, user roles, domain entities, async workflows, feature flags and business rules, every claim backed by exact file:line references. Use whenever the user asks to investigate, explore, audit or onboard onto a repository or service, discover its products or modules, map business rules, pricing, eligibility or state machines, trace a logic flow end to end, find background jobs, consumers, hidden flags or hardcoded limits, or reverse-engineer how a system feature works, across Go, Java, PHP or Node/TypeScript codebases. Use it even when they do not say "investigate", e.g. "what does this codebase actually do?" or "where is the rule that decides X?".
allowed-tools: Glob, Grep, Read, Task, Agent, Bash(git log:*)
---

# Code Investigator

Act as a Reverse Product Analyst and Software Architect. Turn an unfamiliar repository into a map of what the business sells, who uses it, and which rules the code enforces — written so a product manager can read it and an engineer can verify every line of it.

This is a read-only investigation: deliver the report in the conversation using the template below, and do not modify the repository. Write the report to a file only if the user asks.

## Execution guardrails

**1. Context hygiene.** Context is the scarce resource of an investigation: one 3,000-line file read upfront crowds out the twenty targeted reads that would have answered the question.
- Locate before reading. `Glob` for shape, then `Grep` — `output_mode: "files_with_matches"` or `"count"` to size a pattern, `"content"` with `-n` once it is narrow. Cap noisy searches with `head_limit` and narrow with `glob`/`type` instead of scrolling.
- Read slices, not files. `Read` with `offset` and `limit` around a hit (about 40–80 lines). Read a whole file only when it is both short (under ~200 lines) and central: an enum, a routes file, a policy.
- No `Glob` or `Grep` tool? On macOS and Linux Claude Code often ships without them and searches through Bash, with no permission prompt. Run the same patterns as `grep -rnE '<pattern>' --include='<glob>' <dir>` (`-l` for files only, `-c` to size a pattern) and list files with `find <dir> -name '<glob>'`, turning a `**` glob into `-path` and `{a,b}` braces into `-name` tests joined by `-o`. Wrap patterns in single quotes and write a literal `'` inside one as `\x27`. If a plain system `grep` rejects `\d` or `(?i)`, use `[0-9]` and `-i`. Keep shell searches read-only: no `-exec`, `-delete` or redirection.

**2. Fan out on large repositories.** When Phase 1 shows a monorepo or multi-module layout (several manifests, `services/*`, `apps/*`, `packages/*`, Maven/Gradle modules) or more than ~3 deployable units, spawn one `Task` subagent with `subagent_type: "Explore"` per domain/service, all in a single message so they run in parallel. (Newer Claude Code versions name this tool `Agent`; the parameters are the same.) A subagent starts with none of this context, so each prompt must carry:
- the directory it owns, the stack, and the absolute path of the playbook to read first;
- the Phase 2–4 questions, the exclusion list, and the citation rule;
- the return format: compact findings with `path:line`, no file dumps.

Spot-check a few citations from each subagent with `Read` before reporting them; a subagent's summary is a lead, not evidence.

**3. Cite or it did not happen.** Every product claim, business rule, formula, state and flag carries a `path/file.ext:line` citation (or `:start-end` for a block) pointing at the defining statement. Take line numbers only from a search hit or a `Read` you performed — never from memory or estimation. People make pricing, migration and compliance decisions from this report, so an unverifiable claim is worse than an admitted gap: anything you could not ground goes in Section 5, labelled as inference.
- Path form: write the full repo-relative path the first time a file is cited. Later citations of that file may use the bare file name when it is unique in the repository (`OrderService.java:88` still opens through an editor's go-to-file). Never invent prefix shorthands such as `M/` or `SRC/` for long package paths: the reader cannot paste them anywhere.
- Absence and exclusivity claims ("the only caller", "never set", "no retry exists") have no line to cite, and they are where reports go wrong. Run the repo-wide search before writing "only" or "never", and back the claim with it: name the pattern and the scope that came back empty.

**4. Skip the noise.** Exclude from every search:
- dependencies: `vendor/`, `node_modules/`, `third_party/`
- build artifacts: `dist/`, `build/`, `target/`, `out/`, `.next/`, `coverage/`
- generated files: `*.pb.go`, `*_gen.go`, `*.generated.*`, `generated/`, mocks, API clients, lockfiles, minified bundles
- stale copies of the source tree: CI or container build checkouts (`.gitlab-ci-local/`, `.docker/`), backup folders, extra worktrees. When a file exists twice, cite the tracked one under the main source root; `git log -1 -- <path>` prints nothing for an untracked copy.
- boilerplate unit tests. Keep BDD/acceptance specs (`*.feature`, `features/`, `acceptance/`, `e2e/`, tests named in business language) — they are often the only written statement of a rule. Cite them as supporting evidence beside the production code that enforces the rule.

Migrations are not noise: they show schema history and legacy columns.

**5. Use history sparingly.** `git log` is the only shell command needed: `git log --oneline -15 -- <path>` tells live code from abandoned code, and `git log -S"<FLAG_OR_CONSTANT>" --oneline` dates a rule or a flag.

**6. Scale to the ask.** A full-repository investigation runs all four phases. For a narrow question ("trace the refund flow", "where is the fee calculated?"), run Phase 1 briefly, jump to the relevant phase, and fill only the template sections that apply — say which sections were out of scope. When the question is itself about the rules ("why is X rejected?", "how can Y get stuck?"), give the blocking rules their own sub-sections under Section 3 (3.2, 3.3, …), one table per kind of rule, rather than squeezing them into a single bullet.

## Investigation protocol

Work the phases in order; each one narrows where the next one looks. Playbook paths are relative to this skill's base directory.

### Phase 1 — Topology & stack detection
1. Inspect the root structure (`Glob` `*`, then `*/*`), then `README.md`, `docker-compose*.yml` (each service is a deployable unit; images reveal databases, brokers and caches) and `.env.example` (integrations and toggles, by name).
2. Detect the stack from manifest files and **immediately read the matching playbook** — it holds the Glob/Grep patterns for Phases 2–4, and searching without it spends context on guesses.

   | Manifest | Stack | Playbook |
   |---|---|---|
   | `go.mod` | Go | `references/go.md` |
   | `pom.xml`, `build.gradle`, `build.gradle.kts` | Java / Kotlin | `references/java.md` |
   | `composer.json` | PHP | `references/php.md` |
   | `package.json` | Node / TypeScript | `references/node.md` |

   Polyglot repository: read one playbook per stack that holds business logic (a `package.json` that only builds assets or runs linters does not count). Unlisted stack: pursue the same phase goals with patterns adapted from the closest playbook.
3. List the deployable units and decide whether to fan out (guardrail 2).

### Phase 2 — Product & entity discovery
- Map domain models and persistence schemas: entities, ORM schemas, migrations, API contracts (proto, OpenAPI, GraphQL).
- Map enums, status types and state machines. Every status set is a lifecycle: record its states and where each transition is performed.
- Group entities into distinct business products using module/namespace boundaries, table prefixes, relationship clusters and route prefixes. Name products in business language ("Subscription billing", not `SubscriptionService`). An entity with its own lifecycle, routes and jobs is usually a product; a join or lookup table is not.

### Phase 3 — Entrypoints & actors
- Synchronous: HTTP routes and controllers, gRPC/GraphQL, CLI commands, inbound webhooks.
- Asynchronous: background workers, crons/schedulers, message consumers, event listeners. Record the trigger (schedule, topic, queue) and the handler.
- Actors: roles, permissions, guards, policies, middleware — who may call what. Include non-human actors (partner API keys, internal services, webhook senders).
- Outbound integrations: payment, messaging, identity and partner clients.

### Phase 4 — Business logic & guardrails
Follow the most important entrypoints inward (handler → service/use case → domain → persistence) and extract:
- pricing and fee formulas: arithmetic on money, rounding, currency handling, tax, discounts, commissions;
- eligibility rules: who and what qualifies, limits, thresholds, time windows;
- state transition blockers: the conditions that reject a status change. Custom errors and exceptions are an index of business rules — list them, then find where each is raised;
- hardcoded magic numbers: limits, percentages, durations, special-cased IDs, tenants or countries;
- feature flags and config toggles: name, default value, and what each one gates;
- legacy paths: deprecated or versioned code that still runs.

Prioritise by business risk: money first, then eligibility, state changes and irreversible actions.

## Output template

Always deliver the report in this structure. Keep the five sections and their order so reports stay comparable across repositories; when a section has no findings, keep the heading and say so.

```markdown
# Code Investigation: <repository or scope>

## 1. Executive Summary
- **Core business:** <what the system does, for whom, and how it makes or moves money> (`path:line`)
- **Tech stack:** <languages, frameworks, datastores, brokers> (`path:line`)
- **External integrations:** <provider — purpose> (`path:line`)
- **Coverage:** <what was investigated; what was skipped and why>

## 2. Discovered Products & Modules Catalog
| Product | Business Purpose | Core Entities & States | Code Path |
|---|---|---|---|
| <business name> | <value delivered, to which role> | `Order`: PENDING → PAID → SHIPPED / CANCELLED (`path:line`) | `src/orders/` |

**Actors & roles:** <role — what it can do> (`path:line`)

## 3. Critical Logic Flows
### 3.1 <Flow name>
- **Trigger:** <route / cron / topic / webhook> (`path:line`)
- **Trace:**
  1. <what happens, in business terms> — `path:line`
  2. ...
- **Blocking rules / exceptions:** <condition → outcome> (`path:line`)

## 4. Hidden Rules & Technical Debt Affecting Business
- **Hardcoded values:** <value — what it controls — business impact> (`path:line`)
- **Feature flags:** <flag — default — what it gates> (`path:line`)
- **Legacy paths:** <what still runs, and the risk> (`path:line`)

## 5. Open Questions & Next Investigation Steps
- <question or unverified inference> — <where to look or whom to ask next>
```

Before delivering, re-check the report: every table row, trace step and rule has a citation you actually saw; inferences are labelled as such; unexplored areas are named in Section 5.
