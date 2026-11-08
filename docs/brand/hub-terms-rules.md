# Distinctive words of a run: the rule

**Status:** Phase 2.3.1, plan 02 (2026-11-08). Owner brief of 2026-11-08: the figures of the hub show the core of each lead, built from the run's own record text. Source of the parameters: the owner brief and the prototype build script. Owner ruling R-01 applies: the session decisions overrule the mos-brand book where they conflict.

**Code:** `src/mindrian_eureka/hub/terms.py`. **Tests:** `tests/test_hub_terms.py`.

## What the words are

Every record of a run gets its 5 most distinctive words. Every pair of records gets the words that both records share, at most 6.

A distinctive word is a word that is frequent in this record and rare in the other records of the same run. The count is made once, at build time, from the record text that the run already holds. It uses the standard library only. No model, no clock, no random source, no network and no file is read.

The same records give the same lists, byte for byte, on every computer.

## The rule

1. The text of a record is its title, one space, its text.
2. Tokens. Lower-case the text. Match the regular expression `[a-z][a-z-]{3,}` (a letter, then 3 or more letters or hyphens). Strip hyphens from both ends. Fold the plural (step 3). Drop a token that is in the stop list or has 3 letters or fewer.
3. Fold, in this order, for a token of the length shown. Ends with `ies` and length above 5: replace `ies` by `y`. Else ends with `ses`, `xes`, `zes`, `ches` or `shes` and length above 5: drop `es`. Else ends with `s`, not with `ss`, `us` or `is`, and length above 4: drop `s`. So `programs` gives `program`, `properties` gives `property`, `classes` gives `class`, `calculus` stays `calculus` and `analysis` stays `analysis`.
4. Weight. For record r and word w: `score = tf * idf`, with `idf = log((N + 1) / (df + 0.5))`. `tf` is the count of w in the tokens of r. `df` is the number of records whose tokens hold w. `N` is the number of records of the run. The logarithm is the natural one.
5. Order. Round every score to 9 decimals. Sort the words of r by the rounded score, highest first, then by the word. The first 5 are the distinctive words of r. The first 30 are the depth list of r.
6. Shared words of a pair of records a and b. Take the words that are in the depth list of both. Sort by the larger of the two ranks (0 is first), then by the word. Keep at most 6.

The numbers 5, 30 and 6 and the formula of step 4 come from the owner brief. Any change of a number or of the stop list changes the golden lists and needs a recorded reason.

## Stop list

The stop list is fixed, lower case, with no hyphen, and holds 180 words or fewer. Today it holds 160 words:

a about above after again all also an and any are as at be because been before being between both but by can could did do does doing down during each few for from further had has have having he her here hers him his how i if in into is it its just may more most much must no nor not now of off on once only or other our out over own same she should so some such than that the their them then there these they this those through to too under until up use used uses using very was we were what when where which while who whom why will with would you your paper papers show shows shown present presents propose proposed approach method methods result results based new however thus one two three first second via within without cannot study studies work works given general case cases number set sets problem problems model models

A word that folds into a stop word is dropped too. So `studies` folds to `study` and gives no word.

## Why the 9 decimals

A float holds about 15 to 17 significant digits. Two computers can differ in the last bit of a logarithm. Without rounding, that last bit could swap two words of equal weight and change a list. The scores are rounded to 9 decimals before the sort. 9 decimals is far above any platform difference and far below any real gap between two scores. A test proves that two scores that differ by one part in a million million sort by the word, not by the difference.

## What the words are not

- The words are a screening aid. They help a person decide where to start reading. They are not evidence.
- They are not a summary of the record and not a topic model.
- They make no claim of novelty, demand or value.
- A shared word does not mean the two records work together. It means both records use that word more than the rest of the run does.
- Every pair stays labelled "candidate, not verified" on the page that shows the words.

## Limits

- English letters only. A record written in another script gives no word, and its list is empty. The page says so.
- The folding is light and mechanical. `analyses` and `analysis` stay two words. The `es` fold cuts a word that ends in `ses` too short: `clauses` gives `claus` and `phases` gives `phas`. A word of 5 letters is not cut by the `es` fold, so `boxes` gives `boxe`. A final `s` after a consonant is cut even when it is not a plural, so `canvas` gives `canva`. These are recorded limits of the rule, not goals. The rule is not changed for them, so the golden lists stay stable.
- A word is distinctive in this run, not in general. A word that is rare in this collection of 36 records can be common elsewhere.
- Two long records with one shared rare word can look alike without being alike. Read both records.
- A single-letter or short token (3 letters or fewer) is never a word, so an acronym of 3 letters is not shown.

## Privacy

The words are derived from the record text. They sit in the hub payload next to the record text and nowhere else. In a locked hub they are encrypted with the rest of the payload. The build writes no extra file for them.

## Book status

Book silent, proposed segment: distinctive words. A deterministic word list made from the records of a run, with the rule printed. Proposal: the rule of this file. The status of this segment is book silent, proposed segment, until the book adopts or rejects it.

Brand rule 5 (keep facts and proposed connections distinct) and brand rule 15 (highlighting never upgrades evidence status) apply. The words are shown as a reading aid next to the label "candidate, not verified". No book write command ran for this file (owner ruling R-01; the brand-lock reconciliation is not approved).

## Tests

- `tests/test_hub_terms.py` pins the token rule, the fold, the stop list, the formula, the tie rule, the rounding, the shared words, the depth of 30, the shape of the result, the determinism, hostile text and a timing print for 2000 records.
- `tests/fixtures/hub_terms/records-top5.json` holds the 5 words of every record of the public fixture run. `tests/fixtures/hub_terms/pairs-shared.json` holds the shared words of every pair of both engines. Sorted keys, one line for each key.
- To rewrite a golden on purpose: delete the two files, run the test file with `EUREKA_WRITE_TERM_GOLDENS=1`, read the new lists, and commit them with the reason in the commit message. The test fails with "golden written, review it" when it writes, so a rewrite is never silent.
