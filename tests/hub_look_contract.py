"""The look contract of the hub shell (Phase 2.3.1, plan 03, owner decision D-01).

Each `Role` names one visual role of the target stylesheet, the declarations the target
writes for it, the declarations the hub writes for it, and the deviation ids (LD-nn) that
`docs/brand/hub-design-decisions.md` explains where the two differ. `after` names the plan
that fills the row: "03" for the shell rows of this plan, "06" for the row rows of plan 06.

The file holds CSS selectors, properties and values only. It holds no text of the target
page and no name. `tests/test_hub_look_tokens.py` proves the target side against
`evidence/target-site.css` and the hub side against the hub stylesheets.

A target declaration is `(selector, property, value as written)`. A hub declaration is
`(selector, property, {width key: value})` where the width key is `base`, `768` or `1024`
and the value is the text as written in the hub stylesheet, or `None` when the hub must not
declare the property at that width (for example, no `backdrop-filter`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

TargetDecl = tuple[str, str, str]
HubDecl = tuple[str, str, Mapping[str, str | None]]


@dataclass(frozen=True)
class Role:
    id: str
    what: str
    target: tuple[TargetDecl, ...]
    hub: tuple[HubDecl, ...]
    deviation: str | None
    after: str

    def deviations(self) -> tuple[str, ...]:
        if not self.deviation:
            return ()
        return tuple(part.strip() for part in self.deviation.split(","))


def _all(value: str | None) -> dict[str, str | None]:
    return {"base": value}


def _from_768(base: str | None, wide: str | None) -> dict[str, str | None]:
    return {"base": base, "768": wide}


ROLES: tuple[Role, ...] = (
    Role(
        "S01",
        "body size",
        (("body", "font", "17px/1.58 var(--body)"),),
        (("body", "font-size", _from_768("16px", "17px")),),
        "LD-02",
        "03",
    ),
    Role(
        "S02",
        "body line height",
        (("body", "font", "17px/1.58 var(--body)"),),
        (("body", "line-height", _all("1.58")),),
        None,
        "03",
    ),
    Role(
        "S03",
        "sticky header",
        (
            (".site-header", "position", "sticky"),
            (".site-header", "top", "0"),
            (".site-header", "z-index", "20"),
        ),
        (
            ("#hub-header", "position", _all("sticky")),
            ("#hub-header", "inset-block-start", _all("0")),
            ("#hub-header", "z-index", _all("20")),
        ),
        None,
        "03",
    ),
    Role(
        "S04",
        "header minimum height",
        ((".site-header", "min-height", "76px"),),
        (("#hub-header", "min-block-size", {"768": "76px"}),),
        "LD-26",
        "03",
    ),
    Role(
        "S05",
        "header rule",
        ((".site-header", "border-bottom", "1px solid var(--line)"),),
        (("#hub-header", "border-block-end", _all("1px solid var(--hub-line)")),),
        "LD-01",
        "03",
    ),
    Role(
        "S06",
        "header ground",
        (
            (".site-header", "background", "rgba(247,245,238,.96)"),
            (".site-header", "backdrop-filter", "blur(10px)"),
        ),
        (
            ("#hub-header", "background", _all("var(--mos-paper)")),
            ("#hub-header", "backdrop-filter", _all(None)),
        ),
        "LD-08",
        "03",
    ),
    Role(
        "S07",
        "lockup width",
        ((".lockup img", "width", "156px"),),
        (("#hub-header img", "inline-size", _from_768("116px", "156px")),),
        "LD-16",
        "03",
    ),
    Role(
        "S08",
        "context label",
        (
            (".context-label", "font", "600 12px/1.45 var(--mono)"),
            (".context-label", "letter-spacing", ".04em"),
            (".context-label", "color", "var(--blue)"),
        ),
        (
            (".hub-header-label", "font-family", _all("var(--mos-font-code)")),
            (".hub-header-label", "font-size", _all("13px")),
            (".hub-header-label", "font-weight", _all("600")),
            (".hub-header-label", "letter-spacing", _all("0.04em")),
            (".hub-header-label", "color", _all("var(--mos-blue)")),
        ),
        "LD-04",
        "03",
    ),
    Role(
        "S09",
        "context line",
        (
            (".site-context", "font-size", "12px"),
            (".site-context", "line-height", "1.4"),
            (".site-context", "color", "var(--soft)"),
        ),
        (
            (".hub-header-sub", "font-size", _all("13px")),
            (".hub-header-sub", "line-height", _all("1.4")),
            (".hub-header-sub", "color", _all("var(--mos-soft)")),
        ),
        "LD-04",
        "03",
    ),
    Role(
        "S10",
        "nav link",
        (
            (".nav a", "font-size", "12px"),
            (".nav a", "font-weight", "650"),
            (".nav a", "color", "var(--ink)"),
            (".nav a", "text-decoration", "none"),
        ),
        (
            ("#hub-nav a", "font-size", _all("13px")),
            ("#hub-nav a", "font-weight", _all("600")),
            ("#hub-nav a", "color", _all("var(--mos-ink)")),
            ("#hub-nav a", "text-decoration", _all("none")),
        ),
        "LD-04, LD-07",
        "03",
    ),
    Role(
        "S11",
        "nav gap",
        ((".nav", "gap", "clamp(12px,2vw,28px)"),),
        (("#hub-nav", "gap", _all("clamp(12px, 2vw, 28px)")),),
        None,
        "03",
    ),
    Role(
        "S12",
        "action link",
        (
            (".nav .nav-evidence", "padding", "10px 13px"),
            (".nav .nav-evidence", "border", "1px solid var(--ink)"),
        ),
        (
            (".hub-header-action", "padding", _all("10px 13px")),
            (".hub-header-action", "border", _all("1px solid var(--mos-ink)")),
            (".hub-header-action", "min-block-size", _all("44px")),
        ),
        "LD-09",
        "03",
    ),
    Role(
        "S13",
        "eyebrow",
        (
            (".eyebrow", "font", "600 12px/1.45 var(--mono)"),
            (".eyebrow", "letter-spacing", ".04em"),
            (".eyebrow", "color", "var(--blue)"),
        ),
        (
            (".hub-eyebrow", "font-size", _all("13px")),
            (".hub-eyebrow", "font-weight", _all("600")),
            (".hub-eyebrow", "letter-spacing", _all("0.04em")),
            (".hub-eyebrow", "color", _all("var(--mos-blue)")),
        ),
        "LD-04",
        "03",
    ),
    Role(
        "S14",
        "eyebrow dot",
        (
            (".eyebrow-dot", "width", "8px"),
            (".eyebrow-dot", "height", "8px"),
            (".eyebrow-dot", "border-radius", "50%"),
            (".eyebrow-dot", "background", "var(--red)"),
        ),
        (
            (".hub-eyebrow-dot", "inline-size", _all("8px")),
            (".hub-eyebrow-dot", "block-size", _all("8px")),
            (".hub-eyebrow-dot", "background", _all("var(--mos-red)")),
            (".hub-eyebrow-dot", "border-radius", _all(None)),
        ),
        "LD-13",
        "03",
    ),
    Role(
        "S15",
        "display heading",
        (
            (".section-heading h2", "font-size", "clamp(34px,4.2vw,52px)"),
            (".section-heading h2", "font", "700 clamp(34px,4.5vw,58px)/1.02 var(--display)"),
            (".section-heading h2", "letter-spacing", "-.04em"),
        ),
        (
            ("#hub-title", "font-size", _all("clamp(34px, 4.2vw, 52px)")),
            ("#hub-title", "line-height", _all("1.02")),
            ("#hub-title", "font-weight", _all("700")),
            ("#hub-title", "letter-spacing", _all("-0.04em")),
        ),
        "LD-03",
        "03",
    ),
    Role(
        "S16",
        "heading rule",
        (
            (".section-heading", "padding-bottom", "16px"),
            (".section-heading", "margin-bottom", "22px"),
            (".section-heading", "border-bottom", "1px solid var(--ink)"),
        ),
        (
            (".hub-title-row", "padding-block-end", _all("16px")),
            (".hub-title-row", "margin-block-end", _all("22px")),
            (".hub-title-row", "border-block-end", _all("1px solid var(--mos-ink)")),
        ),
        None,
        "03",
    ),
    Role(
        "S17",
        "counts rules",
        (
            (".metrics", "border-top", "1px solid var(--ink)"),
            (".metrics", "border-bottom", "1px solid var(--ink)"),
        ),
        (("#hub-counts", "border-block", _all("1px solid var(--mos-ink)")),),
        None,
        "03",
    ),
    Role(
        "S18",
        "counts numeral",
        (
            (".metric strong", "font", "700 42px/.98 var(--display)"),
            (".metric strong", "letter-spacing", "-.04em"),
        ),
        (
            (".hub-count strong", "font-size", _from_768("32px", "42px")),
            (".hub-count strong", "line-height", _all("0.98")),
            (".hub-count strong", "font-weight", _all("700")),
            (".hub-count strong", "letter-spacing", _all("-0.04em")),
        ),
        "LD-11",
        "03",
    ),
    Role(
        "S19",
        "counts caption",
        (
            (".metric span", "font-size", "12px"),
            (".metric span", "color", "var(--soft)"),
            (".metric span", "margin-top", "8px"),
        ),
        (
            (".hub-count span", "font-size", _all("13px")),
            (".hub-count span", "color", _all("var(--mos-soft)")),
            (".hub-count span", "margin-block-start", _all("8px")),
        ),
        "LD-04",
        "03",
    ),
    Role(
        "S20",
        "container",
        (
            (":root", "--max", "1200px"),
            (".metrics", "padding", "0 30px"),
        ),
        (
            ("#hub-page", "max-inline-size", _all("calc(1200px + 2 * var(--hub-gutter))")),
            (":root", "--hub-gutter", _from_768("20px", "30px")),
        ),
        "LD-12",
        "03",
    ),
    Role(
        "S21",
        "data check panel",
        (
            (".notice", "background", "var(--quiet)"),
            (".notice", "border", "1px solid var(--line)"),
            (".notice", "padding", "14px 16px"),
        ),
        (
            ("#hub-data-check", "background", _all("var(--mos-quiet)")),
            ("#hub-data-check", "border", _all("1px solid var(--hub-line)")),
            ("#hub-data-check", "padding", _all("var(--hub-space-4) var(--hub-space-5)")),
        ),
        "LD-01, LD-19",
        "03",
    ),
    Role(
        "S22",
        "text link",
        (
            ("a", "color", "var(--blue)"),
            ("a", "text-decoration-thickness", "1px"),
            ("a", "text-underline-offset", "4px"),
        ),
        (
            ("a", "color", _all("var(--mos-blue)")),
            ("a", "text-decoration-thickness", _all("1px")),
            ("a", "text-underline-offset", _all("4px")),
        ),
        None,
        "03",
    ),
    Role(
        "S23",
        "focus ring",
        (
            ("a:focus-visible", "outline", "3px solid var(--blue)"),
            ("a:focus-visible", "outline-offset", "4px"),
        ),
        (
            (":focus-visible", "outline", _all("3px solid var(--mos-ink)")),
            (":focus-visible", "outline-offset", _all("3px")),
        ),
        "LD-20",
        "03",
    ),
    Role(
        "S24",
        "primary button",
        (
            (".button-dark", "background", "var(--ink)"),
            (".button-dark", "color", "var(--paper)"),
            (".button-dark:hover", "background", "var(--blue)"),
            (".button-dark:hover", "color", "var(--white)"),
            (".button", "min-height", "48px"),
        ),
        (
            (".hub-button", "background", _all("var(--mos-ink)")),
            (".hub-button", "color", _all("var(--mos-paper)")),
            (".hub-button:hover", "background", _all("var(--mos-blue)")),
            (".hub-button:hover", "color", _all("var(--mos-white)")),
            (".hub-button", "min-block-size", _all("44px")),
        ),
        "LD-24, LD-09",
        "03",
    ),
    Role(
        "S25",
        "footer rule",
        ((".footer-tagline", "border-top", "1px solid var(--line)"),),
        (("#hub-footer", "border-block-start", _all("1px solid var(--hub-line)")),),
        "LD-01",
        "03",
    ),
    Role(
        "S26",
        "hover motion and smooth scrolling",
        (
            (".button:hover", "transform", "translateY(-2px)"),
            ("html", "scroll-behavior", "smooth"),
        ),
        (
            (".hub-button:hover", "transform", _all(None)),
            ("html", "scroll-behavior", _all(None)),
        ),
        "LD-14, LD-15",
        "03",
    ),
    Role(
        "S27",
        "band box",
        (
            (".findings-overview", "background", "var(--ink)"),
            (".findings-overview", "color", "var(--paper)"),
            (".findings-overview", "padding", "16px 18px"),
        ),
        (
            (".mos-ground-ink", "background", _all("var(--mos-ink)")),
            (".mos-ground-ink", "color", _all("var(--mos-paper)")),
            (".hub-band", "padding", _all("var(--hub-space-4) var(--hub-space-5)")),
        ),
        "LD-18",
        "03",
    ),
    Role(
        "S28",
        "band label",
        (
            (".overview-label", "font", "600 11px var(--mono)"),
            (".overview-label", "letter-spacing", ".04em"),
        ),
        (
            (".hub-band-label", "font-size", _all("13px")),
            (".hub-band-label", "font-weight", _all("600")),
            (".hub-band-label", "letter-spacing", _all("0.04em")),
        ),
        "LD-04",
        "03",
    ),
    Role(
        "S29",
        "band marker",
        (
            (".overview-mark", "width", "10px"),
            (".overview-mark", "height", "10px"),
            (".overview-mark", "background", "var(--yellow)"),
        ),
        (
            (".hub-band-mark", "inline-size", _all("10px")),
            (".hub-band-mark", "block-size", _all("10px")),
            (".hub-band-mark", "background", _all("var(--mos-yellow)")),
        ),
        None,
        "03",
    ),
    Role(
        "S30",
        "band text",
        (
            (".findings-overview p", "font-size", "14px"),
            (".findings-overview p", "color", "#eeece5"),
        ),
        (
            (".hub-band-reading", "font-size", _all("14px")),
            (".hub-band-reading", "color", _all(None)),
        ),
        "LD-10",
        "03",
    ),
    Role(
        "S31",
        "band link",
        (
            (".findings-overview a", "color", "#d9e1ff"),
            (".findings-overview a", "font-size", "12px"),
            (".findings-overview a", "font-weight", "650"),
        ),
        (
            (".hub-band-link", "color", _all("var(--mos-paper)")),
            (".hub-band-link", "font-size", _all("13px")),
            (".hub-band-link", "font-weight", _all("600")),
        ),
        "LD-04, LD-07, LD-10",
        "03",
    ),
    # Finding rows (plan 06, owner decision D-01 and the prototype of 2026-11-08). The target
    # values are the `.engine-*` rules of the target stylesheet; the hub values are the
    # `.hub-bank-*` rules of hub-bank.css by width key.
    Role(
        "R01",
        "row grid",
        (
            (
                ".engine-row",
                "grid-template-columns",
                "38px minmax(155px,.82fr) 108px minmax(300px,1.7fr)",
            ),
        ),
        (
            (
                ".hub-bank-row",
                "grid-template-columns",
                {
                    "base": "36px minmax(0, 1fr)",
                    "768": "44px minmax(0, 1fr) 130px",
                    "1024": "44px minmax(0, 1.15fr) 150px minmax(0, 1.2fr) 300px",
                },
            ),
        ),
        "LD-05, LD-17, LD-27",
        "06",
    ),
    Role(
        "R02",
        "row spacing",
        (
            (".engine-row", "gap", "16px"),
            (".engine-row", "padding", "19px 4px 20px 0"),
        ),
        (
            (".hub-bank-row", "column-gap", _all("var(--hub-space-5)")),
            (".hub-bank-row", "padding-block", _all("var(--hub-space-5)")),
        ),
        "LD-21",
        "06",
    ),
    Role(
        "R03",
        "row rule",
        ((".engine-row", "border-bottom", "1px solid var(--line)"),),
        ((".hub-bank-row", "border-block-end", _all("1px solid var(--hub-line)")),),
        "LD-01",
        "06",
    ),
    Role(
        "R04",
        "row index",
        (
            (".engine-index", "color", "var(--red)"),
            (".engine-index", "font-size", "12px"),
            (".engine-index", "padding-top", "3px"),
        ),
        (
            (".hub-bank-rank-n", "font-family", _all("var(--mos-font-code)")),
            (".hub-bank-rank-n", "font-size", _all("13px")),
            (".hub-bank-rank-n", "font-weight", _all("600")),
            (".hub-bank-rank-n", "color", _all("var(--mos-red)")),
            (".hub-bank-rank-n", "padding-block-start", _all("3px")),
        ),
        "LD-04, LD-05",
        "06",
    ),
    Role(
        "R05",
        "row title",
        (
            (".engine-name h3", "font", "700 18px/1.15 var(--display)"),
            (".engine-name h3", "letter-spacing", "-.02em"),
        ),
        (
            (".hub-bank-pair", "font-size", _from_768("20px", "22px")),
            (".hub-bank-pair", "line-height", _all("1.25")),
            (".hub-bank-pair", "font-weight", _all("700")),
            (".hub-bank-pair", "letter-spacing", _all("-0.02em")),
        ),
        "LD-29",
        "06",
    ),
    Role(
        "R06",
        "row id",
        (
            (".engine-name code", "font-size", "12px"),
            (".engine-name code", "color", "var(--soft)"),
        ),
        (
            (".hub-bank-ids a", "font-family", _all("var(--mos-font-code)")),
            (".hub-bank-ids a", "font-size", _all("13px")),
            (".hub-bank-ids a", "color", _all("var(--mos-blue)")),
            (".hub-bank-ids a", "text-decoration", _all("underline")),
        ),
        "LD-04, LD-22",
        "06",
    ),
    Role(
        "R07",
        "row numeral",
        (
            (".engine-count strong", "font", "700 27px/1 var(--display)"),
            (".engine-count strong", "letter-spacing", "-.04em"),
            (".engine-count", "color", "var(--blue)"),
        ),
        (
            (".hub-bank-numeral", "font-size", _from_768("28px", "40px")),
            (".hub-bank-numeral", "font-weight", _all("700")),
            (".hub-bank-numeral", "line-height", _all("1")),
            (".hub-bank-numeral", "letter-spacing", _all("-0.04em")),
            (".hub-bank-numeral--meaning", "color", _all("var(--mos-blue)")),
            (".hub-bank-numeral--wording", "color", _all("var(--mos-red)")),
        ),
        "LD-30, LD-33",
        "06",
    ),
    Role(
        "R08",
        "row caption",
        (
            (".engine-count span", "font-size", "12px"),
            (".engine-count span", "color", "var(--soft)"),
        ),
        (
            (".hub-bank-caption", "font-family", _all("var(--mos-font-code)")),
            (".hub-bank-caption", "font-size", _all("13px")),
            (".hub-bank-caption", "color", _all("var(--mos-soft)")),
            (".hub-bank-caption", "display", _all("block")),
        ),
        "LD-04, LD-17",
        "06",
    ),
    Role(
        "R09",
        "row description",
        (
            (".engine-description p", "font-size", "13px"),
            (".engine-description p", "line-height", "1.48"),
            (".engine-description p", "color", "#393731"),
        ),
        (
            (".hub-bank-reading p", "font-size", _all("16px")),
            (".hub-bank-reading p", "line-height", _all("1.5")),
        ),
        "LD-06, LD-31",
        "06",
    ),
    Role(
        "R10",
        "row actions",
        (
            (".engine-description a", "font-size", "12px"),
            (".engine-description a", "font-weight", "700"),
        ),
        (
            (".hub-bank-read", "min-block-size", _all("44px")),
            (".hub-bank-read", "font-size", _all("16px")),
            (".hub-bank-read", "font-weight", _all("600")),
            (".hub-bank-open-btn", "border", _all("1px solid var(--mos-ink)")),
            (".hub-bank-open-btn", "min-block-size", _all("44px")),
            (".hub-bank-open-btn", "font-size", _all("16px")),
            (".hub-bank-open-btn", "font-weight", _all("600")),
            (".hub-bank-open-btn", "background", _all("transparent")),
        ),
        "LD-23, LD-24, LD-09",
        "06",
    ),
    Role(
        "R11",
        "list rule",
        ((".engine-list", "border-top", "1px solid var(--line)"),),
        ((".hub-bank-list", "border-block-start", _all("1px solid var(--hub-line)")),),
        "LD-01",
        "06",
    ),
)

WIDTH_KEYS: tuple[str, ...] = ("base", "768", "1024")
