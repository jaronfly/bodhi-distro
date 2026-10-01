#!/usr/bin/env python3
"""Build bodhi-seed.zip for skill upload in claude.ai and Claude Desktop.

The archive holds the skill folder itself as its top level (bodhi-seed/SKILL.md,
bodhi-seed/references/...), which is the shape claude.ai looks for; a SKILL.md at
the root of the zip is not recognized. Before zipping, the frontmatter is checked
against the Agent Skills specification (https://agentskills.io/specification),
and every relative link in SKILL.md must point to a file inside the skill.

The build is deterministic: sorted entries, fixed timestamps and permissions, so
the same skill always produces the same bytes and SHA-256. Standard library only.

  python3 bin/package_skill.py            # writes dist/bodhi-seed.zip
  python3 bin/package_skill.py --check    # validate only; writes nothing
  python3 bin/package_skill.py --out PATH # choose where the zip goes

Upload: claude.ai or the desktop app, Customize > Skills, then add a skill and
choose the zip. The zip is built on demand and never committed.
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "bodhi-seed"
DEFAULT_OUT = ROOT / "dist" / "bodhi-seed.zip"
# Top-level frontmatter fields the Agent Skills specification defines.
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
# An older claude.ai help-center page gave 200 characters for a description; the
# current docs and the spec allow 1024. Staying within 200 keeps both readings happy.
CAUTIOUS_DESCRIPTION = 200


def frontmatter(text):
    """Return {top-level key: raw value} from a SKILL.md, without a YAML dependency."""
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with a --- frontmatter line")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter has no closing --- line")
    fields = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line[0] in " \t#":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError("frontmatter line is not key: value: " + line)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif ": " in value or value.endswith(":"):
            # YAML reads an unquoted ": " as a nested mapping, and strict loaders reject it.
            raise ValueError("frontmatter value for %s has an unquoted ': '; quote it or "
                             "reword it" % key.strip())
        fields[key.strip()] = value
    return fields


def check_skill(skill_dir):
    """Return (errors, warnings) for a skill folder."""
    errors, warnings = [], []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return ["SKILL.md is missing"], warnings
    text = skill_md.read_text(encoding="utf-8")
    try:
        fields = frontmatter(text)
    except ValueError as exc:
        return [str(exc)], warnings
    extra = sorted(set(fields) - ALLOWED_FIELDS)
    if extra:
        errors.append("fields the Agent Skills spec does not define: " + ", ".join(extra)
                      + " (move them under metadata:)")
    name = fields.get("name", "")
    if not name:
        errors.append("name is required")
    elif len(name) > 64 or not NAME.match(name):
        errors.append("name must be 1-64 lowercase letters, digits and single hyphens: " + name)
    elif name != skill_dir.name:
        errors.append("name " + name + " must match the folder name " + skill_dir.name)
    description = fields.get("description", "")
    if not description:
        errors.append("description is required")
    elif len(description) > 1024:
        errors.append("description is %d characters; the limit is 1024" % len(description))
    elif len(description) > CAUTIOUS_DESCRIPTION:
        warnings.append("description is %d characters; some claude.ai docs cite a 200-character "
                        "limit" % len(description))
    if len(fields.get("compatibility", "")) > 500:
        errors.append("compatibility is limited to 500 characters")
    # Every relative link in every Markdown file must land on a file inside the skill:
    # a link that reaches back into the repository breaks once the folder is installed alone.
    root = skill_dir.resolve()
    for page in sorted(skill_dir.rglob("*.md")):
        for target in LINK.findall(page.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            linked = (page.parent / target).resolve()
            if root not in linked.parents or not linked.is_file():
                errors.append(page.relative_to(skill_dir).as_posix() + " links to a file outside "
                              "the skill or missing: " + target)
    return errors, warnings


def skill_files(skill_dir):
    files = []
    for path in sorted(skill_dir.rglob("*")):
        relative = path.relative_to(skill_dir)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("symlinks are not packaged: " + str(relative))
        if path.is_file() and path.suffix != ".pyc":
            files.append(relative)
    return files


def build(skill_dir, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    names = []
    with zipfile.ZipFile(str(tmp), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in skill_files(skill_dir):
            arcname = skill_dir.name + "/" + relative.as_posix()
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (skill_dir / relative).read_bytes())
            names.append(arcname)
    tmp.replace(out)
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the bodhi-seed skill zip for claude.ai upload.")
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="zip path (default dist/bodhi-seed.zip)")
    parser.add_argument("--skill", type=Path, default=SKILL, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    skill_dir = args.skill.resolve()
    errors, warnings = check_skill(skill_dir)
    for warning in warnings:
        print("package_skill: warning: " + warning, file=sys.stderr)
    if errors:
        for error in errors:
            print("package_skill: " + error, file=sys.stderr)
        return 1
    if args.check:
        print(json.dumps({"status": "valid", "skill": str(skill_dir)}, sort_keys=True))
        return 0
    out = args.out.expanduser().absolute()
    try:
        names = build(skill_dir, out)
    except (OSError, ValueError) as exc:
        print("package_skill: " + str(exc), file=sys.stderr)
        return 1
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(json.dumps({"status": "built", "zip": str(out), "sha256": digest, "files": names},
                     sort_keys=True))
    print("Upload it in claude.ai or Claude Desktop: Customize > Skills, add a skill, choose "
          "this zip. Then turn it on and check that it loads (docs/INSTALL.md).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
