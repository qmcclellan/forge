# Pinned StarkGrid contract dependency (KS-0006)

This directory vendors a **read-only reference snapshot** of two StarkGrid
artifacts, so Forge's own test suite can prove structural conformance to the
StarkGrid target contract without a live StarkGrid checkout or network
access at test time. This is a **versioned contract dependency**, not
runtime service coupling -- `forge/coder_target.py` itself never reads
anything under this directory; only `tests/test_ks0006_coder_target.py` does.

- **Pinned StarkGrid SHA:** `575130340de3241cac2eeabeaa19192aa0ca302a`
  (`v3.0.0-dev`, the exact SHA `coder-terraform-target-contract-v1.md` and
  `forge-node-dashboard-to-starkgrid-frontend-mapping-v1.md` were authoritative
  at when this converter was implemented against them).
- **Contract version:** `coder-terraform-target-contract/v1`

## Vendored files, with source SHA-256 at the pin point

| file here | source in StarkGrid | sha256 at pin |
|---|---|---|
| `validate-target-contract.sh` | `ops/coder/validate-target-contract.sh` | `e3a4367be9737dff95988cc4b563908f1425329718d7c4fa8860b9e0e23df16c` |
| `expected-node-dashboard-example/main.tf` | `ops/coder/contract-examples/node-dashboard-example/main.tf` | `d968adecec89fbbc2823f77dee026232e738563461c95ad464fae4943d5af5c9` |

`expected-node-dashboard-example/main.tf` is the CONTRACT'S OWN worked
example, used only to prove Forge's generated output is *structurally
equivalent* (same required elements, same resolution of the Node 20/22
discrepancy) -- never copied into the implementation itself. See
`tests/test_ks0006_coder_target.py` for exactly how it is used.

## Re-pinning

If StarkGrid publishes a `coder-terraform-target-contract-v2.md` (this
repository's own convention is a new versioned file, never editing v1 in
place -- see that contract's own "Versions" section), re-vendor these files
from the new authoritative SHA, update the SHA-256 table above, and record
the new pin. Until then, drift between this pin and StarkGrid's live `main.tf`
authoring guidance for v1 is a StarkGrid-side change to an already-versioned
contract, which does not happen without a new version file.
