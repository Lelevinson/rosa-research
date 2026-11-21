# Parity integration (weekend 2026-11-21 to 23): research-side pointer

Branch `member/martin-parity` of Lelevinson/rosa-research, created from `8713f9b205033a25f8ed8d9549610e9ad0b8bfde`.
`member/martin` is not modified. No `rosa_auth` file and no credential is changed or added.

The audit, tasks, frozen acceptance criteria and scorer live in **Lelevinson/rosa-evaluation**, branch
`member/martin-parity`: `artifacts/parity-integration-20261121/` (PARITY_AUDIT.md, ACCEPTANCE_CRITERIA.md frozen at
rosa-evaluation commit `8f50101`, PA1_CONDITIONS_2026-11-21.md, PA1_RECLASSIFICATION_2026-11-21.md) and
`tools/parity/`.

## Relation to this repository's native-schema-v1 profile (`8713f9b`, `src/rosa_backends/tool_contract_ollama.py`)

- Granite (PA-1, transport): the parity adapter may append exactly one sentence, byte-identical to
  `NATIVE_GUIDANCE['granite3.3']` here and to IBM's official template (HF commit `51dd4bc2`), SHA-256
  `7e12d9b58f45f60365ccc471bae05c77809f94d8947408becb8bce85f39e624e`.
- Not used: native-schema-v1's extra system message with a copy of the tool schemas, its forced non-streaming
  transport, and its Llama guidance. Llama uses PA-2 instead (an Ollama template fix from Meta's public
  `llama-models` code, same weights blob).
- `ToolContractOllama` stays an opt-in profile; the parity runs do not import it.

## Gate log
- 2026-11-21: branch created; B1 gate (rosa-evaluation `8f50101`); PA-1 reclassified as transport (rosa-evaluation `7d1515d`).
