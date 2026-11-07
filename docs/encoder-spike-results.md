---
status: not_run
---

# GPU encoder spike: Nemotron-3-Embed-1B-BF16 on the RTX 3060

This page is the record of one run of a local GPU test. The model is `nvidia/Nemotron-3-Embed-1B-BF16`. The computer is the owner's RTX 3060 with 12 GB of memory. Every result is a candidate, not verified.

## Status

Front matter `status: not_run` means that no log from a run has been rendered into this page. Every value in the Results table says NOT RUN until a log exists.

The table in Results is not typed by hand. The script `scripts/encoder-spike.py` writes the log `gpu-spike-log.json`. The same script renders the table from that log with `--render-doc`. A test compares the table with the log, so a value that the log does not hold cannot stay on this page.

Where a cell says NOT RUN, no run produced that value.

## What this proves and what it does not

The run answers a narrow question. Does this model load and embed on one RTX 3060? How much GPU memory and how much time does it take for the 36 short texts of the public example?

The run also reads the facts that the model folder defines: the vector width, the maximum sequence length, the prefix strings, and whether the model needs remote code. It compares the bfloat16 vectors with the float32 vectors on the dense top-200 pairs.

The run does not show quality on the task of Eureka. It does not show the cost for long texts. It does not show anything about another computer. A pass is not a verdict on the default encoder.

The script encodes each text in one model call, with no chunking. The CPU vectors for the optional MiniLM check must come from the same rule. Otherwise the overlap measures the chunk rule and not the GPU.

## How to run

Run these steps on the GPU computer. The scratch environment lives outside the repository.

1. Check each package name on pypi.org before you install it: `https://pypi.org/project/torch/`, `https://pypi.org/project/transformers/`, `https://pypi.org/project/sentence-transformers/`, `https://pypi.org/project/numpy/`, `https://pypi.org/project/huggingface-hub/`. Install only these exact names.
2. Make a scratch environment outside the repository: `python3 -m venv ~/eureka-spike-venv`, then `source ~/eureka-spike-venv/bin/activate`.
3. Install a CUDA build of torch with the selector on pytorch.org. Then run `pip install "transformers>=5.2" "sentence-transformers>=5.4.1" numpy huggingface-hub`.
4. Run `nvidia-smi`. It must show the RTX 3060 inside WSL.
5. Run `python3 scripts/encoder-spike.py --dry-run --out-dir ~/eureka-spike-out` first. It must print the planned steps and write a log with no numbers.
6. Run `python3 scripts/encoder-spike.py --allow-download --out-dir ~/eureka-spike-out`. The first run downloads about 2.3 GB (INFERRED from the size on the model card). If the download asks for a login, the model page may need accepted terms (UNVERIFIED). For the same-model drift run, add `--minilm-dir <MiniLM folder> --cpu-vectors docs/encoder-evidence/minilm-cpu-vectors.npz`.
7. Copy `gpu-spike-log.json` and `nemotron-bf16-vectors.npz` from `~/eureka-spike-out` into `docs/encoder-evidence/` in the repository. Then run `python3 scripts/encoder-spike.py --render-doc docs/encoder-spike-results.md --log docs/encoder-evidence/gpu-spike-log.json`. This command uses only the standard library. It also sets the front matter status.
8. Return the file `gpu-spike-log.json`. If the script stopped, return the log it wrote and the error text.

The script never enables remote code. It refuses an output folder inside the repository.

## Results

<!-- spike-table:start -->
| Measure | Value | Log field |
| --- | --- | --- |
| Python version | NOT RUN | `environment.python` |
| Operating system | NOT RUN | `environment.platform` |
| torch version | NOT RUN | `environment.torch` |
| transformers version | NOT RUN | `environment.transformers` |
| sentence-transformers version | NOT RUN | `environment.sentence_transformers` |
| numpy version | NOT RUN | `environment.numpy` |
| CUDA device found | NOT RUN | `environment.cuda_available` |
| CUDA runtime version | NOT RUN | `environment.cuda_runtime` |
| GPU driver version | NOT RUN | `environment.driver` |
| GPU name | NOT RUN | `environment.gpu_name` |
| GPU memory (GiB) | NOT RUN | `environment.gpu_memory_bytes` |
| Model name | NOT RUN | `model.id` |
| Resolved revision (snapshot commit hash) | NOT RUN | `model.revision` |
| Files in the snapshot | NOT RUN | `model.file_count` |
| Size of the snapshot (GiB) | NOT RUN | `model.total_bytes` |
| Weights in several files | NOT RUN | `model.sharded_weights` |
| Snapshot error | NOT RUN | `model.error` |
| bfloat16 run loads and embeds | NOT RUN | `load.bf16.ok` |
| bfloat16 load time (seconds) | NOT RUN | `load.bf16.seconds` |
| bfloat16 attention setting that worked | NOT RUN | `load.bf16.attention_used` |
| bfloat16 error | NOT RUN | `load.bf16.error` |
| Model needs remote code | NOT RUN | `load.needs_remote_code` |
| float32 run loads and embeds | NOT RUN | `load.fp32.ok` |
| float32 load time (seconds) | NOT RUN | `load.fp32.seconds` |
| float32 error | NOT RUN | `load.fp32.error` |
| Vector width | NOT RUN | `embedding.dimension` |
| Maximum sequence length of the model (tokens) | NOT RUN | `embedding.max_seq_length` |
| Prefix strings defined by the model folder | NOT RUN | `embedding.prompts` |
| Query prefix equals the profile string | NOT RUN | `embedding.query_prefix_confirmed` |
| Document prefix equals the profile string | NOT RUN | `embedding.document_prefix_confirmed` |
| Texts embedded | NOT RUN | `texts.count` |
| Highest token count among the texts | NOT RUN | `texts.max_tokens` |
| bfloat16 texts for each second | NOT RUN | `speed.bf16.texts_per_second` |
| float32 texts for each second | NOT RUN | `speed.fp32.texts_per_second` |
| bfloat16 peak GPU memory (GiB) | NOT RUN | `memory.bf16.peak_allocated_bytes` |
| float32 peak GPU memory (GiB) | NOT RUN | `memory.fp32.peak_allocated_bytes` |
| Top-200 overlap, bfloat16 against float32 | NOT RUN | `drift.bf16_vs_fp32.top200_overlap` |
| Top-200 overlap, MiniLM on the GPU against the CPU vectors | NOT RUN | `drift.minilm_gpu_vs_cpu.top200_overlap` |
<!-- spike-table:end -->

## Decisions that follow from the numbers

The owner takes these decisions after a log exists. None is taken on this page.

- Pin the revision of the `gpu-nemotron` profile in `encoder_spec.py`. Use only the value of `model.revision` from the log.
- Confirm or change the two prefix strings. Use the prefix fields of the log.
- Decide whether a model that needs remote code is acceptable. The plan of this spike says no.
- Decide the overlap threshold of `eureka check-example` for a GPU run. Use the same-model drift fields of the log.
- Decide whether to keep the profile.

Threshold: not set

The owner decides the threshold. It stays unset until the owner reads the drift numbers.

## Next step

After the owner-run, a quick task records the pin and the threshold. The comparison harness then fills the Nemotron column with `--vectors-in nemotron=docs/encoder-evidence/nemotron-bf16-vectors.npz`.
