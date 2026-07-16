import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dlc.graph_policy import GraphActorBundle, PermutationInvariantActor, pack_dynamic_neighbor_obs, _opponent_fill_vector
from dlc.policies import (
    TelemetryAdaptiveGatePolicy,
    TelemetryBarrierExpertGatePolicy,
    TelemetryConservativeAdaptivePolicy,
    TelemetryCruisePolicy,
    TelemetryExpertGatePolicy,
    TelemetryFastExpertGatePolicy,
    TelemetryLanePolicy,
    TelemetryOvertakePolicy,
    TelemetryRecoveryAdaptivePolicy,
    TelemetryRecoveryExpertGatePolicy,
    TelemetryYieldPolicy,
    TrackFollowPolicy,
)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    torch = None
    nn = None
    F = None


EGO_DIM = 17
RELATION_DIM = 7
MASKED_RELATION_DIM = 8
PLAYFIELD = 2000 / 6.0


def wrap_to_pi(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def mlp(in_dim, hidden_dim, out_dim, layers=2):
    modules = []
    last_dim = int(in_dim)
    for _ in range(layers):
        modules.append(nn.Linear(last_dim, hidden_dim))
        modules.append(nn.ELU())
        last_dim = hidden_dim
    modules.append(nn.Linear(last_dim, out_dim))
    return nn.Sequential(*modules)


def gaussian_nll(mu, logvar, target):
    logvar = torch.clamp(logvar, -6.0, 3.0)
    return 0.5 * (torch.exp(-logvar) * (target - mu).square() + logvar)


def normalize_items(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def make_background_policy(name, agent_id):
    speeds = [14.0, 15.0, 16.0, 17.0]
    if name == "telemetry_lane":
        return TelemetryLanePolicy(target_speed=speeds[agent_id % len(speeds)], name=f"telemetry_lane_{agent_id}")
    if name == "telemetry_cruise":
        return TelemetryCruisePolicy(target_speed=[13.0, 14.5, 16.0, 17.0][agent_id % 4], name=f"telemetry_cruise_{agent_id}")
    if name == "telemetry_yield":
        return TelemetryYieldPolicy(target_speed=speeds[agent_id % len(speeds)], yield_speed=10.5, name=f"telemetry_yield_{agent_id}")
    if name == "telemetry_overtake":
        speed = speeds[agent_id % len(speeds)]
        return TelemetryOvertakePolicy(target_speed=speed, pass_speed=speed + 3.0, lane_offset=0.0, pass_lane_offset=1.0, name=f"telemetry_overtake_{agent_id}")
    if name == "telemetry_adaptive":
        speed = speeds[agent_id % len(speeds)]
        return TelemetryAdaptiveGatePolicy(target_speed=speed, pass_speed=speed + 3.0, lane_offset=0.0, pass_lane_offset=1.0, name=f"telemetry_adaptive_{agent_id}")
    if name == "telemetry_adaptive_recovery":
        speed = speeds[agent_id % len(speeds)]
        return TelemetryRecoveryAdaptivePolicy(target_speed=speed, pass_speed=speed + 3.0, lane_offset=0.0, name=f"telemetry_adaptive_recovery_{agent_id}")
    if name == "telemetry_adaptive_conservative":
        speed = [12.5, 13.5, 14.5, 15.5][agent_id % 4]
        return TelemetryConservativeAdaptivePolicy(target_speed=speed, pass_speed=speed + 2.0, lane_offset=0.0, name=f"telemetry_adaptive_conservative_{agent_id}")
    if name == "telemetry_expert_gate":
        return TelemetryExpertGatePolicy(name=f"telemetry_expert_gate_{agent_id}")
    if name == "telemetry_expert_fast":
        return TelemetryFastExpertGatePolicy(name=f"telemetry_expert_fast_{agent_id}")
    if name == "telemetry_expert_barrier":
        return TelemetryBarrierExpertGatePolicy(name=f"telemetry_expert_barrier_{agent_id}")
    if name == "telemetry_expert_recovery":
        return TelemetryRecoveryExpertGatePolicy(name=f"telemetry_expert_recovery_{agent_id}")
    raise ValueError(f"unknown background policy: {name}")


class GraphTransitionModel(nn.Module):
    def __init__(
        self,
        obs_dim,
        action_dim,
        num_agents=4,
        hidden_dim=256,
        pooling_mode="attention",
        use_slot_mask=False,
        slot_feature_dim=RELATION_DIM,
        quality_dim=4,
    ):
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.num_agents = int(num_agents)
        self.hidden_dim = int(hidden_dim)
        self.pooling_mode = str(pooling_mode)
        self.use_slot_mask = bool(use_slot_mask)
        self.slot_feature_dim = int(slot_feature_dim)
        self.quality_dim = int(quality_dim)
        self.relation_dim = self.slot_feature_dim + 1 if self.use_slot_mask else RELATION_DIM
        self.node_encoder = mlp(EGO_DIM, hidden_dim, hidden_dim)
        self.relation_encoder = mlp(self.slot_feature_dim, hidden_dim, hidden_dim)
        self.action_encoder = mlp(action_dim, hidden_dim, hidden_dim)
        self.relation_attention = nn.Linear(hidden_dim, 1)
        self.fuse = mlp(5 * hidden_dim, hidden_dim, hidden_dim)
        self.next_head = nn.Linear(hidden_dim, obs_dim)
        self.next_logvar_head = nn.Linear(hidden_dim, 1)
        self.reward_head = nn.Linear(hidden_dim, 1)
        self.reward_logvar_head = nn.Linear(hidden_dim, 1)
        self.risk_head = nn.Linear(hidden_dim, 1)
        self.quality_head = nn.Linear(hidden_dim, self.quality_dim) if self.quality_dim > 0 else None

    def forward(self, obs, action):
        ego = obs[..., :EGO_DIM]
        rel = obs[..., EGO_DIM:]
        batch_shape = ego.shape[:-1]
        node = self.node_encoder(ego)
        act = self.action_encoder(action)

        if rel.shape[-1] == 0:
            rel_ctx = torch.zeros(*batch_shape, self.hidden_dim, device=obs.device, dtype=obs.dtype)
            attn_entropy = torch.zeros(*batch_shape, device=obs.device, dtype=obs.dtype)
        else:
            rel = rel.reshape(*batch_shape, -1, self.relation_dim)
            if self.use_slot_mask:
                mask = rel[..., -1:]
                rel = rel[..., : self.slot_feature_dim]
                rel_emb = self.relation_encoder(rel) * mask
                valid = mask.sum(dim=-2).clamp_min(1.0)
                rel_ctx = rel_emb.sum(dim=-2) / valid
                weights = mask.squeeze(-1)
                attn_entropy = -(weights * torch.log(weights.clamp_min(1e-6))).sum(dim=-1)
            else:
                rel_emb = self.relation_encoder(rel)
                if self.pooling_mode == "mean":
                    weights = torch.full(
                        rel_emb.shape[:-1],
                        1.0 / max(rel_emb.shape[-2], 1),
                        device=obs.device,
                        dtype=obs.dtype,
                    )
                else:
                    logits = self.relation_attention(rel_emb).squeeze(-1)
                    weights = torch.softmax(logits, dim=-1)
                rel_ctx = (rel_emb * weights.unsqueeze(-1)).sum(dim=-2)
                attn_entropy = -(weights * torch.log(weights.clamp_min(1e-6))).sum(dim=-1)

        global_node = node.mean(dim=-2, keepdim=True).expand(-1, node.shape[-2], -1)
        global_action = act.mean(dim=-2, keepdim=True).expand(-1, act.shape[-2], -1)
        fused = self.fuse(torch.cat([node, rel_ctx, act, torch.cat([global_node, global_action], dim=-1)], dim=-1))

        next_mu = self.next_head(fused)
        next_logvar = self.next_logvar_head(fused)
        reward_mu = self.reward_head(fused).squeeze(-1)
        reward_logvar = self.reward_logvar_head(fused).squeeze(-1)
        risk_logits = self.risk_head(fused).squeeze(-1)
        quality_pred = self.quality_head(fused) if self.quality_head is not None else None
        return {
            "next_mu": next_mu,
            "next_logvar": next_logvar,
            "reward_mu": reward_mu,
            "reward_logvar": reward_logvar,
            "risk_logits": risk_logits,
            "quality_pred": quality_pred,
            "attn_entropy": attn_entropy,
        }


@dataclass
class GraphWorldModelBundle:
    transition: GraphTransitionModel
    proposal_actor: PermutationInvariantActor
    obs_mean: np.ndarray
    obs_std: np.ndarray
    action_mean: np.ndarray
    action_std: np.ndarray
    meta: dict

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "transition": self.transition.state_dict(),
                "proposal_actor": self.proposal_actor.state_dict(),
                "obs_mean": self.obs_mean,
                "obs_std": self.obs_std,
                "action_mean": self.action_mean,
                "action_std": self.action_std,
                "meta": self.meta,
            },
            path,
        )

    @classmethod
    def load(cls, path, map_location="cpu"):
        data = torch.load(path, map_location=map_location, weights_only=False)
        meta = data["meta"]
        transition = GraphTransitionModel(
            obs_dim=meta["obs_dim"],
            action_dim=meta["action_dim"],
            num_agents=meta["num_agents"],
            hidden_dim=meta["hidden_dim"],
            pooling_mode=meta.get("pooling_mode", "attention"),
            use_slot_mask=meta.get("use_slot_mask", False),
            slot_feature_dim=meta.get("slot_feature_dim", RELATION_DIM),
            quality_dim=meta.get("quality_dim", 4),
        )
        transition.load_state_dict(data["transition"], strict=False)
        proposal_actor = PermutationInvariantActor(
            ego_dim=meta.get("ego_dim", EGO_DIM),
            opponent_dim=meta.get("opponent_dim", RELATION_DIM),
            hidden_dim=meta.get("proposal_hidden_dim", meta["hidden_dim"]),
            action_dim=meta["action_dim"],
            use_slot_mask=meta.get("use_slot_mask", False),
            slot_feature_dim=meta.get("slot_feature_dim", RELATION_DIM),
        )
        proposal_actor.load_state_dict(data["proposal_actor"])
        transition.eval()
        proposal_actor.eval()
        return cls(
            transition=transition,
            proposal_actor=proposal_actor,
            obs_mean=data["obs_mean"],
            obs_std=data["obs_std"],
            action_mean=data["action_mean"],
            action_std=data["action_std"],
            meta=meta,
        )

    def normalize_obs(self, obs):
        if "ego_mean" in self.meta:
            return self._normalize_structured_obs(obs)
        return (np.asarray(obs, dtype=np.float32) - self.obs_mean) / self.obs_std

    def denormalize_obs(self, obs):
        if "ego_mean" in self.meta:
            return self._denormalize_structured_obs(obs)
        return np.asarray(obs, dtype=np.float32) * self.obs_std + self.obs_mean

    def _normalize_structured_obs(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        ego_dim = int(self.meta.get("ego_dim", EGO_DIM))
        opponent_dim = int(self.meta.get("opponent_dim", RELATION_DIM))
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
                opponent = np.concatenate([features, mask], axis=-1)
            else:
                opponent = (
                    opponent - np.asarray(self.meta["opponent_mean"], dtype=np.float32)
                ) / np.asarray(self.meta["opponent_std"], dtype=np.float32)
            normalized[..., ego_dim:] = opponent.reshape(*normalized[..., ego_dim:].shape)
        return normalized

    def _denormalize_structured_obs(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        ego_dim = int(self.meta.get("ego_dim", EGO_DIM))
        opponent_dim = int(self.meta.get("opponent_dim", RELATION_DIM))
        use_slot_mask = bool(self.meta.get("use_slot_mask", False))
        slot_feature_dim = int(self.meta.get("slot_feature_dim", opponent_dim - 1 if use_slot_mask else opponent_dim))
        denorm = np.zeros_like(obs, dtype=np.float32)
        denorm[..., :ego_dim] = (
            obs[..., :ego_dim] * np.asarray(self.meta["ego_std"], dtype=np.float32)
        ) + np.asarray(self.meta["ego_mean"], dtype=np.float32)
        opponent = obs[..., ego_dim:]
        if opponent.shape[-1] > 0:
            opponent = opponent.reshape(*opponent.shape[:-1], -1, opponent_dim)
            if use_slot_mask:
                features = opponent[..., :slot_feature_dim]
                mask = opponent[..., slot_feature_dim:]
                features = (
                    features * np.asarray(self.meta["opponent_std"], dtype=np.float32)
                ) + np.asarray(self.meta["opponent_mean"], dtype=np.float32)
                opponent = np.concatenate([features, np.clip(mask, 0.0, 1.0)], axis=-1)
            else:
                opponent = (
                    opponent * np.asarray(self.meta["opponent_std"], dtype=np.float32)
                ) + np.asarray(self.meta["opponent_mean"], dtype=np.float32)
            denorm[..., ego_dim:] = opponent.reshape(*denorm[..., ego_dim:].shape)
        return denorm

    def normalize_action(self, action):
        return (np.asarray(action, dtype=np.float32) - self.action_mean) / self.action_std

    def denormalize_action(self, action):
        return np.asarray(action, dtype=np.float32) * self.action_std + self.action_mean


class GraphWorldModelPolicy:
    def __init__(
        self,
        model_path,
        device="cpu",
        neighbor_mode="fixed",
        max_neighbors=None,
        neighbor_selection_mode="legacy",
        planner_horizon=None,
        planner_candidates=None,
        planner_risk_weight=None,
        planner_progress_weight=None,
        planner_uncertainty_weight=None,
        planner_overtake_weight=None,
        planner_lane_weight=None,
        planner_grass_weight=None,
        planner_close_gap_weight=None,
        overtake_aware_planner=None,
        quality_proposal_path=None,
        quality_planner_mode="proposal_only",
        quality_rollout_blend=None,
        quality_overtake_weight=None,
        quality_lane_weight=None,
        quality_grass_weight=None,
        quality_close_gap_weight=None,
        learned_quality_weight=None,
        learned_quality_gate=False,
        learned_quality_min_on_track=0.45,
        learned_quality_max_grass=0.55,
        learned_quality_max_lane_error=0.72,
        learned_quality_gate_penalty=2.0,
        elegance_barrier=False,
        elegance_barrier_weight=1.0,
        elegance_lateral_limit=0.30,
        elegance_heading_cos_min=0.82,
        elegance_grass_penalty=2.0,
        elegance_backward_penalty=1.2,
        elegance_close_gap_limit=8.0,
        geometry_generalization=False,
        geometry_curvature_lookahead=8,
        geometry_curvature_speed_weight=18.0,
        geometry_lateral_speed_weight=4.5,
        geometry_heading_speed_weight=5.0,
        geometry_min_speed=9.5,
        geometry_anchor_blend=0.35,
        geometry_barrier_weight=0.65,
        hard_safety_shield=None,
        use_rule_anchor=True,
        use_handcrafted_candidates=True,
        use_geometry_recovery=True,
    ):
        if torch is None:
            raise ImportError("GraphWorldModelPolicy requires torch")
        self.device = torch.device(device)
        self.bundle = GraphWorldModelBundle.load(model_path, map_location=self.device)
        self.bundle.transition.to(self.device)
        self.bundle.proposal_actor.to(self.device)
        self.quality_bundle = None
        self.quality_expected_obs_dim = None
        if quality_proposal_path:
            self.quality_bundle = GraphActorBundle.load(quality_proposal_path, map_location=self.device)
            self.quality_bundle.actor.to(self.device)
            self.quality_expected_obs_dim = int(
                self.quality_bundle.meta.get("obs_dim", self.quality_bundle.obs_mean.shape[-1])
            )
        self.name = self.bundle.meta.get("name", "graph_world_model")
        self.neighbor_mode = str(neighbor_mode)
        self.max_neighbors = None if max_neighbors is None else int(max_neighbors)
        self.neighbor_selection_mode = str(neighbor_selection_mode or "legacy")
        self.target_agent = int(self.bundle.meta.get("target_agent", max(self.bundle.meta.get("num_agents", 2) - 1, 0)))
        self.target_agent_mode = str(self.bundle.meta.get("target_agent_mode", "last"))
        self.background_policy_names = normalize_items(
            self.bundle.meta.get("background_policies", "telemetry_cruise,telemetry_yield,telemetry_lane")
        )
        self.horizon = int(self.bundle.meta.get("planner_horizon", 5) if planner_horizon is None else planner_horizon)
        self.candidates = int(self.bundle.meta.get("planner_candidates", 16) if planner_candidates is None else planner_candidates)
        self.risk_weight = float(self.bundle.meta.get("risk_weight", 1.4) if planner_risk_weight is None else planner_risk_weight)
        self.uncertainty_weight = float(
            self.bundle.meta.get("uncertainty_weight", 0.35)
            if planner_uncertainty_weight is None
            else planner_uncertainty_weight
        )
        self.progress_weight = float(
            self.bundle.meta.get("progress_weight", 1.0)
            if planner_progress_weight is None
            else planner_progress_weight
        )
        self.imitation_weight = float(self.bundle.meta.get("imitation_weight", 0.08))
        self.gamma = float(self.bundle.meta.get("planner_discount", 0.985))
        self.profile = self.bundle.meta.get("planner_profile", "risk_aware")
        default_overtake_aware = bool(self.bundle.meta.get("use_slot_mask", False))
        if overtake_aware_planner is None:
            overtake_aware_planner = self.bundle.meta.get("overtake_aware_planner", default_overtake_aware)
        self.overtake_aware_planner = bool(overtake_aware_planner)
        self.overtake_weight = float(self.bundle.meta.get("overtake_weight", 2.4) if planner_overtake_weight is None else planner_overtake_weight)
        self.lane_quality_weight = float(self.bundle.meta.get("lane_quality_weight", 0.42) if planner_lane_weight is None else planner_lane_weight)
        self.grass_penalty_weight = float(self.bundle.meta.get("grass_penalty_weight", 2.0) if planner_grass_weight is None else planner_grass_weight)
        self.close_gap_penalty_weight = float(self.bundle.meta.get("close_gap_penalty_weight", 0.65) if planner_close_gap_weight is None else planner_close_gap_weight)
        self.quality_planner_mode = str(quality_planner_mode or "proposal_only")
        self.quality_rollout_blend = float(
            self.bundle.meta.get("quality_rollout_blend", 0.0)
            if quality_rollout_blend is None
            else quality_rollout_blend
        )
        self.quality_overtake_weight = float(
            self.bundle.meta.get("quality_overtake_weight", 0.0)
            if quality_overtake_weight is None
            else quality_overtake_weight
        )
        self.quality_lane_weight = float(
            self.bundle.meta.get("quality_lane_weight", 0.0)
            if quality_lane_weight is None
            else quality_lane_weight
        )
        self.quality_grass_weight = float(
            self.bundle.meta.get("quality_grass_weight", 0.0)
            if quality_grass_weight is None
            else quality_grass_weight
        )
        self.quality_close_gap_weight = float(
            self.bundle.meta.get("quality_close_gap_weight", 0.0)
            if quality_close_gap_weight is None
            else quality_close_gap_weight
        )
        self.learned_quality_weight = float(
            self.bundle.meta.get("learned_quality_weight", 0.0)
            if learned_quality_weight is None
            else learned_quality_weight
        )
        self.learned_quality_gate = bool(learned_quality_gate)
        self.learned_quality_min_on_track = float(learned_quality_min_on_track)
        self.learned_quality_max_grass = float(learned_quality_max_grass)
        self.learned_quality_max_lane_error = float(learned_quality_max_lane_error)
        self.learned_quality_gate_penalty = float(learned_quality_gate_penalty)
        self.elegance_barrier = bool(elegance_barrier)
        self.elegance_barrier_weight = float(elegance_barrier_weight)
        self.elegance_lateral_limit = float(elegance_lateral_limit)
        self.elegance_heading_cos_min = float(elegance_heading_cos_min)
        self.elegance_grass_penalty = float(elegance_grass_penalty)
        self.elegance_backward_penalty = float(elegance_backward_penalty)
        self.elegance_close_gap_limit = float(elegance_close_gap_limit)
        self.geometry_generalization = bool(geometry_generalization)
        self.geometry_curvature_lookahead = max(2, int(geometry_curvature_lookahead))
        self.geometry_curvature_speed_weight = float(geometry_curvature_speed_weight)
        self.geometry_lateral_speed_weight = float(geometry_lateral_speed_weight)
        self.geometry_heading_speed_weight = float(geometry_heading_speed_weight)
        self.geometry_min_speed = float(geometry_min_speed)
        self.geometry_anchor_blend = float(np.clip(geometry_anchor_blend, 0.0, 1.0))
        self.geometry_barrier_weight = float(geometry_barrier_weight)
        self._geometry_context = {
            "curvature": 0.0,
            "target_speed": float(self.bundle.meta.get("planner_target_speed", 22.0)),
            "sharp_turn": False,
        }
        self.target_speed = float(self.bundle.meta.get("planner_target_speed", 22.0))
        self.hard_safety_shield = bool(
            self.bundle.meta.get("hard_safety_shield", True)
            if hard_safety_shield is None
            else hard_safety_shield
        )
        self.use_rule_anchor = bool(use_rule_anchor)
        self.use_handcrafted_candidates = bool(use_handcrafted_candidates)
        self.use_geometry_recovery = bool(use_geometry_recovery)
        self.shield_lateral = float(self.bundle.meta.get("shield_lateral", 0.62))
        self.shield_heading_cos = float(self.bundle.meta.get("shield_heading_cos", 0.55))
        self.shield_grass_lateral = float(self.bundle.meta.get("shield_grass_lateral", 0.48))
        self.geometry_recovery_policy = TrackFollowPolicy(
            lookahead=int(self.bundle.meta.get("geometry_recovery_lookahead", 8)),
            target_speed=float(self.bundle.meta.get("geometry_recovery_speed", 17.5)),
            lateral_gain=float(self.bundle.meta.get("geometry_recovery_lateral_gain", 1.05)),
            heading_gain=float(self.bundle.meta.get("geometry_recovery_heading_gain", 1.55)),
            name="geometry_recovery",
        )
        self.anchor_policy = TelemetryBarrierExpertGatePolicy(name="world_model_anchor")
        self.last_decision_debug = {}

    def reset(self):
        self.geometry_recovery_policy.reset()
        self.anchor_policy.reset()

    def set_controlled_agent(self, agent_id):
        self.target_agent = int(agent_id)
        self.target_agent_mode = "fixed"

    def _active_target_agent(self, num_agents):
        if self.target_agent_mode == "last":
            return max(int(num_agents) - 1, 0)
        return min(max(int(self.target_agent), 0), max(int(num_agents) - 1, 0))

    def _make_background_policies(self, num_agents):
        names = self.background_policy_names or ["telemetry_lane"]
        target_agent = self._active_target_agent(num_agents)
        policies = []
        for agent_id in range(num_agents):
            if agent_id == target_agent:
                policies.append(None)
            else:
                policies.append(make_background_policy(names[agent_id % len(names)], agent_id))
        return policies

    def _background_action(self, obs, policies):
        actions = np.zeros((obs.shape[0], 3), dtype=np.float32)
        for agent_id, policy in enumerate(policies):
            if policy is None:
                continue
            actions[agent_id] = policy.act(None, obs)[agent_id]
        return actions

    def _proposal_actions(self, obs):
        obs_norm = self.bundle.normalize_obs(obs)
        obs_tensor = torch.as_tensor(obs_norm, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            return self.bundle.proposal_actor(obs_tensor).cpu().numpy()

    def _quality_proposal_actions(self, obs):
        if self.quality_bundle is None:
            return None
        target_obs_dim = obs.shape[1] if self.max_neighbors is None or self.max_neighbors <= 0 else self.quality_expected_obs_dim
        selection_mode = "fixed" if self.neighbor_mode == "fixed_k" else self.neighbor_selection_mode
        quality_obs = pack_dynamic_neighbor_obs(
            obs,
            fill=_opponent_fill_vector(self.quality_bundle),
            target_obs_dim=target_obs_dim,
            max_neighbors=self.max_neighbors,
            selection_mode=selection_mode,
        )
        obs_norm = self.quality_bundle.normalize_obs(quality_obs)
        obs_tensor = torch.as_tensor(obs_norm, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            return self.quality_bundle.actor(obs_tensor).cpu().numpy()

    def _quality_planner_enabled(self):
        return self.quality_bundle is not None and self.quality_planner_mode not in {"", "proposal_only", "off", "none"}

    def _rollout_target_action(self, imagined, proposal_actions, quality_actions, target_agent, candidate, step):
        if step == 0:
            return np.asarray(candidate, dtype=np.float32)
        base_action = self._proposal_actions(imagined)[target_agent]
        if not self._quality_planner_enabled():
            return base_action
        fresh_quality = self._quality_proposal_actions(imagined)
        if fresh_quality is None:
            quality_action = quality_actions[target_agent] if quality_actions is not None else base_action
        else:
            quality_action = fresh_quality[target_agent]
        blend = float(np.clip(self.quality_rollout_blend, 0.0, 1.0))
        action = (1.0 - blend) * np.asarray(base_action, dtype=np.float32) + blend * np.asarray(quality_action, dtype=np.float32)
        return self._speed_limited_action(action, imagined[target_agent])

    def _imitation_penalty(self, action, proposal_action, quality_action=None):
        action = np.asarray(action, dtype=np.float32)
        proposal_penalty = float(np.square(action - np.asarray(proposal_action, dtype=np.float32)).mean())
        if not self._quality_planner_enabled() or quality_action is None:
            return proposal_penalty
        quality_penalty = float(np.square(action - np.asarray(quality_action, dtype=np.float32)).mean())
        return min(proposal_penalty, quality_penalty)

    def _learned_quality_score(self, transition_out, target_agent):
        quality_pred = transition_out.get("quality_pred")
        if quality_pred is None or self.learned_quality_weight <= 0.0:
            return 0.0
        q = quality_pred[0, target_agent]
        if q.shape[-1] < 4:
            return 0.0
        on_track_prob = float(torch.sigmoid(q[0]).detach().cpu())
        grass_prob = float(torch.sigmoid(q[1]).detach().cpu())
        lane_error = float(torch.sigmoid(q[2]).detach().cpu())
        forward_clearance = float(torch.sigmoid(q[3]).detach().cpu())
        score = self.learned_quality_weight * (
            1.25 * on_track_prob
            - 1.35 * grass_prob
            - 0.75 * lane_error
            + 0.25 * forward_clearance
        )
        if self.learned_quality_gate:
            gate_violation = 0.0
            gate_violation += max(0.0, self.learned_quality_min_on_track - on_track_prob)
            gate_violation += max(0.0, grass_prob - self.learned_quality_max_grass)
            gate_violation += max(0.0, lane_error - self.learned_quality_max_lane_error)
            score -= self.learned_quality_gate_penalty * gate_violation
        return score

    def _slot_meta(self, obs):
        opponent_dim = int(self.bundle.meta.get("opponent_dim", MASKED_RELATION_DIM if self.bundle.meta.get("use_slot_mask", False) else RELATION_DIM))
        use_slot_mask = bool(self.bundle.meta.get("use_slot_mask", False))
        if obs.shape[-1] <= EGO_DIM:
            return 0, RELATION_DIM, False
        remainder = obs.shape[-1] - EGO_DIM
        if remainder % opponent_dim != 0:
            if remainder % MASKED_RELATION_DIM == 0:
                opponent_dim = MASKED_RELATION_DIM
                use_slot_mask = True
            elif remainder % RELATION_DIM == 0:
                opponent_dim = RELATION_DIM
                use_slot_mask = False
        slot_feature_dim = opponent_dim - 1 if use_slot_mask else opponent_dim
        return opponent_dim, slot_feature_dim, use_slot_mask

    def _traffic_features(self, obs_row):
        opponent_dim, slot_feature_dim, use_slot_mask = self._slot_meta(obs_row)
        features = {
            "nearest_forward": None,
            "nearest_left": 0.0,
            "nearest_distance": None,
            "ahead_count": 0,
            "alongside_count": 0,
            "nearest_closing_speed": 0.0,
        }
        if opponent_dim <= 0:
            return features
        for start in range(EGO_DIM, len(obs_row), opponent_dim):
            slot = np.asarray(obs_row[start : start + opponent_dim], dtype=np.float32)
            if slot.shape[0] < opponent_dim:
                break
            if use_slot_mask and float(slot[-1]) <= 0.0:
                continue
            rel = slot[:slot_feature_dim]
            if rel.shape[0] < 5:
                continue
            rel_forward = float(rel[0]) * PLAYFIELD
            rel_left = float(rel[1]) * PLAYFIELD
            rel_vx = float(rel[2]) * 50.0 if rel.shape[0] > 2 else 0.0
            rel_vy = float(rel[3]) * 50.0 if rel.shape[0] > 3 else 0.0
            distance = float(rel[4]) * PLAYFIELD
            if 0.0 < rel_forward < 65.0 and abs(rel_left) < 18.0:
                features["ahead_count"] += 1
                if features["nearest_forward"] is None or rel_forward < features["nearest_forward"]:
                    features["nearest_forward"] = rel_forward
                    features["nearest_left"] = rel_left
                    features["nearest_distance"] = distance
                    features["nearest_closing_speed"] = max(-(rel_vx + 0.25 * abs(rel_vy)), 0.0)
            if abs(rel_forward) <= 14.0 and abs(rel_left) < 14.0:
                features["alongside_count"] += 1
        return features

    def _recovery_action(self, obs_row, base_action):
        action = np.asarray(base_action, dtype=np.float32).copy()
        lateral = float(obs_row[12])
        heading_error = math.atan2(float(obs_row[13]), float(obs_row[14]))
        on_grass = float(obs_row[15]) > 0.5
        backward = float(obs_row[16]) > 0.5
        heading_cos = float(obs_row[14])
        speed = float(obs_row[4]) * 50.0
        corrective_steer = -np.clip(2.0 * heading_error + 0.80 * lateral, -1.0, 1.0)
        action[0] = corrective_steer
        action[1] = 0.48 if on_grass else 0.56
        action[2] = 0.0 if speed < 18.0 else 0.18
        if backward or heading_cos < 0.28:
            if speed < 4.0 and not backward:
                action[1] = 0.34
                action[2] = 0.0
            else:
                action[1] = 0.06
                action[2] = 0.55
        elif abs(lateral) > 0.62 or heading_cos < 0.55:
            action[1] = min(action[1], 0.34)
            action[2] = max(action[2], 0.10 if speed < 12.0 else 0.28)
        return action

    def _geometry_recovery_action(self, env, obs, target_agent, base_action):
        if not self.use_geometry_recovery:
            return self._recovery_action(obs[target_agent], base_action)
        if env is None:
            return self._recovery_action(obs[target_agent], base_action)
        try:
            action = self.geometry_recovery_policy.act(env, obs)[target_agent]
        except Exception:
            return self._recovery_action(obs[target_agent], base_action)
        action = np.asarray(action, dtype=np.float32).copy()
        obs_row = obs[target_agent]
        speed = float(obs_row[4]) * 50.0
        heading_cos = float(obs_row[14])
        on_grass = float(obs_row[15]) > 0.5
        backward = float(obs_row[16]) > 0.5
        if backward:
            if speed < 3.0:
                action[1] = max(action[1], 0.28)
                action[2] = 0.0
            else:
                action[1] = min(action[1], 0.08)
                action[2] = max(action[2], 0.45)
        elif speed < 5.0 and heading_cos < 0.25:
            action[1] = max(action[1], 0.32)
            action[2] = 0.0
        elif on_grass:
            action[1] = max(action[1], 0.42)
            action[2] = min(action[2], 0.05)
        return self._speed_limited_action(action, obs_row)

    def _anchor_action(self, env, obs, target_agent, fallback_action):
        if not self.use_rule_anchor:
            return self._speed_limited_action(fallback_action, obs[target_agent])
        try:
            action = self.anchor_policy.act(env, obs)[target_agent]
        except Exception:
            action = fallback_action
        return self._speed_limited_action(action, obs[target_agent])

    def _update_geometry_context(self, env, obs, target_agent):
        base_speed = float(self.target_speed)
        context = {"curvature": 0.0, "target_speed": base_speed, "sharp_turn": False}
        if not self.geometry_generalization or env is None:
            self._geometry_context = context
            return context
        try:
            track = list(env.unwrapped.track)
            if not track:
                self._geometry_context = context
                return context
            car_pos = np.asarray(env.unwrapped.cars[target_agent].hull.position, dtype=np.float32).reshape(1, 2)
            track_xy = np.asarray(track, dtype=np.float32)[:, 2:]
            idx = int(np.argmin(np.linalg.norm(car_pos - track_xy, axis=1)))
            lookahead = min(self.geometry_curvature_lookahead, max(len(track) // 8, 2))
            prev_beta = float(track[(idx - lookahead) % len(track)][1])
            next_beta = float(track[(idx + lookahead) % len(track)][1])
            if getattr(env.unwrapped, "episode_direction", "CCW") == "CW":
                prev_beta += math.pi
                next_beta += math.pi
            curvature = abs(wrap_to_pi(next_beta - prev_beta)) / max(float(2 * lookahead), 1.0)
            obs_row = np.asarray(obs[target_agent], dtype=np.float32)
            lateral = abs(float(obs_row[12]))
            heading_cos = float(obs_row[14])
            speed_limit = (
                base_speed
                - self.geometry_curvature_speed_weight * curvature
                - self.geometry_lateral_speed_weight * max(0.0, lateral - 0.18)
                - self.geometry_heading_speed_weight * max(0.0, 0.88 - heading_cos)
            )
            context = {
                "curvature": float(curvature),
                "target_speed": float(max(self.geometry_min_speed, min(base_speed, speed_limit))),
                "sharp_turn": bool(curvature > 0.030 or (curvature > 0.020 and lateral > 0.24)),
            }
        except Exception:
            context = {"curvature": 0.0, "target_speed": base_speed, "sharp_turn": False}
        self._geometry_context = context
        return context

    def _speed_limited_action(self, action, obs_row):
        action = np.asarray(action, dtype=np.float32).copy()
        speed = float(obs_row[4]) * 50.0
        lateral = abs(float(obs_row[12]))
        heading_cos = float(obs_row[14])
        on_grass = float(obs_row[15]) > 0.5
        safe_speed = float(self._geometry_context.get("target_speed", self.target_speed))
        if heading_cos < 0.85:
            safe_speed -= 5.0
        if lateral > 0.30:
            safe_speed -= 4.0
        safe_speed = max(self.geometry_min_speed if self.geometry_generalization else 10.0, safe_speed)
        if self.geometry_generalization and self._geometry_context.get("sharp_turn", False):
            action[0] *= 0.82
            if lateral > 0.24 or heading_cos < 0.88:
                action[1] = min(action[1], 0.42)
                action[2] = max(action[2], 0.08)
        if speed > safe_speed + 6.0:
            action[1] = min(action[1], 0.02)
            action[2] = max(action[2], 0.45)
        elif speed > safe_speed + 2.0:
            action[1] = min(action[1], 0.08)
            action[2] = max(action[2], 0.25)
        if on_grass and speed > 22.0:
            action[1] = min(action[1], 0.08)
            action[2] = max(action[2], 0.20)
        if (heading_cos < 0.72 or lateral > 0.42) and speed > 12.0:
            action[1] = min(action[1], 0.08)
            action[2] = max(action[2], 0.28)
        action[0] = np.clip(action[0], -1.0, 1.0)
        action[1:] = np.clip(action[1:], 0.0, 1.0)
        return action

    def _needs_hard_recovery(self, obs_row):
        if not self.overtake_aware_planner or not self.hard_safety_shield:
            return False
        lateral = abs(float(obs_row[12]))
        heading_cos = float(obs_row[14])
        on_grass = float(obs_row[15]) > 0.5
        backward = float(obs_row[16]) > 0.5
        severe_grass = on_grass and (lateral > self.shield_grass_lateral or heading_cos < 0.70)
        return bool(backward or severe_grass or lateral > self.shield_lateral or heading_cos < self.shield_heading_cos)

    def _candidate_pool(self, proposal_target, background_target, target_obs=None, extra_targets=None):
        base = np.asarray(proposal_target, dtype=np.float32)
        background = np.asarray(background_target, dtype=np.float32)
        pools = [base, background]
        for item in extra_targets or []:
            pools.append(np.asarray(item, dtype=np.float32))
        if not self.use_handcrafted_candidates:
            dedup = []
            seen = set()
            for item in pools:
                if target_obs is not None:
                    item = self._speed_limited_action(item, target_obs)
                key = tuple(np.round(item, 3))
                if key not in seen:
                    seen.add(key)
                    dedup.append(item)
            return dedup[: self.candidates]
        if self.overtake_aware_planner and target_obs is not None:
            target_obs = np.asarray(target_obs, dtype=np.float32)
            traffic = self._traffic_features(target_obs)
            speed = float(target_obs[4]) * 50.0
            lateral = float(target_obs[12])
            heading_error = math.atan2(float(target_obs[13]), float(target_obs[14]))
            on_grass = float(target_obs[15]) > 0.5
            backward = float(target_obs[16]) > 0.5
            recovery_needed = abs(lateral) > 0.50 or float(target_obs[14]) < 0.66 or backward
            geom_target_speed = float(self._geometry_context.get("target_speed", self.target_speed))
            sharp_turn = bool(self._geometry_context.get("sharp_turn", False))

            chase = base.copy()
            chase[0] = np.clip(base[0] - 0.25 * heading_error, -1.0, 1.0)
            chase[1] = 0.64 if speed < geom_target_speed else 0.18
            chase[2] = 0.0 if speed < geom_target_speed + 1.0 else 0.24
            pools.append(chase)

            if self.geometry_generalization:
                anchored = (1.0 - self.geometry_anchor_blend) * base + self.geometry_anchor_blend * background
                anchored = np.asarray(anchored, dtype=np.float32)
                anchored[0] = np.clip(anchored[0] - 0.18 * heading_error - 0.18 * lateral, -1.0, 1.0)
                anchored[1] = min(anchored[1], 0.52 if not sharp_turn else 0.38)
                anchored[2] = max(anchored[2], 0.0 if speed < geom_target_speed else 0.16)
                pools.append(anchored)

            allow_pass = not recovery_needed and abs(lateral) < 0.34 and float(target_obs[14]) > 0.84
            if self.geometry_generalization and sharp_turn:
                allow_pass = allow_pass and abs(lateral) < 0.22 and traffic["nearest_forward"] is not None and traffic["nearest_forward"] < 18.0
            if allow_pass and (traffic["nearest_forward"] is not None or traffic["alongside_count"] > 0):
                pass_side = -1.0 if traffic["nearest_left"] >= 0.0 else 1.0
                steer_grid = [0.08, 0.16, 0.24] if sharp_turn else [0.12, 0.22, 0.32]
                for side in [pass_side, -pass_side]:
                    for steer_mag in steer_grid:
                        cand = base.copy()
                        cand[0] = np.clip(side * steer_mag - 0.12 * heading_error, -1.0, 1.0)
                        cand[1] = 0.52 if sharp_turn else 0.64
                        cand[2] = 0.0
                        pools.append(cand)
                if traffic["nearest_forward"] is not None and traffic["nearest_forward"] < 11.0 and abs(traffic["nearest_left"]) < 8.0:
                    brake = background.copy()
                    brake[0] = np.clip(-0.25 * np.sign(traffic["nearest_left"] or 1.0), -1.0, 1.0)
                    brake[1] = 0.04
                    brake[2] = 0.46
                    pools.append(brake)

            if recovery_needed:
                pools.insert(0, self._recovery_action(target_obs, background))
                for gain in [0.40, 0.65]:
                    recover = base.copy()
                    recover[0] = -np.clip(gain * (2.0 * heading_error + 0.80 * lateral), -1.0, 1.0)
                    recover[1] = 0.46 if on_grass else 0.52
                    recover[2] = 0.0 if speed < 16.0 else 0.18
                    pools.insert(1, recover)

        if self.profile != "nominal":
            steer_offsets = [-0.22, -0.12, 0.0, 0.12, 0.22]
            gas_offsets = [-0.08, 0.0, 0.08]
            brake_offsets = [-0.05, 0.0, 0.04]
            for ds in steer_offsets:
                for dg in gas_offsets:
                    for db in brake_offsets:
                        cand = base.copy()
                        cand[0] = np.clip(cand[0] + ds, -1.0, 1.0)
                        cand[1] = np.clip(cand[1] + dg, 0.0, 1.0)
                        cand[2] = np.clip(cand[2] + db, 0.0, 1.0)
                        pools.append(cand)
        dedup = []
        seen = set()
        for item in pools:
            if target_obs is not None:
                item = self._speed_limited_action(item, target_obs)
            key = tuple(np.round(item, 3))
            if key not in seen:
                seen.add(key)
                dedup.append(item)
        return dedup[: self.candidates]

    def _state_quality_terms(self, previous_obs, next_obs, target_agent):
        prev_target = previous_obs[target_agent]
        next_target = next_obs[target_agent]
        prev_traffic = self._traffic_features(prev_target)
        next_traffic = self._traffic_features(next_target)
        lateral = abs(float(next_target[12]))
        heading_cos = float(next_target[14])
        heading_error = math.acos(float(np.clip(heading_cos, -1.0, 1.0)))
        on_grass = float(next_target[15]) > 0.5
        backward = float(next_target[16]) > 0.5
        speed = float(next_target[4]) * 50.0

        overtake_score = 0.0
        if prev_traffic["nearest_forward"] is not None:
            if next_traffic["nearest_forward"] is None:
                overtake_score += 1.2
            else:
                gap_delta = (prev_traffic["nearest_forward"] - next_traffic["nearest_forward"]) / 65.0
                overtake_score += float(np.clip(gap_delta, -0.4, 0.8))
            overtake_score += 0.35 * max(prev_traffic["ahead_count"] - next_traffic["ahead_count"], 0)
        overtake_score += 0.03 * max(speed - min(self.target_speed, 18.0), 0.0)

        lane_penalty = lateral + 0.55 * heading_error
        if lateral > 0.32:
            lane_penalty += 1.8 * (lateral - 0.32)
        if heading_cos < 0.82:
            lane_penalty += 1.2 * (0.82 - heading_cos)
        if on_grass or backward or lateral > 0.46:
            overtake_score = min(overtake_score, 0.0)
        grass_penalty = 2.5 * float(on_grass) + 1.2 * float(backward)
        if lateral > 0.46:
            grass_penalty += 0.8 * (lateral - 0.46)
        close_gap_penalty = 0.0
        if next_traffic["nearest_forward"] is not None:
            close_gap_penalty = max(0.0, 10.0 - next_traffic["nearest_forward"]) / 10.0
        elegance_barrier = 0.0
        if self.elegance_barrier:
            elegance_barrier += max(0.0, lateral - self.elegance_lateral_limit) ** 2
            elegance_barrier += max(0.0, self.elegance_heading_cos_min - heading_cos) ** 2
            elegance_barrier += self.elegance_grass_penalty * float(on_grass)
            elegance_barrier += self.elegance_backward_penalty * float(backward)
            if next_traffic["nearest_forward"] is not None:
                elegance_barrier += max(0.0, self.elegance_close_gap_limit - next_traffic["nearest_forward"]) / max(self.elegance_close_gap_limit, 1e-6)
            if next_traffic["alongside_count"] > 0 and lateral > self.elegance_lateral_limit:
                elegance_barrier += 0.35 * float(next_traffic["alongside_count"])
        if self.geometry_generalization:
            curvature = float(self._geometry_context.get("curvature", 0.0))
            target_speed = float(self._geometry_context.get("target_speed", self.target_speed))
            geometry_barrier = 0.0
            geometry_barrier += curvature * max(0.0, speed - target_speed) / 8.0
            geometry_barrier += max(0.0, lateral - 0.34) * (1.0 + 8.0 * curvature)
            geometry_barrier += max(0.0, 0.78 - heading_cos) * (1.0 + 10.0 * curvature)
            geometry_barrier += 1.2 * float(on_grass) * (1.0 + 6.0 * curvature)
            elegance_barrier += self.geometry_barrier_weight * geometry_barrier
        return overtake_score, lane_penalty, grass_penalty, close_gap_penalty, elegance_barrier

    def _score_candidate(self, obs, proposal_actions, background_policies, candidate, target_agent, quality_actions=None):
        imagined = np.asarray(obs, dtype=np.float32).copy()
        score = 0.0
        discount = 1.0
        proposal = np.asarray(proposal_actions, dtype=np.float32)
        quality = None if quality_actions is None else np.asarray(quality_actions, dtype=np.float32)
        for step in range(self.horizon):
            bg = self._background_action(imagined, background_policies)
            target_action = self._rollout_target_action(
                imagined,
                proposal_actions,
                quality_actions,
                target_agent,
                candidate,
                step,
            )
            full_action = bg.copy()
            full_action[target_agent] = target_action
            obs_tensor = torch.as_tensor(
                self.bundle.normalize_obs(imagined)[None, ...], dtype=torch.float32, device=self.device
            )
            act_tensor = torch.as_tensor(
                self.bundle.normalize_action(full_action)[None, ...], dtype=torch.float32, device=self.device
            )
            with torch.no_grad():
                out = self.bundle.transition(obs_tensor, act_tensor)
                next_norm = out["next_mu"].cpu().numpy()[0]
                next_obs = self.bundle.denormalize_obs(next_norm)
                reward = float(out["reward_mu"].cpu().numpy()[0, target_agent])
                risk = float(torch.sigmoid(out["risk_logits"])[0, target_agent].cpu().numpy())
                uncertainty = float(
                    np.clip(
                        out["next_logvar"].cpu().numpy()[0, target_agent, 0]
                        + out["reward_logvar"].cpu().numpy()[0, target_agent],
                        -2.0,
                        4.0,
                    )
            )
            progress = float(next_obs[target_agent, 9] - imagined[target_agent, 9])
            learned_quality_score = self._learned_quality_score(out, target_agent)
            quality_ref = quality[target_agent] if quality is not None else None
            imitation = self._imitation_penalty(full_action[target_agent], proposal[target_agent], quality_ref)
            if self.overtake_aware_planner:
                overtake, lane_penalty, grass_penalty, close_gap_penalty, elegance_barrier = self._state_quality_terms(
                    imagined,
                    next_obs,
                    target_agent,
                )
            else:
                overtake = 0.0
                lane_penalty = 0.0
                grass_penalty = 0.0
                close_gap_penalty = 0.0
                elegance_barrier = 0.0
            overtake_weight = self.overtake_weight
            lane_weight = self.lane_quality_weight
            grass_weight = self.grass_penalty_weight
            close_gap_weight = self.close_gap_penalty_weight
            if self._quality_planner_enabled():
                overtake_weight += self.quality_overtake_weight
                lane_weight += self.quality_lane_weight
                grass_weight += self.quality_grass_weight
                close_gap_weight += self.quality_close_gap_weight
            score += discount * (
                reward
                + self.progress_weight * progress
                + overtake_weight * overtake
                + learned_quality_score
                - self.risk_weight * risk
                - self.uncertainty_weight * uncertainty
                - self.imitation_weight * imitation
                - lane_weight * lane_penalty
                - grass_weight * grass_penalty
                - close_gap_weight * close_gap_penalty
                - self.elegance_barrier_weight * elegance_barrier
            )
            imagined = next_obs
            discount *= self.gamma
        return score

    def act(self, env, obs):
        obs = np.asarray(obs, dtype=np.float32)
        if self.neighbor_mode in {"dynamic", "fixed_k"}:
            target_obs_dim = obs.shape[1] if self.max_neighbors is None or self.max_neighbors <= 0 else self.bundle.meta.get("obs_dim")
            selection_mode = "fixed" if self.neighbor_mode == "fixed_k" else self.neighbor_selection_mode
            obs = pack_dynamic_neighbor_obs(
                obs,
                fill=_opponent_fill_vector(self.bundle),
                target_obs_dim=target_obs_dim,
                max_neighbors=self.max_neighbors,
                selection_mode=selection_mode,
            )
        target_agent = self._active_target_agent(obs.shape[0])
        self._update_geometry_context(env, obs, target_agent)
        proposal_actions = self._proposal_actions(obs)
        quality_actions = self._quality_proposal_actions(obs)
        background_policies = self._make_background_policies(obs.shape[0])
        background_actions = self._background_action(obs, background_policies)
        anchor_target = self._anchor_action(env, obs, target_agent, background_actions[target_agent])
        self.last_decision_debug = {
            "target_agent": int(target_agent),
            "geometry_generalization": bool(self.geometry_generalization),
            "geometry_context": dict(self._geometry_context),
            "hard_recovery": False,
            "candidate_count": 0,
            "best_score": None,
            "anchor_action": np.asarray(anchor_target, dtype=float).tolist(),
            "use_rule_anchor": self.use_rule_anchor,
            "use_handcrafted_candidates": self.use_handcrafted_candidates,
            "hard_safety_shield": self.hard_safety_shield,
            "use_geometry_recovery": self.use_geometry_recovery,
        }
        if self._needs_hard_recovery(obs[target_agent]):
            actions = background_actions.copy()
            actions[target_agent] = self._geometry_recovery_action(env, obs, target_agent, anchor_target)
            self.last_decision_debug.update(
                {
                    "hard_recovery": True,
                    "selected_action": np.asarray(actions[target_agent], dtype=float).tolist(),
                }
            )
            return actions.astype(np.float32)
        candidate_pool = self._candidate_pool(
            proposal_actions[target_agent],
            anchor_target,
            target_obs=obs[target_agent],
            extra_targets=[quality_actions[target_agent]] if quality_actions is not None else None,
        )

        best_action = candidate_pool[0]
        best_score = -np.inf
        for candidate in candidate_pool:
            score = self._score_candidate(
                obs,
                proposal_actions,
                background_policies,
                candidate,
                target_agent,
                quality_actions=quality_actions,
            )
            if score > best_score:
                best_score = score
                best_action = candidate

        actions = background_actions.copy()
        actions[target_agent] = best_action
        self.last_decision_debug.update(
            {
                "candidate_count": int(len(candidate_pool)),
                "best_score": float(best_score),
                "selected_action": np.asarray(best_action, dtype=float).tolist(),
            }
        )
        return actions.astype(np.float32)
