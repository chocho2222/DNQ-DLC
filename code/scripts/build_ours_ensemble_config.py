#!/usr/bin/env python
"""Build the evaluation config for the proposed controller as an ensemble.

The main comparison evaluates the proposed controller from one world-model
checkpoint. The single ``ours_dnq_dlc`` record is replaced by one record whose
``policy`` field is the list of five checkpoints trained from the same recipe
under five different seeds; the controller fuses them at rollout time. Every
other algorithm record is copied unchanged, so the ensemble can be run in the
same pass as the comparators that were already evaluated.

Only the ensemble arm is kept by default (``--only-ensemble``), because the
comparators of the main matrix are already archived; dropping the flag keeps
every record and reproduces the full matrix in one pass.

Usage:
    python -m scripts.build_ours_ensemble_config \
        --base configs/tits_ours_seedspread_20260928.json \
        --out configs/tits_ours_ensemble_20260928.json --only-ensemble
"""
import argparse
import json
from pathlib import Path

OURS = "ours_dnq_dlc"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True,
                        help="config carrying the single-seed arms of the recipe")
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", default=f"{OURS}_ensemble")
    parser.add_argument("--only-ensemble", action="store_true",
                        help="emit the ensemble arm alone and drop the comparators")
    parser.add_argument("--template-config", default="",
                        help="config holding the single-model arm whose fields become "
                             "the ensemble's, for a variant such as the shield-off arm")
    parser.add_argument("--template-name", default="",
                        help="arm name to copy out of --template-config")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=JSON",
                        help="override one field of the ensemble record, e.g. "
                             "--set ensemble_epistemic=false")
    args = parser.parse_args()

    config = json.loads(Path(args.base).read_text(encoding="utf-8"))
    members = [a for a in config["algorithms"]
               if a.get("name", "").startswith(f"{OURS}_seed")]
    if len(members) < 2:
        raise SystemExit("the base config carries fewer than two world-model seeds")
    members.sort(key=lambda a: int(a["world_model_train_seed"]))

    if args.template_config:
        if not args.template_name:
            raise SystemExit("--template-config needs --template-name")
        other = json.loads(Path(args.template_config).read_text(encoding="utf-8"))
        source = next((a for a in other["algorithms"] if a.get("name") == args.template_name), None)
        if source is None:
            raise SystemExit(f"{args.template_config} has no arm {args.template_name!r}")
        template = dict(source)
    else:
        template = dict(members[0])
    template.pop("world_model_train_seed", None)
    template["name"] = args.name
    template["label_cn"] = f"DNQ-DLC (ensemble of {len(members)} world models)"
    template["policy"] = [member["policy"] for member in members]
    template["world_model_ensemble_seeds"] = [
        int(member["world_model_train_seed"]) for member in members]
    for item in args.set:
        key, _, value = item.partition("=")
        if not key or not value:
            raise SystemExit(f"--set expects KEY=JSON, got {item!r}")
        template[key] = json.loads(value)

    kept = [a for a in config["algorithms"]
            if not a.get("name", "").startswith(f"{OURS}_seed")]
    config["algorithms"] = [template] if args.only_ensemble else [template] + kept
    config["note"] = (str(config.get("note", "")) +
                      f" | The proposed controller is one policy that fuses "
                      f"{len(members)} world models trained from the same recipe "
                      f"under seeds "
                      f"{config['algorithms'][0]['world_model_ensemble_seeds']}.")
    Path(args.out).write_text(json.dumps(config, indent=2, sort_keys=False),
                              encoding="utf-8")
    print(f"wrote {args.out} with {len(config['algorithms'])} algorithm records")


if __name__ == "__main__":
    main()
