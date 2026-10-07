"""Shared opponent layout and explicit checkpoint compatibility checks."""
import numpy as np

# The seven relation features are always the first seven channels of a slot. A
# masked slot appends the occupancy mask; the dynamic-neighbourhood packing also
# appends the admission rank ahead of the mask, which is why a slot can be 7, 8
# or 9 channels wide. Rule-based policies consume the seven features either way.
SLOT_FEATURE_DIM = 7
SLOT_WIDTHS = (8, 9, 7)


def slot_width(count, masked=None, width=None):
    """Channels per opponent slot, from the number of opponent channels.

    ``masked`` states whether the layout carries an occupancy mask, which
    resolves the layouts whose channel count divides by more than one width.
    """
    if width is not None:
        width = int(width)
        if width not in SLOT_WIDTHS:
            raise ValueError(f'unknown opponent slot width {width}')
        return width
    if masked is None:
        admissible = [w for w in SLOT_WIDTHS if count % w == 0]
        if len(admissible) > 1:
            raise ValueError('Ambiguous opponent layout; provide masked explicitly')
    else:
        admissible = [w for w in ((8, 9) if masked else (7,)) if count % w == 0]
    if not admissible:
        raise ValueError('Invalid opponent layout')
    return admissible[0]


def opponent_slots(row, masked=None, width=None):
    row = np.asarray(row)
    count = row.shape[-1] - 17
    if count == 0:
        return np.empty((0, SLOT_FEATURE_DIM), dtype=row.dtype)
    width = slot_width(count, masked=masked, width=width)
    if count < 0 or count % width:
        raise ValueError('Invalid opponent layout')
    slots = row[17:].reshape(-1, width)
    if width == SLOT_FEATURE_DIM:
        return slots
    return slots[slots[:, width - 1] > 0.5, :SLOT_FEATURE_DIM]


def require_checkpoint_version(env, meta):
    version = getattr(getattr(env, 'unwrapped', None), 'telemetry_version', 'legacy_v1')
    expected = meta.get('telemetry_version', 'legacy_v1')
    # Legacy checkpoints can only be used with corrected telemetry when the
    # caller explicitly enables the recorded migration path.  This keeps
    # accidental protocol mixing impossible in normal experiments.
    migrated = bool(getattr(getattr(env, 'unwrapped', None),
                            'allow_legacy_checkpoint_migration', False))
    if version != expected and not (version == 'corrected_v2' and expected == 'legacy_v1' and migrated):
        raise ValueError('Checkpoint telemetry version differs from environment; retrain or explicitly migrate')


def rule_observation(env, obs):
    """Legacy feedback rules use right-positive lateral coordinates internally."""
    if env is None or getattr(env.unwrapped, 'telemetry_version', 'legacy_v1') != 'corrected_v2':
        return obs
    obs = np.asarray(obs)
    masked = env.unwrapped.observation_type == 'telemetry_dynamic'
    channels = obs.shape[1] - 17
    width = 7 if channels <= 0 else slot_width(channels, masked=bool(masked))
    count = (obs.shape[1] - 17) // width
    result = np.zeros((len(obs), 17 + 7 * count), dtype=obs.dtype)
    result[:, :17] = obs[:, :17]
    result[:, 12] *= -1
    for i, row in enumerate(obs):
        slots = opponent_slots(row, masked=masked, width=width).copy()
        slots[:, 1] *= -1
        result[i, 17:] = np.tile([10, 10, 0, 0, 10, 0, 1], count)
        result[i, 17:17 + slots.size] = slots.reshape(-1)
    return result
