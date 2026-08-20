# MLAI Protected-File Baseline

Status: Initial baseline recorded before the canonical data-foundation phase.

## Protection policy

The files below are the current analysis foundation. Changes to them must:

1. Preserve the evidence-first and non-signal boundary.
2. Include or update deterministic fixtures and acceptance checks.
3. Keep future outcomes separate from current-state inputs.
4. Update the relevant architecture or contract documentation when behavior
   changes.
5. Recompute this baseline when a milestone intentionally changes a protected
   contract.

These hashes are change-detection anchors, not a replacement for version
control, review, or testing.

## Baseline hashes

| File | SHA-256 |
|---|---|
| `lib/market-engine/src/types.ts` | `30a348a7ec2df040f583e63adecaa653651c8b13b5fb1c7729059317628df15a` |
| `lib/market-engine/src/normalize.ts` | `322e73326a4a8d6855311319aeb8fd32a5fb5b4d03e9ef71669f9843fc4402e8` |
| `lib/market-engine/src/analyze.ts` | `c93a83f7a3994cb012b741cfa38427c1c6e5f117b1d7e6dc4e837426c201baf1` |
| `lib/market-engine/src/index.ts` | `7110784dcbb8bc536e6ef05c2c2f38868e0b3e4876231dfe638224c153c95d6f` |
| `scripts/src/analyze.ts` | `b5a55858dc05d0b3f9d8e1dcf86b5be17fdc02492915cd170043ce081ee000a3` |
| `scripts/src/market-engine.test.ts` | `da3cca788f61df960b63c54786e166a36029802729ade082e9223fbd634bc26c` |
| `scripts/package.json` | `1ac365966f91d4739c919919cb8986cd3bff57efa7b0fd429aa99f3cb181da16` |
| `replit.md` | `58fef664559f7a37fecdcd32df0ce673504880aa69c05da3fcef3c71e3d041be` |
| `docs/MLAI-DATA-CONTRACT.md` | `68ced3a56023a4ccad2e92e5b998fdf9d6b11eda6b79a37136329b729955266e` |
| `docs/MLAI-ARCHITECTURE.md` | `16202b934783435615e7c04d564d1dd82ae4624e2d7b470782119af2a3f43585` |
| `lib/api-spec/openapi.yaml` | `f9ab7c42c1b0ac5c937994943e70ffce6bb728d22ccb7fe7af963939264a82be` |
| `lib/db/src/schema/index.ts` | `459c09e0be1c1e28c794ee70e838f55d0c3d225fa6614fe2d4182a86fbf5e115` |
| `package.json` | `70cea0f4dad2fe6eac92d937b9f09dea474c1f2372d747950885b0875e59d601` |
| `pnpm-lock.yaml` | `017bed96c0e53ad82f5968ac090fe825b672c6ecc687f63d7de0b1620fdcd50d` |

## Reference-document hash

The uploaded planning document is also anchored so that future implementation
work can be compared against the exact roadmap version used for this audit:

| File | SHA-256 |
|---|---|
| `attached_assets/Pasted-MLAI-Market-Language-Brain-Detailed-Architecture-and-De_1786886094881.txt` | `08887b97c0cb486d0b5768074535b7ea9148fc436d91f215915d42990211c8e5` |

## Intentional omissions

Generated `dist/` output, dependency directories, caches, and workflow state are
not protected source-of-truth files. They should be regenerated from the
protected source and lockfile.