"""The copy deck of the opportunity hub.

Every user-visible string of UI-SPEC section 9 lives here under its copy-deck ID. An ID
with several strings uses dotted keys, for example `G01.bank`. A slot is written
`{name}` and is filled by `fill`. The deck holds ASCII characters only, no dash
characters and no internal engine names.

Import rule: the standard library, `..run.contracts` and `.contracts` only.
"""

from __future__ import annotations

import re

from ..run.contracts import LABEL, UNUSUAL_PAIRS_NAME, WORDING_AND_MEANING_NAME
from .contracts import js_assignment

# The slot names that the deck may use. `fill` refuses any other name.
SLOT_NAMES: frozenset[str] = frozenset(
    {
        "x",
        "y",
        "z",
        "n",
        "a",
        "b",
        "ID",
        "title",
        "k",
        "i",
        "list",
        "reason",
        "version",
        "fingerprint",
        "records",
        "engine",
        "floor",
        "floor_unusual_pairs",
        "floor_wording_and_meaning",
    }
)

_SLOT = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

DECK: dict[str, str] = {
    # --- 9.1 Global ---------------------------------------------------------
    "G01.bank": "Opportunity bank | MindrianOS Eureka",
    "G01.graph": "Connection graph | MindrianOS Eureka",
    "G01.catalogue": "Catalogue | MindrianOS Eureka",
    "G01.locked": "Locked | MindrianOS Eureka",
    "G02": "Skip to the results",
    "G03": "MindrianOS Eureka",
    "G03.lockup_alt": "MindrianOS",
    "G04": "Opportunity hub",
    "G05": "This page runs from local files. It sends nothing over the internet.",
    "G06": "Your results are ready to review. They are candidates, not verified.",
    "G07": (
        "A pair means two records read alike in one way and differently in another. "
        "It does not mean anything is new, wanted or valuable."
    ),
    "G08": LABEL,
    "G09.bank.short": "Bank",
    "G09.bank.long": "Opportunity bank",
    "G09.graph.short": "Graph",
    "G09.graph.long": "Connection graph",
    "G09.catalogue.short": "Catalogue",
    "G09.catalogue.long": "Catalogue",
    "G10": "Views",
    "G11.records": "Records in the collection",
    "G11.unusual_pairs": "Pairs, unusual-pairs engine",
    "G11.wording_and_meaning": "Pairs, wording engine",
    "G11.hoods": "Neighborhoods",
    "G12": "Search, filters and the map need JavaScript. The lists on this page still work.",
    "G13": "This page needs JavaScript to unlock. Turn it on, then reload.",
    "G14": (
        "Made with MindrianOS Eureka {version}. Run fingerprint {fingerprint}. "
        "{records} records read. Every result on this page is a "
        + LABEL
        + ", and needs human review."
    ),
    "G15.unusual_pairs": UNUSUAL_PAIRS_NAME,
    "G15.unusual_pairs.short": "Unusual-pairs engine",
    "G15.wording_and_meaning": WORDING_AND_MEANING_NAME,
    "G15.wording_and_meaning.short": "Wording engine",
    "G16": "Scores are a screening signal. They do not show novelty, evidence, demand or value.",
    # --- 9.2 Opportunity bank -----------------------------------------------
    "B01": "Which pairs should a person look at first?",
    "B02": "The top pairs come first. Open one to see why it ranks here.",
    "B03.legend": "Show pairs from",
    "B03.both": "Both engines",
    "B03.unusual_pairs": "Unusual-pairs engine",
    "B03.wording_and_meaning": "Wording engine",
    "B04.summary": "What are the two engines?",
    "B04.body": (
        f"Unusual-pairs engine: {UNUSUAL_PAIRS_NAME}. "
        f"Wording engine: {WORDING_AND_MEANING_NAME}. "
        "Both rank a pair by how far its wording score and its meaning score disagree."
    ),
    "B05": (
        "Pairs below the cut-off are hidden. "
        "Cut-off: {floor_unusual_pairs} for the unusual-pairs engine, "
        "{floor_wording_and_meaning} for the wording engine."
    ),
    "B05.one.unusual_pairs": "Cut-off: {floor} for the unusual-pairs engine.",
    "B05.one.wording_and_meaning": "Cut-off: {floor} for the wording engine.",
    "B06": "This engine has no cut-off in this run.",
    "B07": "Show weaker pairs",
    "B08.rank": "Rank {n}",
    "B08.wording": "Wording score {x}",
    "B08.meaning": "Meaning score {y}",
    "B08.rank_score": "Rank score {z}",
    "B08.read": "Read this pair",
    "B08.source_name": "Source record {ID}: {title}",
    "B09.more": "Show 25 more pairs",
    "B09.status": "Showing {a} of {b} pairs.",
    "B10": "No pairs found in this run",
    "B11": (
        "The engines did not rank any pair for this collection. "
        "That does not mean the records have nothing in common. "
        "Read the engine notes below."
    ),
    "B12": "No pairs match this filter",
    "B13.body": "Show both engines, or show weaker pairs.",
    "B13.button": "Show both engines",
    "B14": "The full list is in the file ranked-pairs.md in your run folder.",
    "B15.legend": "Show pairs of class",
    "B15.all": "All classes",
    "B15.cross": "Open next to licensed",
    "B15.open_open": "Both open",
    "B15.licensed_licensed": "Both licensed",
    "B16.label": "Start a room from this pair",
    "B16.hint": (
        "Copy the command under a pair and run it in a terminal. "
        "Replace RUN_FOLDER with your run folder. "
        "The command writes a new folder that MindrianOS can open as a room. "
        "It changes no room."
    ),
    # --- 9.3 Connection graph -----------------------------------------------
    "Gr01": "Who sits next to whom, and where might the next lead be?",
    "Gr02": (
        "Each ball is a record. A line is a proposed pair. "
        "A pair means two records read alike in one way and differently in another. "
        "Yellow marks a record with top pairs into two or more neighborhoods. "
        "It is a place to look, not a result."
    ),
    "Gr03.record": "Record. Its tint shows its neighborhood.",
    "Gr03.eureka": "Potential eureka. Top pairs into two or more neighborhoods.",
    "Gr03.unusual_pairs": "Proposed pair, unusual-pairs engine.",
    "Gr03.wording_and_meaning": "Proposed pair, wording engine.",
    "Gr03.crossing": "Pair that crosses neighborhoods. Drawn thicker.",
    "Gr03.selected": "Selected record. Ringed.",
    "Gr04.label": "Find a record",
    "Gr04.placeholder": "ID, title word or text word",
    "Gr04.button": "Find",
    "Gr04.count": "{n} matches.",
    "Gr04.none": "No match. Try an ID or a word.",
    "Gr05.tour": "Show me the potential eurekas",
    "Gr05.next": "Next potential eureka ({i} of {n})",
    "Gr05.reset": "Reset view",
    "Gr05.zoom_in": "Zoom in",
    "Gr05.zoom_out": "Zoom out",
    "Gr05.show_guide": "Show the guide",
    "Gr05.hide_guide": "Hide the guide",
    "Gr06": (
        "Drag to turn. Scroll or pinch to zoom. Right-drag to pan. Select a ball to read it. "
        "The zoom buttons and the lists work without a mouse."
    ),
    "Gr07": (
        "A line does not mean the records work together, that anyone wants them or that "
        "they are worth money. Every pair here is a candidate for human review."
    ),
    "Gr08": "{n} records are in no pair, so they are not drawn. Find them in the catalogue.",
    "Gr09": "No record in this run has top pairs into two or more neighborhoods.",
    "Gr10": "This collection is small, so a diagram shows it better than a 3D map.",
    "Gr11": "Building the map.",
    "Gr12": "The 3D map cannot start on this device. Here are the same pairs as a list.",
    "Gr13": (
        "Interactive 3D map of records and proposed pairs. "
        "Use Find a record, the zoom buttons or the list of pairs to read it without the map."
    ),
    "Gr14.sphere": "{ID} | {title}",
    "Gr14.hood": "Neighborhood {k}",
    "Gr14.bridge": "Potential eureka",
    "Gr14.line": "Proposed pair, {engine}, rank score {z}. " + LABEL + ".",
    "Gr15": "Potential eureka {ID}",
    "Gr16": "Pairs in this map",
    "Gr17": "Nothing to draw yet",
    "Gr18": (
        "A map needs at least one pair. This run has none. "
        "The engine notes are in the Opportunity bank."
    ),
    "Gr19": (
        "A neighborhood is a group of records that link to each other more than to the rest. "
        "The hub groups them from the pair links."
    ),
    # --- 9.4 Catalogue ------------------------------------------------------
    "C01": "What is in the collection?",
    "C02": "Every record in the collection, with the file it came from.",
    "C03.label": "Search the collection",
    "C03.placeholder": "ID, title word or text word",
    "C04.file.label": "Source file",
    "C04.file.all": "All files",
    "C04.pair.label": "Appears in a pair",
    "C04.pair.any": "Any",
    "C04.pair.some": "In at least one pair",
    "C04.pair.none": "In no pair",
    "C05": "Showing {a} of {b} records.",
    "C06.id": "ID",
    "C06.title": "Title",
    "C06.file": "Source file",
    "C06.pairs": "Pairs",
    "C06.n_pairs": "{n} pairs",
    "C06.one_pair": "1 pair",
    "C06.no_pairs": "No pairs",
    "C07": "Read {ID}",
    "C08": "No records match",
    "C09.body": "Clear the search or a filter.",
    "C09.button": "Clear search and filters",
    "C10": "Show 50 more records",
    "C11": "The full catalogue is in corpus/records.jsonl in your run folder.",
    # --- 9.5 Reading panel --------------------------------------------------
    "P01.heading": "Nothing selected",
    "P01.body": "Select a record or a pair to read it here.",
    "P02.close": "Close",
    "P02.close_name": "Close the panel",
    "P02.record": "Selected record",
    "P02.pair": "Selected pair",
    "P03.source": "Where it comes from",
    "P03.text": "Text of the record",
    "P03.hood": "Neighborhood",
    "P03.check": "Data check for this record",
    "P03.pairs": "Pairs with other records ({n})",
    "P03.why": "Why this is a potential eureka",
    "P03.two": "The two records",
    "P03.scores": "Scores",
    "P03.reading": "How the engine reads it",
    "P03.meaning": "What the scores mean",
    "P04.file": "Source file",
    "P04.ref": "Source reference",
    "P05.open": "Open source record",
    "P05.catalogue": "Open in the catalogue",
    "P05.full": "Show full text",
    "P05.read_pair": "Read this pair",
    "P05.read": "Read {ID}",
    "P06.source": "From the source",
    "P06.inferred": "Inferred",
    "P06.proposed": "Proposed",
    "P06.eureka": "Potential eureka",
    "P06.hidden": "Hidden by default",
    "P07": (
        "This record has top pairs into {n} neighborhoods: {list}. "
        "That makes it a place to look. It is not a result."
    ),
    "P08": "Neighborhood {k}, {n} records",
    "P09.identical": "Identical text to {ID}",
    "P09.no_text": "No text",
    "P10.cross": "Open next to licensed",
    "P10.open_open": "Both open",
    "P10.licensed_licensed": "Both licensed",
    # --- 9.6 Data check -----------------------------------------------------
    "D01": "Data check",
    "D02.same": "Records with the same text as another record: {n}.",
    "D02.empty": "Records with no text: {n}.",
    "D02.removed": "Records removed before ranking: {n}. {reason}.",
    "D02.boilerplate": "Shared boilerplate text: not checked in this run.",
    "D03": (
        "A copy scores as a near-perfect pair and can look like a discovery. "
        "A pair that involves a copy carries a flag."
    ),
    # --- 9.7 Locked and error states ----------------------------------------
    "L01": "This hub is locked",
    "L02": (
        "The results are stored scrambled in this file. Type the passphrase to open them. "
        "The check happens on this computer. Nothing is sent anywhere."
    ),
    "L03.label": "Passphrase",
    "L03.show": "Show passphrase",
    "L03.hide": "Hide passphrase",
    "L03.unlock": "Unlock",
    "L04": "Checking the passphrase.",
    "L05": "That passphrase did not open the file. Check it and try again.",
    "L06": "This browser cannot unlock the file. Open the page in a current browser.",
    "L07": (
        "This protects the file when it is stored. "
        "It does not protect a computer that already has the passphrase."
    ),
    "L08": "The file is damaged or was changed. Build the hub again.",
    "E01": "The hub data did not load",
    "E02": (
        "Keep hub-data.js in the same folder as hub.html and open hub.html again. "
        "If that does not help, run eureka hub again."
    ),
    "E03": "This hub file is from a different version",
    "E04": "Build the hub again with the current version of MindrianOS Eureka.",
    "E05": "No record has the ID {ID}. Check the ID or search for a word.",
}


def fill(text: str, **values: object) -> str:
    """Fill the `{name}` slots of a deck string.

    The function does one pass over the text, so a value that holds `{x}` is not
    filled again. It never uses `str.format`, so a value cannot reach the format syntax.

    Args:
        text: A deck string.
        **values: The value of each slot. Each value is converted with `str`.

    Returns:
        The text with every slot replaced.

    Raises:
        ValueError: The text holds a slot name that the deck does not know.
        KeyError: The text holds a known slot and no value was given for it.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in SLOT_NAMES:
            raise ValueError(f"unknown slot name: {name}")
        if name not in values:
            raise KeyError(name)
        return str(values[name])

    return _SLOT.sub(replace, text)


def deck_js_bytes() -> bytes:
    """Return `hub-copy.js`: the deck as `window.HUB_COPY`.

    Returns:
        The same bytes on every call.
    """
    return js_assignment("HUB_COPY", DECK, digits=None)
