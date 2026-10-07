"""One-step supervision preserves the opponent identities selected at real t."""
import numpy as np
from dlc.graph_policy import _rank_opponent_slots


def pack_transition_pair(obs, next_obs, neighbor_ids, next_neighbor_ids, k=3,
                         selection='interaction', priority=False):
    obs = np.asarray(obs, dtype=np.float32)
    next_obs = np.asarray(next_obs, dtype=np.float32)
    if k <= 0 or obs.shape != next_obs.shape or (obs.shape[1]-17) % 8:
        raise ValueError('Expected matching full masked observations and positive K')
    slot_out = 9 if priority else 8
    packed = np.zeros((len(obs), 17+slot_out*k), dtype=np.float32)
    successor = np.zeros_like(packed)
    packed[:, :17], successor[:, :17] = obs[:, :17], next_obs[:, :17]
    selected_ids = []
    for agent, row in enumerate(obs):
        slots = row[17:].reshape(-1, 8)
        following = next_obs[agent, 17:].reshape(-1, 8)
        ranked = _rank_opponent_slots(row, 8, True, selection,
                                      telemetry_version='corrected_v2')[:k]
        used, selected = set(), []
        for dest, features in enumerate(ranked):
            source = next(i for i, slot in enumerate(slots)
                          if i not in used and slot[7] > .5 and np.array_equal(slot[:7], features))
            used.add(source)
            identity = neighbor_ids[agent][source]
            if identity not in next_neighbor_ids[agent]:
                raise ValueError('Selected physical opponent missing in next full observation')
            following_index = next_neighbor_ids[agent].index(identity)
            start = 17+slot_out*dest
            if priority:
                # [seven relation features, admission priority, occupancy mask]
                packed[agent, start:start+7] = slots[source][:7]
                packed[agent, start+7] = 1.0 - dest / max(k-1, 1)
                packed[agent, start+8] = slots[source][7]
                successor[agent, start:start+7] = following[following_index][:7]
                successor[agent, start+7] = 1.0 - dest / max(k-1, 1)
                successor[agent, start+8] = following[following_index][7]
            else:
                packed[agent, start:start+8] = slots[source]
                successor[agent, start:start+8] = following[following_index]
            selected.append(int(identity))
        selected_ids.append(selected)
    return packed, successor, selected_ids


def promote_priority_channel(transitions, k):
    """Insert the admission rank as an eighth slot feature.

    Collection stores the seven relation features and the occupancy mask, in
    the order the admission rule ranked them. The rank is therefore recoverable
    from the slot position, and the stored dataset can serve the nine-dimension
    model without re-collecting: the promoted arrays are bit-identical to what
    ``pack_transition_pair(..., priority=True)`` would have written.
    """
    k = int(k)
    if k <= 0:
        raise ValueError('positive K required for the priority channel')
    promoted = []
    for row in transitions:
        item = dict(row)
        for key in ('obs', 'next_obs'):
            item[key] = _insert_priority(np.asarray(row[key], dtype=np.float32), k)
        promoted.append(item)
    return promoted


def _insert_priority(obs, k):
    obs = np.asarray(obs, dtype=np.float32)
    width = int(obs.shape[-1]) - 17
    if width == 9 * k:
        return obs
    if width != 8 * k:
        raise ValueError(f'expected {8 * k} or {9 * k} opponent channels, got {width}')
    slots = obs[:, 17:].reshape(len(obs), k, 8)
    out = np.zeros((len(obs), 17 + 9 * k), dtype=np.float32)
    out[:, :17] = obs[:, :17]
    block = out[:, 17:].reshape(len(obs), k, 9)
    block[..., :7] = slots[..., :7]
    rank = 1.0 - np.arange(k, dtype=np.float32) / max(k - 1, 1)
    # A slot no vehicle occupies carries no rank; the packer leaves those slots
    # empty as well, and the mask is what excludes them from the pooling.
    block[..., 7] = np.where(slots[..., 7] > 0.5, rank[None, :], 0.0)
    block[..., 8] = slots[..., 7]
    return out
