---
status: proposed
date: 2026-09-23
---
# Zero Data Retention as an opt-in guarantee for Mee-hosted agents

## Context and Problem Statement

Who hosts an agent changes what guarantee people expect about access to their data. When Alice hosts her own agent — including the case where she rents compute for it — and has visibility into what happens on that server, that access is hers to have; it is not a concern. When Mee hosts the agent, the same category of access, now held by Mee rather than Alice, becomes something people want ruled out: a real guarantee that Mee itself cannot see the personal data flowing through the agent. Whether that guarantee is achievable, and at what layer it would have to live — Mee's own hosting infrastructure, the LLM inference call, or both — needs research; Zero Data Retention (ZDR), offered at minimum as an opt-in, is the candidate mechanism to research.

## Decision Drivers

* ZDR is not a standardized or certifiable term — providers self-define its scope and exceptions. OpenAI's ZDR excludes stateful features such as conversations, threads and agent products even where the underlying model call qualifies ([OpenAI, data controls](https://platform.openai.com/docs/guides/your-data)); Google's Gemini profile still permits a project-isolated in-memory cache with a 24-hour TTL and treats that as ZDR-compatible ([Google Cloud, data governance](https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance)). A Mee-level guarantee needs its own explicit, published specification — it cannot be inherited from a provider's label.
* Opt-in-behind-approval is already how major providers structure ZDR, not a novel shape: OpenAI requires eligible customers to be approved for ZDR at the organization/project level, with the default account excluded ([OpenAI, Offering Zero Data Retention for Frontier Models](https://openai.com/index/offering-zero-data-retention-for-frontier-models/)); Cohere states it does not log customer prompts or generations "if you have been approved for zero data retention" ([Cohere, enterprise data commitments](https://cohere.com/enterprise-data-commitments)). That validates the opt-in framing, but it also means eligibility is tracked per account/project/model, not assumed from a provider name.
* ZDR at the model-call layer does not automatically cover the agent layer. Cursor states that "most models run under Cursor's ZDR agreements," yet its Cloud Agents necessarily keep an encrypted repository copy while an agent is running ([Cursor, Privacy and data governance](https://cursor.com/docs/enterprise/privacy-and-data-governance)). An agent's guarantee is a property of its whole execution graph — planner, tool calls, external APIs, intermediate storage — not just the inference endpoint it happens to call.
* A retention mode enforceable as policy is stronger than one that's merely promised: AWS Bedrock's `none` retention mode — under which neither AWS nor the model provider writes request/response data to durable storage — can be mandated via IAM/Service-Control Policies, so a workload that doesn't use it is rejected rather than relying on every request remembering a flag ([AWS Bedrock, data retention](https://docs.aws.amazon.com/bedrock/latest/userguide/data-retention.html)).
* Third-party attestations bound a claim, they don't prove it: SOC 2 is CPA-provided assurance over controls whose scope is defined per engagement ([AICPA, SOC suite of services](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services)); ISO/IEC 27001 is a risk-management-based information-security standard ([ISO/IEC 27001](https://www.iso.org/standard/27001)). Neither, by existing, certifies that a specific request was never retained.
* Whatever is offered should not block agent hosting for users who don't need the guarantee — it should read as an opt-in mode, not a default that taxes every deployment.

## Considered Options

* **No special guarantee** — Mee-hosted agents get the same operational access as any host Mee runs; users who need stronger isolation self-host.
* **Zero Data Retention as an opt-in mode, defined and owned by Mee** — Mee publishes its own ZDR profile covering the whole agent execution graph, not just an inference call, lets a user require it, and fails the request closed rather than silently falling back to an ordinary host when it can't be met — following the enforceable-policy pattern AWS Bedrock uses for its `none` mode rather than a documentation-only promise
* **Customer-controlled keys as a complement** — content that does pass through Mee's infrastructure is encrypted with keys Mee itself cannot access, narrowing what "Mee has access" means even where some durable storage remains
* **Something else PDN-level** — an identity/isolation primitive (the "agent as restricted identity projection" direction) that makes the question moot rather than answering it with a retention policy

## Decision Outcome

Not yet decided. This ADR exists to record the problem and the leaning, not to close it. The research confirms two things worth acting on regardless of which option is eventually chosen: (1) ZDR requires Mee to author and publish its own specification rather than pointing at an inference provider's — provider-side ZDR (option covered by BYOK) and Mee's-own-hosting ZDR are separate guarantees that don't substitute for each other; and (2) a guarantee that can be enforced as policy (AWS's IAM/SCP-mandated `none` mode being the clearest public example) is categorically stronger than one that is only documented.

## Validation

To be defined once the option is chosen. AWS's IAM/Service-Control-Policy enforcement of Bedrock's `none` retention mode ([AWS Bedrock, data retention](https://docs.aws.amazon.com/bedrock/latest/userguide/data-retention.html)) is one existing example of turning a retention commitment into a checkable, policy-enforced control rather than a claim to take on trust.
