import gzip
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence


ASSET_COLUMNS = (
    "id",
    "originalPath",
    "originalFileName",
    "type",
    "fileCreatedAt",
    "fileModifiedAt",
    "localDateTime",
    "createdAt",
    "deletedAt",
    "isOffline",
    "sidecarPath",
)
EXIF_COLUMNS = ("assetId", "dateTimeOriginal", "description")
ASSET_FILE_COLUMNS = ("assetId", "type", "path")


def _copy_value(value: Optional[str]) -> str:
    if value is None:
        return r"\N"
    return (
        value.replace("\\", r"\\")
        .replace("\t", r"\t")
        .replace("\n", r"\n")
        .replace("\r", r"\r")
    )


def _section(
    table: str, columns: Sequence[str], rows: Iterable[Mapping[str, Optional[str]]]
) -> str:
    header = ", ".join(f'"{column}"' for column in columns)
    lines = [f"COPY public.{table} ({header}) FROM stdin;"]
    lines.extend("\t".join(_copy_value(row.get(column)) for column in columns) for row in rows)
    lines.append(r"\.")
    return "\n".join(lines)


def write_backup(
    path: Path,
    assets: Iterable[Mapping[str, Optional[str]]],
    exif: Iterable[Mapping[str, Optional[str]]] = (),
    asset_files: Optional[Iterable[Mapping[str, Optional[str]]]] = None,
) -> Path:
    sections = [
        _section("asset", ASSET_COLUMNS, assets),
        _section("asset_exif", EXIF_COLUMNS, exif),
    ]
    if asset_files is not None:
        sections.append(_section("asset_file", ASSET_FILE_COLUMNS, asset_files))
    text = "\n".join((*sections, ""))
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)
    return path
