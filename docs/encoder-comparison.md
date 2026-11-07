# Encoder comparison on the 36-record example

Label: candidate, not verified. This page compares text encoders on one small public example. It does not change the default encoder.

## What this compares

The example is the 36 records of `examples/public-example/reference-run/corpus/records.jsonl`. The text is CC0. The source is in `tests/fixtures/hub_public/SOURCE.md`.

The page compares three encoders:

- MiniLM, the profile `cpu-default`. It is the default encoder today.
- `mdbr-leaf-ir`, a small model that the JHTV replay used.
- Nemotron-3-Embed-1B-BF16, the profile `gpu-nemotron`. It needs a GPU.

The measure is the dense top-200 of the 630 pairs of the 36 records. A pair is two records. Each encoder gives each record one vector. The 200 pairs with the highest cosine make the dense top-200 of that encoder. The overlap of two encoders is the share of the 200 pairs that both lists hold. An overlap of 1.0000 means the same 200 pairs. An overlap near 0 means that the two encoders find different pairs.

The page also shows the vector width, the load time and the texts for each second.

## How it was measured

The script is `scripts/encoder-compare.py`. It makes no network call. The log of the run on this computer is `docs/encoder-evidence/cpu-compare-log.json`. The table below is rendered from that log by the script. A test holds the table equal to the render of the log. No number on this page is typed by hand.

The CPU part ran on this computer: a Linux computer with an aarch64 processor, no GPU. The run used 1 thread and the lowest priority. The log holds the thread count, the load time and the three timings.

The encoding rule is the same rule that the owner-run spike (`scripts/encoder-spike.py`) uses. Each text goes through one model call. There is no token-window chunking. The model text is the title, a blank line and the text, stripped. The vectors are normalized to length 1 in float32. A text that is longer than the model window is cut by the model at its window. The table shows the longest text in tokens next to the model window.

This rule differs from the chunked rule of `eureka run`, which cuts a long text into windows and takes the mean. The rule here keeps the CPU vectors and the GPU vectors comparable. The saved vectors are in `docs/encoder-evidence/minilm-cpu-vectors.npz`. The file holds the record ids, the vectors, the fingerprint of the encoder setup and the encoding rule. A test checks that the layout agrees with what the spike script reads.

## Results

<!-- compare-table:start -->
| Measure | MiniLM (cpu-default) | mdbr-leaf-ir | Nemotron-3-Embed-1B-BF16 | Source |
| --- | --- | --- | --- | --- |
| Status | run | NOT RUN | NOT RUN | `columns.*.status` |
| Vector width | 384 | NOT RUN | NOT RUN | `columns.*.dimension` |
| Load time (seconds) | 2.24 | NOT RUN | NOT RUN | `columns.*.load_seconds` |
| Texts for each second (indicative) | 30.90 | NOT RUN | NOT RUN | `columns.*.texts_per_second` |
| Longest text (tokens) | 328 | NOT RUN | NOT RUN | `columns.*.max_tokens` |
| Model window (tokens) | 256 | NOT RUN | NOT RUN | `columns.*.window_tokens` |
| Load average, 1 minute, before the timing | 0.52 | NOT RUN | NOT RUN | `columns.*.loadavg_before` |
| Load average, 1 minute, after the timing | 0.52 | NOT RUN | NOT RUN | `columns.*.loadavg_after` |
| Dense top-200 overlap with MiniLM | 1.0000 | NOT RUN | NOT RUN | `overlap.*.minilm` |
| Dense top-200 overlap with mdbr-leaf-ir | NOT RUN | NOT RUN | NOT RUN | `overlap.*.mdbr_leaf_ir` |
| Dense top-200 overlap with Nemotron | NOT RUN | NOT RUN | NOT RUN | `overlap.*.nemotron` |
<!-- compare-table:end -->

NOT RUN means that no run produced the value. The reasons:

- `mdbr-leaf-ir`: the folder `~/.mindrian/model-cache/MongoDB/mdbr-leaf-ir` holds ONNX files only. It has no `modules.json` and no weight file of the form that sentence-transformers reads. The script does not install `onnxruntime` and does not open the ONNX file, because that is another vector path and a new dependency. The reason text is in the log under `columns.mdbr_leaf_ir.reason`.
- Nemotron: the model needs a computer with a GPU. This session cannot reach one. The reason text is in the log under `columns.nemotron.reason`.

The timings are indicative. Other work may run on the computer. The log records the load average before and after the timing, and the table shows both values.

## What the numbers do not show

- The overlap is not a quality verdict. No human rated these pairs. Two encoders can share many pairs and both be wrong, or share few and both find good leads.
- The published scores of the models are on other tasks. They do not say which model finds better pairs in the Eureka engines.
- The example has 36 short public records. It does not show the cost or the behavior for long texts or for a large collection.
- The timings come from one CPU computer under an unknown load. They do not say how fast a GPU is.
- The engine-level result is not here. The script can compare the pair lists of a finished `eureka run` folder with the shipped reference run (`--engine-run`). That needs a run by the owner.
- Every result keeps the label candidate, not verified.

## Next step and who decides

The owner decides any change of the default encoder from the finished table. This page and this plan change no default.

To fill the Nemotron column:

1. Run the plan 05-08 spike on the GPU computer. Follow `docs/encoder-spike-results.md`.
2. Copy `nemotron-bf16-vectors.npz` to `docs/encoder-evidence/`.
3. Run the script without a model, so that the MiniLM timings of this page stay as they are:
   `python3 scripts/encoder-compare.py --update-log docs/encoder-evidence/cpu-compare-log.json --vectors-in nemotron=docs/encoder-evidence/nemotron-bf16-vectors.npz --out docs/encoder-evidence/compare-log.json --render-page docs/encoder-comparison.md`
4. Run `tests/test_encoder_compare.py`. After step 3 the page follows `docs/encoder-evidence/compare-log.json`, and the tests read that file.

Option: add `--engine-run <folder of a finished eureka run>` to step 3 to record the engine-level overlap for the owner.
