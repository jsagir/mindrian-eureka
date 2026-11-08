"""Read packaged hub assets without writing any file.

Import rule: standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ASSETS_ROOT = Path(__file__).resolve().parent / "assets"

EXPECTED_STATIC: dict[str, str] = {
    "assets/brand/mos-lockup-paper-v2.svg": (
        "028ffd9040e769684c78767b890175bf1b2734e7bd0a4bbf953de38051ba4477"
    ),
    "assets/brand/mos-lockup-reverse-v2.svg": (
        "3033e523efd4f78cafd1ed28fe311251e5f58454491c8aabd783bb456a99236b"
    ),
    "assets/faces/theo-boundary.svg": (
        "71c02c9510bac750821e7587e668543f8b51498b80c57b6feb9b08f92686be2c"
    ),
    "assets/faces/theo-handover.svg": (
        "b75f10a9da8d93d9cffc5d01b07c2aadd36d04d586e24e05abbe726b5df622a1"
    ),
    "assets/faces/theo-limit.svg": (
        "4eb4f93af9fe84399b9758c10ada7fad9650932ac88e11ac10c2ab8362c3261a"
    ),
    "assets/faces/theo-rest.svg": (
        "63517ad7dbf21399b8e3db9144eda9bed743a14b604df99d4b4cab43a5d3b832"
    ),
    "assets/favicon-16.png": ("418af6f5fb7019293a7f3245471548f6cad7cfe139aed8513adda281aa4c8458"),
    "assets/favicon-180.png": ("d63554adee05397dec9b18bf298c507354b340682de7395ebb4992b5686ea7cb"),
    "assets/favicon-32.png": ("4be8387cec69767d5bfc5926f837174813e5aeae914afa29e850a0dab416b2f1"),
    "assets/favicon-48.png": ("bb4c9ea8875104981d26a9882fbf7f412359c1f46cf93b81442d06a33e514903"),
    "assets/favicon.svg": ("740dc879b95b4e66813f332833fcb530bf1612fb045831b24a6f38a5ecc87e81"),
    "assets/fonts/DM-Sans-variable.ttf": (
        "8cd08d97e89c24d0aa92edd2f0f4c8ee6195eee9b7c9f154865a58b02f0c1c0d"
    ),
    "assets/fonts/Figtree-variable.woff2": (
        "4ba7d3d096695818fe0686be4f1e82c6b05134e18a22260336130335027462dd"
    ),
    "assets/fonts/Heebo-variable.ttf": (
        "18f930b583fa8fe6b40b2f8263b7ac6afbac07adc91a12467874e7467d3ace30"
    ),
    "assets/fonts/JetBrains-Mono-variable.ttf": (
        "48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda"
    ),
    "assets/fonts/dmsans-OFL.txt": (
        "c6da9ab29436871bd4347b70607cf2fb2ab82a926a4afe84da0e7a02de4a189e"
    ),
    "assets/fonts/figtree-OFL.txt": (
        "bdc70a7c46c8afbe40b21d2b44a92f52b9aace8ede244804f38c83db61fb9220"
    ),
    "assets/fonts/heebo-OFL.txt": (
        "90041d940cac91091b10132d40e727095b62e90e8c3aff9878fdb2268c7cc64f"
    ),
    "assets/fonts/jetbrainsmono-OFL.txt": (
        "25a5447330f5ce68637e21e6d200f4564ae92a7614accb4b8a79bc51a98720ad"
    ),
    "tokens.css": ("d70d4deaf730d6f336a51d5d9fd9e1d8cb39eda461f9b537dab45e3747a05ef1"),
    "vendor/3d-force-graph.min.js": (
        "fa365edfa625f055982ea9e41feac875bc1c46c6225318c420eed26646e78499"
    ),
    "vendor/LICENSE-3d-force-graph.txt": (
        "7262e566e874d1ce8cfadace01d4f635f8d704b6bdf7b4345cc028e5faeafded"
    ),
    "vendor/NOTICES.txt": ("f4eb589ddf23f95a04e167d599f1ad5756bed090f155ca76b8d1a304c0b50512"),
}

BOOK_SOURCES: dict[str, str] = {
    "assets/brand/mos-lockup-paper-v2.svg": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-dc83869aa5.svg"
    ),
    "assets/brand/mos-lockup-reverse-v2.svg": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-aafc7b2563.svg"
    ),
    "assets/faces/theo-boundary.svg": (
        "segments/identity/theo/states/boundary/entries/2026-10-19/asset-7c79733ea9.svg"
    ),
    "assets/faces/theo-handover.svg": (
        "segments/identity/theo/states/handover/entries/2026-10-19/asset-0af6d74d8a.svg"
    ),
    "assets/faces/theo-limit.svg": (
        "segments/identity/theo/states/limit/entries/2026-10-19/asset-405e3aa366.svg"
    ),
    "assets/faces/theo-rest.svg": (
        "segments/identity/theo/states/rest/entries/2026-10-19/asset-b27be39aab.svg"
    ),
    "assets/favicon-16.png": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-e062595916.png"
    ),
    "assets/favicon-180.png": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-7500ef54f7.png"
    ),
    "assets/favicon-32.png": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-95ebe29cff.png"
    ),
    "assets/favicon-48.png": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-0b8f6f83e5.png"
    ),
    "assets/favicon.svg": (
        "segments/identity/logo/variants/entries/2026-10-19/asset-6b6bb25f85.svg"
    ),
    "assets/fonts/DM-Sans-variable.ttf": (
        "segments/foundations/typography/dm-sans/entries/2026-10-19/asset-a9d9a51c0c.ttf"
    ),
    "assets/fonts/Figtree-variable.woff2": (
        "segments/foundations/typography/figtree/entries/2026-10-19/asset-16fa7737d0.woff2"
    ),
    "assets/fonts/Heebo-variable.ttf": (
        "segments/foundations/typography/heebo/entries/2026-10-19/asset-26ff41b9d0.ttf"
    ),
    "assets/fonts/JetBrains-Mono-variable.ttf": (
        "segments/foundations/typography/jetbrains-mono/entries/2026-10-19/asset-59e37f3e22.ttf"
    ),
    "assets/fonts/dmsans-OFL.txt": (
        "segments/foundations/typography/dm-sans/entries/2026-10-19/asset-a43d992a30.txt"
    ),
    "assets/fonts/figtree-OFL.txt": (
        "segments/foundations/typography/figtree/entries/2026-10-19/asset-982863a066.txt"
    ),
    "assets/fonts/heebo-OFL.txt": (
        "segments/foundations/typography/heebo/entries/2026-10-19/asset-c7b64fae0a.txt"
    ),
    "assets/fonts/jetbrainsmono-OFL.txt": (
        "segments/foundations/typography/jetbrains-mono/entries/2026-10-19/asset-ff0057ecb6.txt"
    ),
    "tokens.css": ("segments/foundations/tokens/entries/2026-10-19/asset-b1c43da20b.css"),
    "vendor/3d-force-graph.min.js": ("npm:3d-force-graph@1.79.1"),
    "vendor/LICENSE-3d-force-graph.txt": ("npm:3d-force-graph@1.79.1"),
    "vendor/NOTICES.txt": ("npm:3d-force-graph@1.79.1"),
}


@dataclass(frozen=True)
class AssetFile:
    """A local packaged file and its destination in a built hub."""

    output_path: str
    package_path: Path
    sha256: str | None


def static_assets() -> tuple[AssetFile, ...]:
    """Return canonical static assets ordered by output path."""
    return tuple(
        AssetFile(name, ASSETS_ROOT / "static" / name, digest)
        for name, digest in sorted(EXPECTED_STATIC.items())
    )


def authored_assets() -> tuple[AssetFile, ...]:
    """Return authored page files, or an empty tuple before they exist."""
    folder = ASSETS_ROOT / "authored"
    if not folder.is_dir():
        return ()
    return tuple(
        AssetFile(path.relative_to(folder).as_posix(), path, None)
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    )


def all_assets() -> tuple[AssetFile, ...]:
    """Return static then authored assets, refusing overlapping output paths."""
    assets = static_assets() + authored_assets()
    paths = [asset.output_path for asset in assets]
    if len(paths) != len(set(paths)):
        raise ValueError("Hub assets contain duplicate output paths")
    return assets
