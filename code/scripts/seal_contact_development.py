"""Snapshot current stage sources and hash all retained artifacts without overwrite."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    snapshot = args.root/'final_source'
    snapshot.mkdir(exist_ok=False)
    paths = [*sorted((repo/'dlc').glob('*.py')),
             *sorted((repo/'gym_multi_car_racing').glob('*.py')),
             *sorted((repo/'tests').glob('test_corrected*.py'))]
    paths += [repo/p for p in [
        'tests/test_training_packing.py', 'tests/test_contact_guard.py', 'tests/test_algorithm_colors.py',
        'scripts/tits_figure_style.py', 'scripts/validate_corrected_protocol.py',
        'scripts/summarize_contact_development.py', 'scripts/audit_corrected_contacts.py',
        'scripts/train_graph_risk_world_model.py', 'scripts/verify_contact_development.py',
        'scripts/check_legacy_contact_replay.py', 'scripts/build_corrected_ablation_config.py',
        'scripts/seal_contact_development.py', 'docs/corrected_protocol_v2.md']]
    for relative in [
        'tests/test_joint_clearance.py', 'scripts/analyze_joint_clearance.py',
        'scripts/audit_vehicle_containment.py', 'scripts/audit_learning_transfer.py',
        'scripts/verify_joint_clearance_development.py',
        'configs/joint_clearance_development_20260910.json',
        'configs/joint_clearance_training_pilot_20260910.json',
        'configs/joint_clearance_model_pilot_20260910.json',
        'configs/graph_learning_transfer_pilot_20260910.json']:
        path = repo/relative
        if path.exists():
            paths.append(path)
    # The physical-quality pilot is a retained negative development result.
    for relative in [
        'dlc/physical_quality_pilot.py', 'tests/test_physical_quality.py',
        'scripts/verify_physical_quality_pilot.py',
        'scripts/audit_physical_quality_predictions.py',
        'configs/physical_quality_pilot_20260910.json']:
        path = repo/relative
        if path.exists():
            paths.append(path)
    for path in paths:
        dest = snapshot/path.relative_to(repo)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
    hashes = {str(p.relative_to(args.root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(args.root.rglob('*')) if p.is_file() and p.name != 'sha256_manifest.json'}
    with (args.root/'sha256_manifest.json').open('x') as file:
        json.dump(hashes, file, indent=2)
    print(json.dumps({'files_hashed': len(hashes), 'root': str(args.root)}))


if __name__ == '__main__':
    main()
