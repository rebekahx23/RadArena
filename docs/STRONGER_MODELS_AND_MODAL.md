# Stronger-model and MedGemma cost plan

Prices checked November 4, 2026 against the public OpenRouter models endpoint and
official Modal/Google documentation. This is planning, not a deployment or a measured
MedGemma throughput result. No stronger-model inference or Modal compute was purchased.
Machine-readable assumptions and calculations are in
`reports/stronger_model_cost_estimates_2026-11-04.json`.

## What to investigate

General model capability may contribute to weak image observations and unreliable
contradiction judgments. The existing evidence does not establish how much. Freeze
the current non-RadGraph workflow first, then run a small development factorial:

| Condition | Planning and assessment | Image observations |
| --- | --- | --- |
| Baseline | Gemma 3 27B | Gemma 3 27B |
| Text upgrade | Gemini 2.5 Pro | Gemma 3 27B |
| Vision upgrade | Gemma 3 27B | Gemini 2.5 Pro or Flash, choose one before running |
| Both | Gemini 2.5 Pro | The same vision candidate as above |

These are candidate upgrades, not measured rankings on RadArena. Do not simultaneously
change references, prompts, memory, and model when attributing a difference to capability.
Use the reviewed evidence-to-verdict diagnostic separately. Start with the six development
reports, then expand development coverage; freeze before any test run.

Gemini 2.5 Flash is the economical fully hosted option. Pro is a useful reasoning
comparison. Current OpenRouter list prices per million input/output tokens are
$0.30/$2.50 for Flash and $1.25/$10 for Pro below 200k input tokens per request.
Pro has a higher long-context tier above that threshold. Gemini 3 Flash Preview is
also listed at $0.50/$3, but is not included in the calculations below.
Sources: [Flash](https://openrouter.ai/google/gemini-2.5-flash),
[Pro](https://openrouter.ai/google/gemini-2.5-pro),
[public catalog](https://openrouter.ai/api/v1/models).

The current audited runner only approves Qwen 8B and Gemma 27B price/context bounds.
New profiles require explicit verified budget-bound configuration before live use;
editing an environment variable alone is not enough. No such enabling change was
made for this cost-planning task.

## Measured workload and longer-output assumptions

The fresh no-RadGraph pilot completed six reports. Blue made 12 text calls (10,015
input / 1,142 output tokens) and 18 image calls (18,304 input / 2,341 output tokens).
The text-only baseline added six calls (9,001 / 367 tokens), and direct image verification
added six (12,313 / 518 tokens). These are final successful episode usage totals, not
transport-failure attempts or a count of fresh cache misses.

For N studies, each with one unchanged and one edited report:

- Blue only: 2N candidates, up to 4N text calls and 6N image calls.
- All three verifier methods: 2N candidates, up to 6N text and 8N image calls total.
- General cost formula: sum over calls of `(input_tokens * input_rate +
  billable_output_tokens * output_rate) / 1,000,000`.

The longer-form scenario assumes **6,000 input tokens per text call**, **4,000 input
tokens per image call including image processing**, and **1,000 total billable output
tokens per call including any reasoning**. It assumes three image checks per Blue
episode. These are chosen planning assumptions, not measured token counts for Gemini.
Different models tokenize images differently; internal reasoning can consume substantial
output budget. There is no assumed batch discount or prompt-cache saving.

| Profile | 30 studies, Blue only | 100 studies, Blue only | 100 studies, all three methods |
| --- | ---: | ---: | ---: |
| Flash for text and vision | $1.18 | $3.94 | $5.54 |
| Pro for text, Flash for vision | $2.77 | $9.22 | $13.46 |
| Pro for text and vision | $4.80 | $16.00 | $22.50 |

For the existing 30-study test comparison, all three methods would instead be about
$1.66 (all Flash), $4.04 (Pro text / Flash vision), or $6.75 (all Pro) under the same
longer-form assumptions. Add 25-50% headroom for token variation and failed/repeated
requests; that headroom is a planning margin, not a guaranteed bound.

At the pilot's short observed output lengths, Blue-only estimates for 100 studies
would be about $0.57, $1.18, and $2.34 respectively. This lower estimate assumes that
new models retain roughly the same token footprint, which is particularly uncertain
for image and reasoning tokens. Do not extrapolate a cents-level pilot to arbitrarily
long responses without a cap.

These totals exclude new Red generations, reflection, learning, handbook-selector
calls, purchase fees, and additional model/ablation conditions. A five-round experiment
repeating the same workload is roughly five times the inference work, before those
additional stages. Hosted API batching is a separate integration; current synchronous
calls receive no batch discount in this estimate.

## MedGemma on Modal

Use `google/medgemma-1.5-4b-it` as the first specialist image-tool candidate. Google
describes it as a multimodal medical model with a medically pretrained image encoder.
Its 4B size does not imply that it will outperform a larger general model on our task.
The model card has limitations on evaluated multi-image and multi-turn use; independently
validate our paired-view protocol. Keep planning, report editing, and final assessment
in the chosen general model, with MedGemma returning observations/limitations.

Sources: [MedGemma model card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card),
[weights and access terms](https://huggingface.co/google/medgemma-1.5-4b-it).
Hugging Face access requires accepting the model terms and supplying an authorized
token. Deployment would use a Modal secret, cached weights, one bounded worker, and
an on-demand endpoint that scales to zero. It is inference, not model training.
Our current vision-model slot also drives Red and the direct VLM baseline, so a
specialist image-tool adapter/slot is needed to substitute only Blue's image tool.

Google's hardware FAQ suggests an L4 with 24 GB for 4B BF16 at a moderate context and
concurrency. Model weights alone are not the complete memory requirement. For 27B,
the text-only and multimodal variants must be distinguished; a text-only checkpoint
cannot inspect X-rays. A100 80 GB is a reasonable starting candidate for full-precision
27B multimodal inference, with actual memory sizing still to be tested.
[Official hardware guidance](https://developers.google.com/health-ai-developer-foundations/faqs).

Current Modal GPU-only rates, converted from per-second prices:

| GPU | GPU cost per hour |
| --- | ---: |
| L4 | $0.7992 |
| A10 | $1.1016 |
| L40S | $1.9512 |
| A100 80 GB | $2.4984 |

CPU and RAM are additional. An illustrative L4 allocation with one physical CPU core
and 16 GiB RAM totals approximately **$0.974/hour** at list prices. Modal lists $30/month
in Starter compute credits; verify actual account eligibility/remaining credit rather
than assuming this project incurs no cash expense. [Modal pricing](https://modal.com/pricing).

For 100 studies, 200 candidate reports and three image checks each, there are 600 tool
calls. Serving two views separately means **1,200 single-view model requests**. With
that illustrative allocation and Flash text planning/assessment:

| Assumed average MedGemma request time | GPU hours | Compute + Flash text estimate |
| --- | ---: | ---: |
| 10 seconds | 3.3 | $4.97 |
| 30 seconds | 10 | $11.46 |
| 60 seconds | 20 | $21.21 |
| 90 seconds | 30 | $30.95 |

These are **unmeasured throughput scenarios**, not MedGemma speed claims. Short
observations may fall toward the faster scenarios; long generations can move toward
the slower ones. Shared two-view inference, caching repeated image/question pairs,
or genuine GPU batching could reduce work; those optimizations require validation
and are not assumed. Larger CPU/RAM allocations raise the rate.

Modal also bills model loading and warm idle resources until scale-down. Long pauses
waiting for external text-model responses can therefore add GPU time. Persist weights,
queue GPU work efficiently, bound container lifetime/concurrency, and avoid leaving
a GPU warm between experiments. [Modal cold-start/billing guidance](https://modal.com/docs/guide/cold-start).
The table excludes startup/debugging, storage/egress if applicable, and idle overhead.

## Proposed use of the $10 cap

Reserve about $1 for the small stronger-model ablation, up to $6 for the selected
main comparison, $1 for a bounded MedGemma throughput/quality pilot, and $2 for
fees/contingency. Adapt the allocations to actual pilot usage, keeping one total ledger
across providers. A broad long-form, multi-round model sweep will exceed this budget.
The next concrete step is the hosted-model comparison; a short Modal pilot can then
measure image quality, tokens/second, cold-start time, and cost before sizing a batch.
