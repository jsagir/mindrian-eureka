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

## Graph package

Package: `3d-force-graph@1.79.1`. Registry license: MIT. Repository: https://github.com/vasturiano/3d-force-graph. No deprecation field was returned by the registry.

Published: 2026-02-04T20:54:45.679Z. Vendored: 2026-10-24. Age: 262 days, above the 14-day minimum.

Tarball integrity: `sha512-iscIVt4jWjJ11KEEswgOIOWk8Ew4EFKHRyERJXJ0ouycqzHCtWwb9E5imnxS5rYF1f1IESkFNAfB+h3EkU0Irw==`. Check: PASS. Computed SHA-512 equals the fresh npm registry value and the value in hub-probe-results.md. Archive members were listed and checked for absolute paths, parent traversal, links, and special files before extraction. All package downloads used `npm pack --ignore-scripts` in separate empty folders under build/vendor-work. Downloaded code was never executed.

| Packaged file | Bytes | SHA-256 |
|---|---|---|
| `3d-force-graph.min.js` | 1240059 | `fa365edfa625f055982ea9e41feac875bc1c46c6225318c420eed26646e78499` |
| `LICENSE-3d-force-graph.txt` | 1072 | `7262e566e874d1ce8cfadace01d4f635f8d704b6bdf7b4345cc028e5faeafded` |
| `NOTICES.txt` | 55747 | `f4eb589ddf23f95a04e167d599f1ad5756bed090f155ca76b8d1a304c0b50512` |

The page loads this self-contained UMD bundle by relative path and only when the 3D stage is requested. It defines `ForceGraph3D` and has no module export statement. If WebGL or the library fails, the page shows Gr12 and the equivalent pair list. Approval is recorded above.

## Third-party notices

The minified bundle retains no banners matching `@license`, `Released under`, `Copyright`, or `SPDX`. NOTICES.txt retains standalone upstream licenses for all 30 packages identified by the accompanying source map, including ISC and BSD-3-Clause terms. Direct dependency declared ranges and registry license IDs are listed first.

Named license-source releases are the latest stable upstream versions published on or before the graph pin. Their source files were compared with the source map. A matching file confirms source content, but does not prove the original resolver lock.

| Package | License-source version | License | Source files matching |
|---|---|---|---|
| `@babel/runtime` | 7.28.6 | MIT | 9/9 |
| `@tweenjs/tween.js` | 25.0.0 | MIT | 1/1 |
| `accessor-fn` | 1.5.3 | MIT | 1/1 |
| `d3-array` | 3.2.4 | ISC | 2/2 |
| `d3-binarytree` | 1.0.2 | MIT | 13/13 |
| `d3-dispatch` | 3.0.1 | ISC | 1/1 |
| `d3-force-3d` | 3.0.6 | MIT | 8/8 |
| `d3-octree` | 1.1.0 | MIT | 16/16 |
| `d3-quadtree` | 3.0.1 | ISC | 14/14 |
| `d3-scale` | 4.0.2 | ISC | 2/2 |
| `d3-scale-chromatic` | 3.1.0 | ISC | 2/2 |
| `d3-selection` | 3.0.0 | ISC | 48/48 |
| `d3-timer` | 3.0.1 | ISC | 1/1 |
| `data-bind-mapper` | 1.0.3 | MIT | 1/1 |
| `float-tooltip` | 1.7.5 | MIT | 1/1 |
| `internmap` | 2.0.3 | ISC | 1/1 |
| `kapsule` | 1.16.3 | MIT | 1/1 |
| `lodash-es` | 4.17.23 | MIT | 14/14 |
| `ngraph.events` | 1.4.0 | BSD-3-Clause | 0/1 |
| `ngraph.forcelayout` | 3.3.1 | BSD-3-Clause | 11/11 |
| `ngraph.graph` | 20.1.1 | BSD-3-Clause | 0/1 |
| `ngraph.merge` | 1.0.0 | MIT | 1/1 |
| `ngraph.random` | 1.2.0 | BSD-3-Clause | 1/1 |
| `polished` | 4.3.1 | MIT | 1/1 |
| `preact` | 10.28.3 | MIT | 0/1 |
| `style-inject` | 0.3.0 | MIT | 1/1 |
| `three` | 0.182.0 | MIT | 5/13 |
| `three-forcegraph` | 1.43.1 | MIT | 1/1 |
| `three-render-objects` | 1.40.4 | MIT | 1/1 |
| `tinycolor2` | 1.6.0 | MIT | 1/1 |

Gaps: no standalone upstream license file was missing. Exact bundled versions remain unresolved where source files differ:

- ngraph.events: exact bundled version unresolved; upstream license below is from 1.4.0
- ngraph.graph: exact bundled version unresolved; upstream license below is from 20.1.1
- preact: exact bundled version unresolved; upstream license below is from 10.28.3
- three: exact bundled version unresolved; upstream license below is from 0.182.0

## Optional gate dependency

`hub-gate = ["cryptography>=44,<51"]` is an optional extra. The three base dependencies are unchanged. PBKDF2 remains in the standard library; AES-GCM requires this extra. Version 50.0.2 is already present in uv.lock. PyPI identifies its owner as the Python Cryptographic Authority and its license expression as Apache-2.0 OR BSD-3-Clause: https://pypi.org/project/cryptography/50.0.2/. This page was checked on 2026-10-24. No PyPI package was downloaded during this plan.

uv.lock status: updated successfully with `uv lock --offline` (76 packages resolved). No network lock update is needed.
