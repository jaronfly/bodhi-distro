#!/usr/bin/env python3
"""Install-time helper for install.sh: copy the skill, keep the install record, undo it.

Everything install.sh writes or installs is recorded in ~/.bodhi/install-manifest.json
(BODHI_HOME moves ~/.bodhi). `uninstall-apply` removes only paths that record lists,
and never a vault or a seed checkout the person already had: those hold their own work.
Third-party software is recorded with the command that would remove it; install.sh asks
before running any of those. Standard library only; nothing here uses the network.

  python3 bin/bodhi_install.py targets --seed DIR
  python3 bin/bodhi_install.py copy-skill --seed DIR --target claude-code [--replace] [--dry-run]
  python3 bin/bodhi_install.py record --kind KIND [--path P] [--label L] [--remove-with CMD]
  python3 bin/bodhi_install.py set-seed --path DIR [--kind clone|seed-in-place]
  python3 bin/bodhi_install.py show
  python3 bin/bodhi_install.py uninstall-plan
  python3 bin/bodhi_install.py uninstall-apply [--dry-run]
"""

import argparse
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("bodhi_cli", str(HERE / "bodhi.py"))
bodhi = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bodhi)

SCHEMA = "bodhi.install-manifest/v1"
# What uninstall may delete, and what it must leave for the person.
REMOVABLE = ("skill", "clone", "file")
KEPT = ("vault", "seed-in-place")
COMMANDS = ("package", "hermes-skill")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def manifest_path():
    return bodhi.bodhi_home() / "install-manifest.json"


def load():
    path = manifest_path()
    if not path.is_file():
        return {"schema": SCHEMA, "created_utc": now(), "seed_dir": "", "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not isinstance(data.get("entries"), list):
        raise SystemExit("install record %s is not a %s file; move it aside" % (path, SCHEMA))
    return data


def save(data, dry_run=False):
    if dry_run:
        return
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_utc"] = now()
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def add_entry(data, entry):
    """Add one entry unless the same kind+path (or kind+label) is already recorded."""
    key = (entry["kind"], entry.get("path") or entry.get("label"))
    for existing in data["entries"]:
        if (existing["kind"], existing.get("path") or existing.get("label")) == key:
            return False
    entry["recorded_utc"] = now()
    data["entries"].append(entry)
    return True


def target_by_key(key):
    for target in bodhi.skill_targets():
        if target["key"] == key:
            return target
    raise SystemExit("unknown target: " + key)


def copy_tree(source, dest):
    """Copy the skill beside its destination, then swap it in, so a crash leaves no half copy."""
    ignore = shutil.ignore_patterns(".*", "__pycache__", "*.pyc")
    staging = dest.with_name("." + dest.name + ".tmp-%d" % os.getpid())
    old = dest.with_name("." + dest.name + ".old-%d" % os.getpid())
    shutil.rmtree(str(staging), ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(source), str(staging), ignore=ignore)
    if dest.exists():
        dest.rename(old)
    staging.rename(dest)
    shutil.rmtree(str(old), ignore_errors=True)


def cmd_targets(args):
    seed_skill = Path(args.seed) / "skills" / bodhi.SKILL_NAME
    seed_hash = bodhi.tree_hash(seed_skill)
    search = os.environ.get("PATH", os.defpath)
    out = []
    for target in bodhi.skill_targets():
        copy = bodhi._find_skill_copy(target)
        out.append({"key": target["key"], "label": target["label"], "dest": str(target["dest"]),
                    "harness_found": [c for c in target["commands"] if shutil.which(c, path=search)],
                    "present": str(copy) if copy else "",
                    "matches": bool(copy) and bodhi.tree_hash(copy) == seed_hash})
    print(json.dumps(out, indent=2))


def cmd_copy_skill(args):
    source = Path(args.seed) / "skills" / bodhi.SKILL_NAME
    if not (source / "SKILL.md").is_file():
        raise SystemExit("no skill at " + str(source))
    target = target_by_key(args.target)
    dest = target["dest"]
    data = load()
    recorded = any(e["kind"] == "skill" and e.get("path") == str(dest) for e in data["entries"])
    if dest.exists() and bodhi.tree_hash(dest) == bodhi.tree_hash(source):
        action = "unchanged"
    elif dest.exists() and not recorded and not args.replace:
        # Someone else's copy: the installer asks before replacing it.
        print(json.dumps({"target": args.target, "dest": str(dest), "action": "exists-unrecorded"}))
        return 0
    else:
        action = "updated" if dest.exists() else "created"
        if not args.dry_run:
            copy_tree(source, dest)
    if action != "unchanged" or not recorded:
        if add_entry(data, {"kind": "skill", "path": str(dest), "label": target["label"]}):
            save(data, args.dry_run)
    print(json.dumps({"target": args.target, "dest": str(dest), "action": action,
                      "dry_run": args.dry_run}))
    return 0


def cmd_record(args):
    data = load()
    entry = {"kind": args.kind, "label": args.label or args.path or args.kind}
    if args.path:
        entry["path"] = str(Path(args.path).expanduser().absolute())
    if args.remove_with:
        entry["remove_with"] = args.remove_with
    if add_entry(data, entry):
        save(data, args.dry_run)
        print(json.dumps({"recorded": entry}))
    else:
        print(json.dumps({"recorded": None, "reason": "already recorded"}))


def cmd_set_seed(args):
    data = load()
    path = str(Path(args.path).expanduser().absolute())
    changed = data.get("seed_dir") != path
    data["seed_dir"] = path
    added = add_entry(data, {"kind": args.kind, "path": path, "label": "Bodhi seed"})
    if changed or added:
        save(data, args.dry_run)
    print(json.dumps({"seed_dir": path, "changed": changed or added}))


def cmd_show(_args):
    print(json.dumps(load(), indent=2, sort_keys=True))


def plan():
    data = load()
    remove, keep, commands = [], [], []
    for entry in data["entries"]:
        if entry["kind"] in REMOVABLE:
            remove.append(entry)
        elif entry["kind"] in COMMANDS:
            commands.append(entry)
        else:
            keep.append(entry)
    return data, remove, keep, commands


def cmd_uninstall_plan(_args):
    if not manifest_path().is_file():
        print(json.dumps({"manifest": "", "remove": [], "keep": [], "commands": []}))
        return 0
    _, remove, keep, commands = plan()
    print(json.dumps({"manifest": str(manifest_path()), "remove": remove, "keep": keep,
                      "commands": commands}, indent=2))
    return 0


def safe_to_remove(entry):
    """Refuse anything that does not look like what the installer made."""
    path = Path(entry["path"])
    if not path.exists():
        return False, "already gone"
    if entry["kind"] == "skill":
        ok = path.name == bodhi.SKILL_NAME and (path / "SKILL.md").is_file()
        return ok, "" if ok else "not a bodhi-seed skill folder"
    if entry["kind"] == "clone":
        ok = (path / ".git").exists() and (path / "bin" / "bodhi.py").is_file() and \
            (path / "skills" / bodhi.SKILL_NAME).is_dir()
        return ok, "" if ok else "not a bodhi-distro checkout"
    if entry["kind"] == "file":
        return path.is_file(), "" if path.is_file() else "not a file"
    return False, "not removable"


def cmd_uninstall_apply(args):
    if not manifest_path().is_file():
        print(json.dumps({"removed": [], "skipped": [], "note": "no install record"}))
        return 0
    data, remove, _, _ = plan()
    removed, skipped = [], []
    for entry in remove:
        ok, why = safe_to_remove(entry)
        if not ok:
            skipped.append({"path": entry["path"], "why": why})
            continue
        if not args.dry_run:
            target = Path(entry["path"])
            if target.is_dir():
                shutil.rmtree(str(target))
            else:
                target.unlink()
        removed.append(entry["path"])
    if not args.dry_run:
        manifest_path().unlink()
    print(json.dumps({"removed": removed, "skipped": skipped, "dry_run": args.dry_run}, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    targets = sub.add_parser("targets")
    targets.add_argument("--seed", required=True)
    copy = sub.add_parser("copy-skill")
    copy.add_argument("--seed", required=True)
    copy.add_argument("--target", required=True, choices=[t["key"] for t in bodhi.skill_targets()])
    copy.add_argument("--replace", action="store_true", help="replace a copy the installer did not make")
    copy.add_argument("--dry-run", action="store_true")
    record = sub.add_parser("record")
    record.add_argument("--kind", required=True, choices=REMOVABLE + KEPT + COMMANDS)
    record.add_argument("--path")
    record.add_argument("--label")
    record.add_argument("--remove-with")
    record.add_argument("--dry-run", action="store_true")
    seed = sub.add_parser("set-seed")
    seed.add_argument("--path", required=True)
    seed.add_argument("--kind", default="clone", choices=("clone", "seed-in-place"))
    seed.add_argument("--dry-run", action="store_true")
    sub.add_parser("show")
    sub.add_parser("uninstall-plan")
    apply = sub.add_parser("uninstall-apply")
    apply.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    handlers = {"targets": cmd_targets, "copy-skill": cmd_copy_skill, "record": cmd_record,
                "set-seed": cmd_set_seed, "show": cmd_show, "uninstall-plan": cmd_uninstall_plan,
                "uninstall-apply": cmd_uninstall_apply}
    return handlers[args.command](args) or 0


if __name__ == "__main__":
    sys.exit(main())
