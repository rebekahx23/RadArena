# Models and the initial $10 experiment budget

The user selected a **$10 total spending cap**. Plan at most **$8 in inference usage**
and reserve $2 for purchase fees/contingency. No credits were purchased, account limits
changed, or paid model calls made during this model-selection work.

## Initial model set

Prices checked November 3, 2026. These are advertised starting USD rates per million
input/output tokens, not assured rates for every provider or image configuration.

| Profile | OpenRouter ID | Input / output | Purpose |
| --- | --- | --- | --- |
| Qwen main | qwen/qwen3-vl-8b-instruct | $0.25 / $0.75 | Main development and controlled agent experiments |
| Gemma baseline | google/gemma-3-27b-it | $0.08 / $0.16 | Cheap alternate open-weight family |
| Gemini comparison | google/gemini-2.5-flash | $0.30 / $2.50 | Additional proprietary-family comparison |
| Optional Flash-Lite | google/gemini-2.5-flash-lite | $0.10 / $0.40 | Cheap controller alternative; not needed initially |

Sources: [Qwen](https://openrouter.ai/qwen/qwen3-vl-8b-instruct),
[Gemma](https://openrouter.ai/google/gemma-3-27b-it),
[Gemini](https://openrouter.ai/google/gemini-2.5-flash),
[Flash-Lite](https://openrouter.ai/google/gemini-2.5-flash-lite).

Gemma 27B also has providers listing higher output rates, such as $0.45/M. Hosted price
does not track parameter count alone. Confirm image acceptance and typed-output behavior
on the actual routed endpoint. This list diversifies model families and price points;
it does not establish a ranking of radiology accuracy. Gemma 3 is a general model and
is distinct from medical-specialist MedGemma. A usable OpenRouter MedGemma endpoint and
its price were not established in this session; do not assume either.

## Cost and experiment plan

A token-only arithmetic illustration of 1M input + 200k output tokens is approximately
$0.40 for Qwen, $0.112 for the lowest listed Gemma rate, or $0.80 for Gemini Flash.
This is not an X-ray benchmark forecast. Actual bills depend on image encoding and
resolution, number of views, repeated image calls, reference context, reasoning tokens,
provider rates, and retries/parsing fallbacks. Models tokenize images differently.

Start with five development studies per family, including controls and corruptions.
Confirm useful image observations and valid structured output. Use measured usage and
failure rates to decide which model proceeds to the main experiments. A full test run
with all three verifier variants is 60 candidates x 3 = 180 episodes per model profile;
avoid also multiplying this grid by every handbook condition and Red/Blue pairing.

| Stage | Spending allocation |
| --- | ---: |
| Compatibility/cost pilots | $1 |
| Main agent experiments | $3 |
| Handbook ablations using the main model | $2 |
| Alternate-family comparisons on fixed cases | $2 |
| Fees and contingency | $2 |

These are allocations, not predictions of stage costs. Reallocate only within the
total cap. Keep output bounded, preserve cache/usage records, and treat missing cost
metadata as unknown rather than free. Free routes may be useful for a smoke test but
should not be assumed stable endpoints for final results.

## Configuration

The default remains Qwen for both text and vision. To test an all-Gemma configuration:

```bash
RADARENA_TEXT_MODEL=google/gemma-3-27b-it \
RADARENA_VISION_MODEL=google/gemma-3-27b-it \
uv run radarena evaluate --split dev --limit-studies 5 --variants direct_vlm \
  --output runs/gemma-dev-pilot
```

Use distinct output directories for each profile. The audited CLI currently supports
Qwen, Gemma, and Gemini Flash using the bounds in `src/radarena/tracing.py`. Set both
variables to the same family for a clean full-system comparison. Hold the vision model
fixed when investigating planner/strategy changes so the comparison isolates those changes.

Current routing: Red's image-conditioned editing uses the vision-model variable; Blue's
image inspection also uses that variable. Planning, handbook selection, and final
assessment use the text-model variable. The CLI demo uses these two settings;
judge commands accept a separate model and Live Arena has its own contestant/reviewer
configuration. Optional mixed development setup: Gemma for text and Qwen for vision;
label it mixed rather than all-Gemma or all-Qwen. Model judging cannot replace clinical review.

## Budget enforcement

The CLI has an audited sequential pilot guard for models with configured bounds:
`--max-cost` (default $0.50) and `--max-calls` (default 80), with provider price filters,
pre-request conservative reserves, and a persistent local ledger. Failed/unknown-cost
requests retain their reserve. See [VALIDATION.md](VALIDATION.md).
This is a per-run control, not an account-wide $10 limit. Track totals across runs.
The supplied key's account settings were read but not changed. No credit purchases
were made. Use provider-side project limits for broader account control.

OpenRouter charges credit-purchase fees separately, so buying $10 in credits may cost
more than $10 cash. References: [pricing](https://openrouter.ai/pricing),
[key limits](https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key),
[current-key metadata](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key).
The latter can inspect remaining credit without exposing the credential in logs.

`configs/model_budget.json` records this plan. It is not an automatic router, sweep
runner, or spending-limit configuration. Small logged live development pilots have
begun; Qwen encountered upstream rate limits and Gemma was selected for the smoke test.
All verifier arms in a comparison use the same model. Keep observed costs separate
from conservative unknown-charge reserves and any unrelated prior account usage.
