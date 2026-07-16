import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dlc.policies import TelemetryOvertakePolicy

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    nn = None


PLAYFIELD = 2000 / 6.0
EGO_DIM = 17
OPPONENT_DIM = 7
MASKED_OPPONENT_DIM = 8


def mlp(in_dim, hidden_dim, out_dim, layers=2):
    modules = []
    last_dim = int(in_dim)
    for _ in range(layers):
        modules.append(nn.Linear(last_dim, hidden_dim))
        modules.append(nn.ELU())
        last_dim = hidden_dim
    modules.append(nn.Linear(last_dim, out_dim))
    return nn.Sequential(*modules)


def wrap_to_pi(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def _opponent_fill_vector(bundle):
    meta = getattr(bundle, "meta", {}) or {}
    opponent_mean = meta.get("opponent_mean")
    if opponent_mean is None:
        return np.zeros((OPPONENT_DIM,), dtype=np.float32)
    return np.asarray(opponent_mean, dtype=np.float32)


def _bundle_obs_meta(bundle):
    meta = getattr(bundle, "meta", {}) or {}
    ego_dim = int(meta.get("ego_dim", EGO_DIM))
    opponent_dim = int(meta.get("opponent_dim", OPPONENT_DIM))
    use_slot_mask = bool(meta.get("use_slot_mask", False))
    slot_feature_dim = int(meta.get("slot_feature_dim", opponent_dim - 1 if use_slot_mask else opponent_dim))
    return ego_dim, opponent_dim, use_slot_mask, slot_feature_dim


def _slot_dim_from_obs(obs_dim, ego_dim=EGO_DIM):
    remainder = int(obs_dim) - int(ego_dim)
    if remainder <= 0:
        return None
    if remainder % MASKED_OPPONENT_DIM == 0:
        return MASKED_OPPONENT_DIM
    if remainder % OPPONENT_DIM == 0:
        return OPPONENT_DIM
    return None


def _infer_source_layout(obs_dim):
    slot_dim = _slot_dim_from_obs(obs_dim)
    if slot_dim is None:
        raise ValueError(f"observation dim {obs_dim} is incompatible with either 7-dim or masked 8-dim slots")
    use_mask = slot_dim == MASKED_OPPONENT_DIM
    feat_dim = slot_dim - 1 if use_mask else slot_dim
    return slot_dim, feat_dim, use_mask


def _rank_opponent_slots(obs_row, slot_dim=OPPONENT_DIM, use_slot_mask=False, selection_mode="legacy", radius=80.0):
    """Score opponent slots by local interaction relevance.

    Higher score means more likely to matter for imminent overtake planning.
    """
    scores = []
    selection_mode = str(selection_mode or "legacy").lower()
    slot_dim = int(slot_dim)
    feat_dim = slot_dim - 1 if use_slot_mask else slot_dim
    if feat_dim <= 0:
        return []
    for start in range(EGO_DIM, len(obs_row), slot_dim):
        slot = np.asarray(obs_row[start : start + slot_dim], dtype=np.float32)
        if slot.shape[0] < slot_dim:
            break
        if use_slot_mask:
            if float(slot[-1]) <= 0.0:
                continue
            slot = slot[:feat_dim]
        elif feat_dim != OPPONENT_DIM:
            slot = slot[:feat_dim]
        rel_forward = float(slot[0]) if feat_dim > 0 else 0.0
        rel_left = float(slot[1]) if feat_dim > 1 else 0.0
        rel_vx = float(slot[2]) if feat_dim > 2 else 0.0
        rel_vy = float(slot[3]) if feat_dim > 3 else 0.0
        distance = float(slot[4]) if feat_dim > 4 else 0.0
        heading_sin = float(slot[5]) if feat_dim > 5 else 0.0
        heading_cos = float(slot[6]) if feat_dim > 6 else 0.0
        closing_speed = max(-rel_vx, 0.0) + max(-rel_vy, 0.0)
        ttc = distance / max(closing_speed, 1e-3) if closing_speed > 1e-4 else 50.0
        heading_alignment = max(heading_cos, 0.0) - abs(heading_sin) * 0.25
        if selection_mode in {"fixed", "fixed_k", "identity", "stable"}:
            score = -float(len(scores))
        elif selection_mode in {"interaction", "traffic", "dynamic_interaction"}:
            forward_m = rel_forward * PLAYFIELD
            left_m = rel_left * PLAYFIELD
            distance_m = max(distance * PLAYFIELD, 1e-3)
            closing_mps = closing_speed * 50.0
            ahead = 0.0 < forward_m < 70.0 and abs(left_m) < 24.0
            alongside = abs(forward_m) < 14.0 and abs(left_m) < 18.0
            rear_pressure = -18.0 < forward_m <= 0.0 and abs(left_m) < 14.0 and closing_mps > 1.0
            if distance_m > float(radius) and not (ahead or alongside or rear_pressure):
                score = -1e6 - distance_m
            else:
                gap_score = 1.0 / max(distance_m / 12.0, 1.0)
                front_gap = max(0.0, 1.0 - abs(forward_m - 22.0) / 55.0) if ahead else 0.0
                lane_overlap = max(0.0, 1.0 - abs(left_m) / 18.0)
                score = (
                    3.6 * float(ahead) * front_gap
                    + 2.8 * float(alongside) * lane_overlap
                    + 1.7 * float(rear_pressure)
                    + 1.1 * gap_score
                    + 0.25 * closing_mps
                    + 0.18 * heading_alignment
                    - 0.015 * distance_m
                )
        elif selection_mode in {"nearest", "distance"}:
            score = -distance
        elif selection_mode in {"front", "ahead"}:
            score = (
                3.0 * float(rel_forward > 0.0)
                - 1.8 * abs(rel_left)
                - 0.55 * distance
                + 0.25 * closing_speed
                + 0.12 * heading_alignment
            )
        else:
            score = (
                2.8 * max(rel_forward, 0.0)
                - 1.3 * abs(rel_left)
                - 0.32 * distance
                + 0.55 / max(ttc, 1.0)
                + 0.25 * closing_speed
                + 0.18 * heading_alignment
            )
        scores.append((score, slot))
    scores.sort(key=lambda item: item[0], reverse=True)
    return [slot for score, slot in scores if score > -1e5]


def pack_dynamic_neighbor_obs(
    obs,
    fill=None,
    target_obs_dim=None,
    max_neighbors=None,
    selection_mode="legacy",
    radius=80.0,
):
    """Reorder and repack opponent slots at runtime.

    The underlying model still sees a fixed observation dimension, but the
    opponent slots are dynamically selected by relevance at every decision step.
    Missing slots are filled with the opponent mean from the bundle when available.
    """
    obs = np.asarray(obs, dtype=np.float32)
    if obs.ndim != 2:
        raise ValueError(f"expected a 2D observation, got shape {obs.shape}")
    ego_dim = EGO_DIM
    if obs.shape[1] < ego_dim:
        raise ValueError(f"expected obs dim >= {ego_dim}, got {obs.shape[1]}")
    source_slot_dim, source_feat_dim, source_use_mask = _infer_source_layout(obs.shape[1])
    source_count = (obs.shape[1] - ego_dim) // source_slot_dim
    if target_obs_dim is None:
        target_obs_dim = obs.shape[1]
    target_obs_dim = int(target_obs_dim)
    target_slot_dim, target_feat_dim, target_use_mask = _infer_source_layout(target_obs_dim)
    slot_count = (target_obs_dim - ego_dim) // target_slot_dim
    if max_neighbors is not None and int(max_neighbors) > 0:
        slot_count = min(int(max_neighbors), slot_count)
    if slot_count <= 0:
        return np.asarray(obs[:, :target_obs_dim], dtype=np.float32).copy()

    fill_vec = np.zeros((target_feat_dim,), dtype=np.float32) if fill is None else np.asarray(fill, dtype=np.float32)
    if fill_vec.shape[0] != target_feat_dim:
        if fill_vec.shape[0] > target_feat_dim:
            fill_vec = fill_vec[:target_feat_dim]
        else:
            fill_vec = np.pad(fill_vec, (0, target_feat_dim - fill_vec.shape[0]), mode="constant")
    packed = np.zeros((obs.shape[0], target_obs_dim), dtype=np.float32)
    for agent_id in range(obs.shape[0]):
        packed[agent_id, :ego_dim] = obs[agent_id, :ego_dim]
        ranked = _rank_opponent_slots(
            obs[agent_id],
            slot_dim=source_slot_dim,
            use_slot_mask=source_use_mask,
            selection_mode=selection_mode,
            radius=radius,
        )[:slot_count]
        for slot_id in range(slot_count):
            dst = ego_dim + slot_id * target_slot_dim
            if slot_id < len(ranked):
                slot = np.asarray(ranked[slot_id], dtype=np.float32)
                if not target_use_mask and slot.shape[0] == target_feat_dim:
                    packed[agent_id, dst : dst + target_slot_dim] = slot
                elif target_use_mask and slot.shape[0] == target_feat_dim:
                    packed[agent_id, dst : dst + slot.shape[0]] = slot
                    packed[agent_id, dst + slot.shape[0]] = 1.0
                else:
                    feat_len = min(slot.shape[0], target_feat_dim)
                    packed[agent_id, dst : dst + feat_len] = slot[:feat_len]
                    if target_use_mask:
                        packed[agent_id, dst + target_feat_dim] = 1.0
            else:
                packed[agent_id, dst : dst + target_feat_dim] = fill_vec
                if target_use_mask:
                    packed[agent_id, dst + target_feat_dim] = 0.0
    return packed


def randomize_neighbor_slots(obs, keep_prob=1.0, max_neighbors=None, seed=None):
    """Stochastically drop opponent slots during training.

    This encourages the actor to rely on a variable number of nearby vehicles
    rather than overfitting to a specific car count or slot index.
    """
    obs = np.asarray(obs, dtype=np.float32)
    if keep_prob >= 1.0:
        return obs.copy()
    rng = np.random.default_rng(seed)
    randomized = obs.copy()
    slot_dim = _slot_dim_from_obs(obs.shape[-1])
    if slot_dim is None:
        return randomized
    if max_neighbors is None:
        max_neighbors = (obs.shape[-1] - EGO_DIM) // slot_dim
    max_neighbors = min(max_neighbors, (obs.shape[-1] - EGO_DIM) // slot_dim)
    if max_neighbors <= 0:
        return randomized
    for agent_id in range(obs.shape[0]):
        for slot_id in range(max_neighbors):
            if rng.random() > keep_prob:
                start = EGO_DIM + slot_id * slot_dim
                if slot_dim == MASKED_OPPONENT_DIM:
                    randomized[agent_id, start : start + slot_dim - 1] = 0.0
                    randomized[agent_id, start + slot_dim - 1] = 0.0
                else:
                    randomized[agent_id, start : start + slot_dim] = 0.0
    return randomized


class PermutationInvariantActor(nn.Module):
    """Set/GNN-style actor for variable-size multi-car telemetry.

    Each agent is encoded from its ego features plus a pooled embedding of all
    opponents. The architecture is order-invariant over opponent slots, so a
    policy trained with one car count can be evaluated with another car count
    after compatible normalization.
    """

    def __init__(self, ego_dim=EGO_DIM, opponent_dim=OPPONENT_DIM, hidden_dim=128, action_dim=3, use_slot_mask=False, slot_feature_dim=None):
        super().__init__()
        self.ego_dim = int(ego_dim)
        self.opponent_dim = int(opponent_dim)
        self.hidden_dim = int(hidden_dim)
        self.action_dim = int(action_dim)
        self.use_slot_mask = bool(use_slot_mask)
        self.slot_feature_dim = int(slot_feature_dim if slot_feature_dim is not None else (self.opponent_dim - 1 if self.use_slot_mask else self.opponent_dim))
        self.ego_encoder = mlp(self.ego_dim, hidden_dim, hidden_dim)
        self.opponent_encoder = mlp(self.slot_feature_dim, hidden_dim, hidden_dim)
        self.actor = mlp(2 * hidden_dim, hidden_dim, action_dim)

    def forward(self, obs):
        ego = obs[..., : self.ego_dim]
        opponent = obs[..., self.ego_dim :]
        batch_shape = ego.shape[:-1]
        ego_emb = self.ego_encoder(ego)
        if opponent.shape[-1] == 0:
            pooled = torch.zeros(*batch_shape, self.hidden_dim, device=obs.device, dtype=obs.dtype)
        else:
            opponent = opponent.reshape(*batch_shape, -1, self.opponent_dim)
            if self.use_slot_mask:
                mask = opponent[..., -1:]
                opponent = opponent[..., : self.slot_feature_dim]
                opp_emb = self.opponent_encoder(opponent) * mask
                pooled = opp_emb.sum(dim=-2) / mask.sum(dim=-2).clamp_min(1.0)
            else:
                opp_emb = self.opponent_encoder(opponent)
                pooled = opp_emb.mean(dim=-2)
        raw = self.actor(torch.cat([ego_emb, pooled], dim=-1))
        steer = torch.tanh(raw[..., 0:1])
        gas = torch.sigmoid(raw[..., 1:2])
        brake = torch.sigmoid(raw[..., 2:3])
        return torch.cat([steer, gas, brake], dim=-1)


@dataclass
class GraphActorBundle:
    actor: PermutationInvariantActor
    obs_mean: np.ndarray
    obs_std: np.ndarray
    meta: dict

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "actor": self.actor.state_dict(),
                "obs_mean": self.obs_mean,
                "obs_std": self.obs_std,
                "meta": self.meta,
            },
            path,
        )

    @classmethod
    def load(cls, path, map_location="cpu"):
        data = torch.load(path, map_location=map_location, weights_only=False)
        meta = data["meta"]
        actor = PermutationInvariantActor(
            ego_dim=meta.get("ego_dim", EGO_DIM),
            opponent_dim=meta.get("opponent_dim", OPPONENT_DIM),
            hidden_dim=meta.get("hidden_dim", 128),
            action_dim=meta.get("action_dim", 3),
            use_slot_mask=meta.get("use_slot_mask", False),
            slot_feature_dim=meta.get("slot_feature_dim"),
        )
        actor.load_state_dict(data["actor"])
        actor.eval()
        return cls(actor=actor, obs_mean=data["obs_mean"], obs_std=data["obs_std"], meta=meta)

    def normalize_obs(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        if "ego_mean" not in self.meta:
            return (obs - self.obs_mean) / self.obs_std

        ego_dim = int(self.meta.get("ego_dim", 17))
        opponent_dim = int(self.meta.get("opponent_dim", OPPONENT_DIM))
        use_slot_mask = bool(self.meta.get("use_slot_mask", False))
        slot_feature_dim = int(self.meta.get("slot_feature_dim", opponent_dim - 1 if use_slot_mask else opponent_dim))
        normalized = np.zeros_like(obs, dtype=np.float32)
        normalized[..., :ego_dim] = (
            obs[..., :ego_dim] - np.asarray(self.meta["ego_mean"], dtype=np.float32)
        ) / np.asarray(self.meta["ego_std"], dtype=np.float32)
        opponent = obs[..., ego_dim:]
        if opponent.shape[-1] > 0:
            opponent = opponent.reshape(*opponent.shape[:-1], -1, opponent_dim)
            if use_slot_mask:
                features = opponent[..., :slot_feature_dim]
                mask = opponent[..., slot_feature_dim:]
                features = (
                    features - np.asarray(self.meta["opponent_mean"], dtype=np.float32)
                ) / np.asarray(self.meta["opponent_std"], dtype=np.float32)
                normalized[..., ego_dim:] = np.concatenate([features, mask], axis=-1).reshape(*normalized[..., ego_dim:].shape)
            else:
                opponent = (
                    opponent - np.asarray(self.meta["opponent_mean"], dtype=np.float32)
                ) / np.asarray(self.meta["opponent_std"], dtype=np.float32)
                normalized[..., ego_dim:] = opponent.reshape(*normalized[..., ego_dim:].shape)
        return normalized


class GraphActorPolicy:
    def __init__(self, model_path, device="cpu", neighbor_mode="fixed", max_neighbors=None, neighbor_selection_mode="legacy"):
        if torch is None:
            raise ImportError("GraphActorPolicy requires torch")
        self.device = torch.device(device)
        self.bundle = GraphActorBundle.load(model_path, map_location=self.device)
        self.bundle.actor.to(self.device)
        self.name = self.bundle.meta.get("name", "graph_actor")
        self.neighbor_mode = str(neighbor_mode)
        self.max_neighbors = None if max_neighbors is None else int(max_neighbors)
        self.neighbor_selection_mode = str(neighbor_selection_mode or "legacy")
        self.expected_obs_dim = int(self.bundle.meta.get("obs_dim", self.bundle.obs_mean.shape[-1]))
        self.bundle_use_slot_mask = bool(self.bundle.meta.get("use_slot_mask", False))
        self.bundle_slot_dim = int(self.bundle.meta.get("opponent_dim", OPPONENT_DIM))

    def reset(self):
        pass

    def act(self, env, obs):
        del env
        if self.neighbor_mode == "dynamic":
            target_obs_dim = obs.shape[1] if self.max_neighbors is None or self.max_neighbors <= 0 else self.expected_obs_dim
            obs = pack_dynamic_neighbor_obs(
                obs,
                fill=_opponent_fill_vector(self.bundle),
                target_obs_dim=target_obs_dim,
                max_neighbors=self.max_neighbors,
                selection_mode=self.neighbor_selection_mode,
            )
        normalized = self.bundle.normalize_obs(obs)
        obs_tensor = torch.as_tensor(normalized, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            action = self.bundle.actor(obs_tensor).cpu().numpy()
        return np.asarray(action, dtype=np.float32)


class SafetyShieldPolicy:
    def __init__(
        self,
        learned_policy,
        fallback_policy=None,
        unsafe_blend=1.0,
        safe_blend=0.25,
        lateral_threshold=0.55,
        heading_cos_threshold=0.70,
        min_forward_gap=0.05,
        action_disagreement_threshold=0.35,
        hard_intervention=False,
        emergency_lateral_threshold=0.78,
        stall_patience=160,
        stall_progress_epsilon=0.002,
        stall_min_speed=4.0,
        close_forward_gap=0.025,
        close_lateral_gap=0.025,
    ):
        self.learned_policy = learned_policy
        self.fallback_policy = fallback_policy or TelemetryOvertakePolicy()
        self.unsafe_blend = float(unsafe_blend)
        self.safe_blend = float(safe_blend)
        self.lateral_threshold = float(lateral_threshold)
        self.heading_cos_threshold = float(heading_cos_threshold)
        self.min_forward_gap = float(min_forward_gap)
        self.action_disagreement_threshold = float(action_disagreement_threshold)
        self.hard_intervention = bool(hard_intervention)
        self.emergency_lateral_threshold = float(emergency_lateral_threshold)
        self.stall_patience = int(stall_patience)
        self.stall_progress_epsilon = float(stall_progress_epsilon)
        self.stall_min_speed = float(stall_min_speed)
        self.close_forward_gap = float(close_forward_gap)
        self.close_lateral_gap = float(close_lateral_gap)
        self.last_progress = None
        self.stall_steps = None
        self.name = f"shield_{learned_policy.name}"

    def reset(self):
        self.learned_policy.reset()
        self.fallback_policy.reset()
        self.last_progress = None
        self.stall_steps = None

    def _ensure_state(self, num_agents):
        if self.last_progress is None or len(self.last_progress) != num_agents:
            self.last_progress = np.zeros(num_agents, dtype=np.float32)
            self.stall_steps = np.zeros(num_agents, dtype=np.int32)

    def _update_stall_state(self, obs_array):
        num_agents = obs_array.shape[0]
        self._ensure_state(num_agents)
        progress = obs_array[:, 9]
        speed = obs_array[:, 4] * 50.0
        improved = progress > (self.last_progress + self.stall_progress_epsilon)
        stalled_speed = speed < self.stall_min_speed
        self.stall_steps[improved] = 0
        self.stall_steps[~improved & stalled_speed] += 1
        self.stall_steps[~improved & ~stalled_speed] = np.maximum(
            self.stall_steps[~improved & ~stalled_speed] - 1,
            0,
        )
        self.last_progress = np.maximum(self.last_progress, progress)

    def _project_action(self, obs_row, action, fallback_action, emergency=False, stall=False, close_ahead=False):
        projected = np.asarray(action, dtype=np.float32).copy()
        fallback_action = np.asarray(fallback_action, dtype=np.float32)

        lateral = float(obs_row[12])
        heading_error = math.atan2(float(obs_row[13]), float(obs_row[14]))
        heading_cos = float(obs_row[14])
        on_grass = float(obs_row[15]) > 0.5
        backward = float(obs_row[16]) > 0.5

        corrective_steer = -np.clip(1.7 * heading_error + 0.85 * lateral, -1.0, 1.0)
        if abs(lateral) > self.lateral_threshold or heading_cos < self.heading_cos_threshold:
            if abs(corrective_steer) > abs(projected[0]) or np.sign(corrective_steer) != np.sign(projected[0]):
                projected[0] = corrective_steer

        if emergency or on_grass or backward:
            projected = fallback_action.copy()
            projected[0] = corrective_steer
            if backward or heading_cos < 0.25:
                projected[1] = min(float(projected[1]), 0.12)
                projected[2] = max(float(projected[2]), 0.45)
            else:
                projected[1] = max(float(projected[1]), 0.45)
                projected[2] = min(float(projected[2]), 0.05)

        if heading_cos < 0.25 or backward:
            projected[1] = min(float(projected[1]), 0.12)
            projected[2] = max(float(projected[2]), 0.45)

        if close_ahead:
            projected[1] = min(float(projected[1]), 0.12)
            projected[2] = max(float(projected[2]), 0.35)

        if stall:
            projected = fallback_action.copy()
            projected[0] = corrective_steer if abs(lateral) > 0.25 else fallback_action[0]
            projected[1] = max(float(projected[1]), 0.55)
            projected[2] = min(float(projected[2]), 0.05)

        projected[0] = np.clip(projected[0], -1.0, 1.0)
        projected[1:] = np.clip(projected[1:], 0.0, 1.0)
        return projected

    def act(self, env, obs):
        learned = self.learned_policy.act(env, obs)
        fallback = self.fallback_policy.act(env, obs)
        obs_array = np.asarray(obs, dtype=np.float32)
        blend = np.full((obs_array.shape[0], 1), self.safe_blend, dtype=np.float32)
        self._update_stall_state(obs_array)
        hard_mask = np.zeros(obs_array.shape[0], dtype=bool)

        for agent_id in range(obs_array.shape[0]):
            close_ahead = False
            unsafe = (
                abs(float(obs_array[agent_id, 12])) > self.lateral_threshold
                or float(obs_array[agent_id, 14]) < self.heading_cos_threshold
                or float(obs_array[agent_id, 15]) > 0.5
                or float(obs_array[agent_id, 16]) > 0.5
            )
            for start in range(17, obs_array.shape[1], 7):
                rel_forward = float(obs_array[agent_id, start])
                rel_left = float(obs_array[agent_id, start + 1])
                close_ahead = close_ahead or (
                    0.0 < rel_forward < min(self.min_forward_gap, self.close_forward_gap)
                    and abs(rel_left) < self.close_lateral_gap
                )
                unsafe = unsafe or (self.hard_intervention and close_ahead)
            action_gap = float(np.linalg.norm(learned[agent_id] - fallback[agent_id]))
            unsafe = unsafe or action_gap > self.action_disagreement_threshold
            emergency = (
                abs(float(obs_array[agent_id, 12])) > self.emergency_lateral_threshold
                or float(obs_array[agent_id, 15]) > 0.5
                or float(obs_array[agent_id, 16]) > 0.5
            )
            stall = bool(self.stall_steps[agent_id] >= self.stall_patience)
            hard_mask[agent_id] = emergency or stall or (self.hard_intervention and close_ahead)
            if unsafe:
                blend[agent_id, 0] = self.unsafe_blend

        action = blend * fallback + (1.0 - blend) * learned
        if self.hard_intervention:
            for agent_id in range(obs_array.shape[0]):
                if hard_mask[agent_id] or abs(float(obs_array[agent_id, 12])) > self.lateral_threshold:
                    action[agent_id] = self._project_action(
                        obs_array[agent_id],
                        action[agent_id],
                        fallback[agent_id],
                        emergency=(
                            abs(float(obs_array[agent_id, 12])) > self.emergency_lateral_threshold
                            or float(obs_array[agent_id, 15]) > 0.5
                            or float(obs_array[agent_id, 16]) > 0.5
                        ),
                        stall=bool(self.stall_steps[agent_id] >= self.stall_patience),
                        close_ahead=hard_mask[agent_id],
                    )
        action[:, 0] = np.clip(action[:, 0], -1.0, 1.0)
        action[:, 1:] = np.clip(action[:, 1:], 0.0, 1.0)
        return action.astype(np.float32)


def make_untrained_graph_bundle(obs_dim, hidden_dim=128, seed=0, use_slot_mask=False, slot_feature_dim=OPPONENT_DIM):
    if torch is None:
        raise ImportError("make_untrained_graph_bundle requires torch")
    torch.manual_seed(seed)
    obs_mean = np.zeros((obs_dim,), dtype=np.float32)
    obs_std = np.ones((obs_dim,), dtype=np.float32)
    actor = PermutationInvariantActor(
        hidden_dim=hidden_dim,
        opponent_dim=(slot_feature_dim + 1) if use_slot_mask else OPPONENT_DIM,
        use_slot_mask=use_slot_mask,
        slot_feature_dim=slot_feature_dim,
    )
    return GraphActorBundle(
        actor=actor,
        obs_mean=obs_mean,
        obs_std=obs_std,
        meta={
            "name": "graph_actor_untrained",
            "ego_dim": EGO_DIM,
            "opponent_dim": (slot_feature_dim + 1) if use_slot_mask else OPPONENT_DIM,
            "hidden_dim": hidden_dim,
            "action_dim": 3,
            "obs_dim": obs_dim,
            "use_slot_mask": bool(use_slot_mask),
            "slot_feature_dim": int(slot_feature_dim),
            "source": "permutation_invariant_multicar_actor",
        },
    )
