from __future__ import annotations

import re
from pathlib import Path


target = Path(
    r"D:\Project\AutoDocGenerator"
    r"\src\autodocgenerator\services\image_processor.py"
)

source = target.read_text(encoding="utf-8")

if "from typing import ClassVar" not in source:
    if re.search(r"^from typing import ", source, flags=re.MULTILINE):
        source = re.sub(
            r"^from typing import ([^\n]+)$",
            lambda match: (
                "from typing import "
                + ", ".join(
                    sorted(
                        {
                            item.strip()
                            for item in match.group(1).split(",")
                        }
                        | {"ClassVar"}
                    )
                )
            ),
            source,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        source = source.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom typing import ClassVar\n",
            1,
        )

pattern = re.compile(
    r"(?P<indent>^[ \t]*)_WORD_NATIVE_EXTENSIONS\s*=\s*\{\n"
    r"(?P<body>(?:^[ \t]+[\"'][^\"']+[\"'],?\n)+)"
    r"^[ \t]*\}",
    flags=re.MULTILINE,
)

match = pattern.search(source)

if match:
    indent = match.group("indent")
    extensions = re.findall(r"[\"']([^\"']+)[\"']", match.group("body"))

    replacement_lines = [
        (
            f"{indent}_WORD_NATIVE_EXTENSIONS: "
            "ClassVar[frozenset[str]] = frozenset("
        ),
        f"{indent}    {{",
        *[
            f'{indent}        "{extension}",'
            for extension in extensions
        ],
        f"{indent}    }}",
        f"{indent})",
    ]

    source = (
        source[: match.start()]
        + "\n".join(replacement_lines)
        + source[match.end() :]
    )
elif "_WORD_NATIVE_EXTENSIONS: ClassVar[frozenset[str]]" not in source:
    raise RuntimeError(
        "Deklarasi _WORD_NATIVE_EXTENSIONS tidak ditemukan."
    )

target.write_text(source.rstrip() + "\n", encoding="utf-8")

print("RUF012 selesai diperbaiki.")
print(target)