# Hub vendor and asset record

## Approval

Date: 2026-10-24.
Status: approved.
The owner answered "approve" to the Plan 06 gate covering npm `3d-force-graph@1.79.1` and PyPI `cryptography>=44,<51` as the optional `hub-gate` extra.
The owner did not describe individual checks. This record does not claim those checks were performed by the owner. Package metadata, integrity and licenses are checked below during implementation.
Approval was written before any package download or dependency declaration in Plan 06.

## Book asset sources

Book commit: `9f4ee34`. Copy date: 2026-10-24. Every copied file was compared byte for byte with its canonical source. `mos-brand doctor` returned PASS.

| Output | Book source | SHA-256 | Method |
|---|---|---|---|
| `tokens.css` | `segments/foundations/tokens/entries/2026-10-19/asset-b1c43da20b.css` | `28f12859744dc738cdddd593a1f5ab72119f6914166b4ec74d309df62ff1dc7b` | CLI |
| `assets/fonts/Figtree-variable.woff2` | `segments/foundations/typography/figtree/entries/2026-10-19/asset-16fa7737d0.woff2` | `4ba7d3d096695818fe0686be4f1e82c6b05134e18a22260336130335027462dd` | CLI |
| `assets/fonts/DM-Sans-variable.ttf` | `segments/foundations/typography/dm-sans/entries/2026-10-19/asset-a9d9a51c0c.ttf` | `8cd08d97e89c24d0aa92edd2f0f4c8ee6195eee9b7c9f154865a58b02f0c1c0d` | CLI |
| `assets/fonts/JetBrains-Mono-variable.ttf` | `segments/foundations/typography/jetbrains-mono/entries/2026-10-19/asset-59e37f3e22.ttf` | `48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda` | CLI |
| `assets/fonts/Heebo-variable.ttf` | `segments/foundations/typography/heebo/entries/2026-10-19/asset-26ff41b9d0.ttf` | `18f930b583fa8fe6b40b2f8263b7ac6afbac07adc91a12467874e7467d3ace30` | CLI |
| `assets/fonts/figtree-OFL.txt` | `segments/foundations/typography/figtree/entries/2026-10-19/asset-982863a066.txt` | `bdc70a7c46c8afbe40b21d2b44a92f52b9aace8ede244804f38c83db61fb9220` | CLI |
| `assets/fonts/dmsans-OFL.txt` | `segments/foundations/typography/dm-sans/entries/2026-10-19/asset-a43d992a30.txt` | `c6da9ab29436871bd4347b70607cf2fb2ab82a926a4afe84da0e7a02de4a189e` | CLI |
| `assets/fonts/jetbrainsmono-OFL.txt` | `segments/foundations/typography/jetbrains-mono/entries/2026-10-19/asset-ff0057ecb6.txt` | `25a5447330f5ce68637e21e6d200f4564ae92a7614accb4b8a79bc51a98720ad` | CLI |
| `assets/fonts/heebo-OFL.txt` | `segments/foundations/typography/heebo/entries/2026-10-19/asset-c7b64fae0a.txt` | `90041d940cac91091b10132d40e727095b62e90e8c3aff9878fdb2268c7cc64f` | CLI |
| `assets/brand/mos-lockup-paper-v2.svg` | `segments/identity/logo/variants/entries/2026-10-19/asset-dc83869aa5.svg` | `028ffd9040e769684c78767b890175bf1b2734e7bd0a4bbf953de38051ba4477` | CLI |
| `assets/faces/theo-handover.svg` | `segments/identity/theo/states/handover/entries/2026-10-19/asset-0af6d74d8a.svg` | `b75f10a9da8d93d9cffc5d01b07c2aadd36d04d586e24e05abbe726b5df622a1` | plain copy after CLI refusal |
| `assets/faces/theo-limit.svg` | `segments/identity/theo/states/limit/entries/2026-10-19/asset-405e3aa366.svg` | `4eb4f93af9fe84399b9758c10ada7fad9650932ac88e11ac10c2ab8362c3261a` | plain copy after CLI refusal |
| `assets/faces/theo-boundary.svg` | `segments/identity/theo/states/boundary/entries/2026-10-19/asset-7c79733ea9.svg` | `71c02c9510bac750821e7587e668543f8b51498b80c57b6feb9b08f92686be2c` | plain copy after CLI refusal |
| `assets/faces/theo-rest.svg` | `segments/identity/theo/states/rest/entries/2026-10-19/asset-b27be39aab.svg` | `63517ad7dbf21399b8e3db9144eda9bed743a14b604df99d4b4cab43a5d3b832` | plain copy after CLI refusal |
| `assets/favicon.svg` | `segments/identity/logo/variants/entries/2026-10-19/asset-6b6bb25f85.svg` | `740dc879b95b4e66813f332833fcb530bf1612fb045831b24a6f38a5ecc87e81` | CLI |
| `assets/favicon-16.png` | `segments/identity/logo/variants/entries/2026-10-19/asset-e062595916.png` | `418af6f5fb7019293a7f3245471548f6cad7cfe139aed8513adda281aa4c8458` | CLI |
| `assets/favicon-32.png` | `segments/identity/logo/variants/entries/2026-10-19/asset-95ebe29cff.png` | `4be8387cec69767d5bfc5926f837174813e5aeae914afa29e850a0dab416b2f1` | CLI |
| `assets/favicon-48.png` | `segments/identity/logo/variants/entries/2026-10-19/asset-0b8f6f83e5.png` | `bb4c9ea8875104981d26a9882fbf7f412359c1f46cf93b81442d06a33e514903` | CLI |
| `assets/favicon-180.png` | `segments/identity/logo/variants/entries/2026-10-19/asset-7500ef54f7.png` | `d63554adee05397dec9b18bf298c507354b340682de7395ebb4992b5686ea7cb` | CLI |

## Copy commands

```sh
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/tokens/entries/2026-10-19/asset-b1c43da20b.css --to src/mindrian_eureka/hub/assets/static/tokens.css
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/figtree/entries/2026-10-19/asset-16fa7737d0.woff2 --to src/mindrian_eureka/hub/assets/static/assets/fonts/Figtree-variable.woff2
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/dm-sans/entries/2026-10-19/asset-a9d9a51c0c.ttf --to src/mindrian_eureka/hub/assets/static/assets/fonts/DM-Sans-variable.ttf
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/jetbrains-mono/entries/2026-10-19/asset-59e37f3e22.ttf --to src/mindrian_eureka/hub/assets/static/assets/fonts/JetBrains-Mono-variable.ttf
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/heebo/entries/2026-10-19/asset-26ff41b9d0.ttf --to src/mindrian_eureka/hub/assets/static/assets/fonts/Heebo-variable.ttf
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/figtree/entries/2026-10-19/asset-982863a066.txt --to src/mindrian_eureka/hub/assets/static/assets/fonts/figtree-OFL.txt
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/dm-sans/entries/2026-10-19/asset-a43d992a30.txt --to src/mindrian_eureka/hub/assets/static/assets/fonts/dmsans-OFL.txt
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/jetbrains-mono/entries/2026-10-19/asset-ff0057ecb6.txt --to src/mindrian_eureka/hub/assets/static/assets/fonts/jetbrainsmono-OFL.txt
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/foundations/typography/heebo/entries/2026-10-19/asset-c7b64fae0a.txt --to src/mindrian_eureka/hub/assets/static/assets/fonts/heebo-OFL.txt
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/logo/variants/entries/2026-10-19/asset-dc83869aa5.svg --to src/mindrian_eureka/hub/assets/static/assets/brand/mos-lockup-paper-v2.svg
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/theo/states/handover/entries/2026-10-19/asset-0af6d74d8a.svg --to src/mindrian_eureka/hub/assets/static/assets/faces/theo-handover.svg
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/theo/states/limit/entries/2026-10-19/asset-405e3aa366.svg --to src/mindrian_eureka/hub/assets/static/assets/faces/theo-limit.svg
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/theo/states/boundary/entries/2026-10-19/asset-7c79733ea9.svg --to src/mindrian_eureka/hub/assets/static/assets/faces/theo-boundary.svg
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/theo/states/rest/entries/2026-10-19/asset-b27be39aab.svg --to src/mindrian_eureka/hub/assets/static/assets/faces/theo-rest.svg
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/logo/variants/entries/2026-10-19/asset-6b6bb25f85.svg --to src/mindrian_eureka/hub/assets/static/assets/favicon.svg
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/logo/variants/entries/2026-10-19/asset-e062595916.png --to src/mindrian_eureka/hub/assets/static/assets/favicon-16.png
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/logo/variants/entries/2026-10-19/asset-95ebe29cff.png --to src/mindrian_eureka/hub/assets/static/assets/favicon-32.png
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/logo/variants/entries/2026-10-19/asset-0b8f6f83e5.png --to src/mindrian_eureka/hub/assets/static/assets/favicon-48.png
node ~/mos-brand/bin/mos-brand.cjs asset --source segments/identity/logo/variants/entries/2026-10-19/asset-7500ef54f7.png --to src/mindrian_eureka/hub/assets/static/assets/favicon-180.png
```

## Book-silent asset-copy exceptions

- `assets/faces/theo-handover.svg`: CLI refusal: "Source must be a canonical artifact selected for this consumer". Copied unchanged from `segments/identity/theo/states/handover/entries/2026-10-19/asset-0af6d74d8a.svg`. SHA-256: `b75f10a9da8d93d9cffc5d01b07c2aadd36d04d586e24e05abbe726b5df622a1`. Proposed segment: permit these canonical state assets in the resolved app-ui packet.
- `assets/faces/theo-limit.svg`: CLI refusal: "Source must be a canonical artifact selected for this consumer". Copied unchanged from `segments/identity/theo/states/limit/entries/2026-10-19/asset-405e3aa366.svg`. SHA-256: `4eb4f93af9fe84399b9758c10ada7fad9650932ac88e11ac10c2ab8362c3261a`. Proposed segment: permit these canonical state assets in the resolved app-ui packet.
- `assets/faces/theo-boundary.svg`: CLI refusal: "Source must be a canonical artifact selected for this consumer". Copied unchanged from `segments/identity/theo/states/boundary/entries/2026-10-19/asset-7c79733ea9.svg`. SHA-256: `71c02c9510bac750821e7587e668543f8b51498b80c57b6feb9b08f92686be2c`. Proposed segment: permit these canonical state assets in the resolved app-ui packet.
- `assets/faces/theo-rest.svg`: CLI refusal: "Source must be a canonical artifact selected for this consumer". Copied unchanged from `segments/identity/theo/states/rest/entries/2026-10-19/asset-b27be39aab.svg`. SHA-256: `63517ad7dbf21399b8e3db9144eda9bed743a14b604df99d4b4cab43a5d3b832`. Proposed segment: permit these canonical state assets in the resolved app-ui packet.
