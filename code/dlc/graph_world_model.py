import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dlc.graph_policy import (
    EGO_DIM,
    _infer_source_layout,
    GraphActorBundle,
    PermutationInvariantActor,
    PLAYFIELD,
    pack_dynamic_neighbor_obs,
    selected_neighbor_ids,
    _opponent_fill_vector,
    _infer_source_layout,
    _rank_opponent_slot_entries,
)
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
PRIORITY_RELATION_DIM = 9
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


def escalation_feasible_indices(violations, allow_best=False):
    """Candidate indices whose imagined rollout never entered the guarded state.

    A ``filter`` shield that has escalated keeps the planner in charge and
    restricts the pool to these candidates. The strict test is only meaningful
    when the vehicle starts outside the guard band: once it already sits at the
    road edge every candidate inherits a positive violation at the first
    imagined step, the strict set is empty, and the caller used to hand control
    to the geometry recovery action for as long as the excursion lasted. With
    ``allow_best`` the shield instead keeps the least-violating candidates,
    which is the same violation-major ordering the constrained pool already
    uses. The shield's own recovery action is a member of that pool, so the
    fallback cannot score worse than handing the vehicle to it.
    """
    strict = {index for index, value in enumerate(violations) if float(value) <= 0.0}
    if strict or not allow_best or not len(violations):
        return strict
    best = min(round(float(value), 2) for value in violations)
    return {index for index, value in enumerate(violations) if round(float(value), 2) <= best}


def make_background_policy(name, agent_id):
    speeds = [14.0, 15.0, 16.0, 17.0]
    if name == 'telemetry_lane13':
        return TelemetryLanePolicy(target_speed=13.0, name=f'telemetry_lane13_{agent_id}')
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
        predict_residual=False,
        masked_pooling="mean",
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
        # Pooling used when the opponents arrive as masked slots. Archived
        # checkpoints were trained with a masked mean and record no
        # ``masked_pooling`` key, so the default keeps their behaviour
        # bit-for-bit; runs that ask for masked attention opt in explicitly.
        self.masked_pooling = str(masked_pooling)
        # Residual parameterization: the next-state head predicts the increment
        # relative to the observation it is conditioned on, so the model starts
        # at the persistence predictor and only has to learn the change. Without
        # this, the head has to reproduce a wide state distribution from scratch
        # and a plain MSE objective settles on something close to its mean.
        self.predict_residual = bool(predict_residual)
        self.relation_dim = self.slot_feature_dim + 1 if self.use_slot_mask else RELATION_DIM
        self.node_encoder = mlp(EGO_DIM, hidden_dim, hidden_dim)
        self.relation_encoder = mlp(self.slot_feature_dim, hidden_dim, hidden_dim)
        self.action_encoder = mlp(action_dim, hidden_dim, hidden_dim)
        self.relation_attention = nn.Linear(hidden_dim, 1)
        self.fuse = mlp(5 * hidden_dim, hidden_dim, hidden_dim)
        self.next_head = nn.Linear(hidden_dim, obs_dim)
        if self.predict_residual:
            nn.init.zeros_(self.next_head.weight)
            nn.init.zeros_(self.next_head.bias)
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
                slot_mask = mask.squeeze(-1)
                if self.masked_pooling != "attention":
                    # Masked mean: every admitted vehicle contributes equally, so
                    # only the *set* of opponents survives the pooling and the
                    # ranking that ordered the slots is discarded here.
                    valid = mask.sum(dim=-2).clamp_min(1.0)
                    rel_ctx = rel_emb.sum(dim=-2) / valid
                    weights = slot_mask
                else:
                    # Masked attention: the weights are learned from the slot
                    # features, so the model can commit to the interaction
                    # partner that the admission rule put in front and let an
                    # irrelevant vehicle contribute almost nothing. Empty slots
                    # are excluded through the additive mask instead of being
                    # counted as zero-valued vehicles.
                    logits = self.relation_attention(rel_emb).squeeze(-1)
                    logits = logits.masked_fill(slot_mask <= 0.5, float("-inf"))
                    empty = ~torch.isfinite(logits).any(dim=-1, keepdim=True)
                    logits = torch.where(empty, torch.zeros_like(logits), logits)
                    weights = torch.softmax(logits, dim=-1)
                    weights = torch.where(empty, torch.zeros_like(weights), weights)
                    rel_ctx = (rel_emb * weights.unsqueeze(-1)).sum(dim=-2)
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
        if self.predict_residual:
            next_mu = obs + next_mu
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
            masked_pooling=meta.get("masked_pooling", "mean"),
            use_slot_mask=meta.get("use_slot_mask", False),
            slot_feature_dim=meta.get("slot_feature_dim", RELATION_DIM),
            quality_dim=meta.get("quality_dim", 4),
            predict_residual=meta.get("predict_residual", False),
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


# Planner lateral geometry, in units of the road half-width.
#
# The legacy_v1 telemetry channel is a projection on the local track tangent: it
# correlates with the true cross-track offset at only 0.152 and under-reports it
# by about 5.8x, so these thresholds were effectively never binding there. A
# corrected_v2 checkpoint sees the real offset, where a side-by-side pass sits at
# roughly the environment's lateral spacing (2.2 units = 0.33 half-widths), so an
# inherited threshold of 0.46 would forbid ever crediting a pass.
#
# The corrected row is calibrated from the hand-tuned rule controller's on-road
# cross-track distribution (p95 = 0.393, p99 = 0.743 of the half-width over
# 13 932 on-road steps), i.e. it penalises nothing a competent on-road controller
# actually uses. It was fixed before scoring any corrected result.
# Side-by-side clearance model of the reference joint-clearance controller
# (dlc/joint_clearance_pilot.py: pair_half_length, pair_half_width). Reusing it
# makes the planner's feasibility test and the environment's contact test agree.
SEPARATION_HALF_LENGTH = 6.0
SEPARATION_HALF_WIDTH = 3.3

PLANNER_GEOMETRY = {
    "legacy_v1": {
        "lane_free": 0.32,
        "pass_open": 0.34,
        "edge": 0.46,
        "guard_lateral": 0.62,
        "guard_grass_lateral": 0.48,
        "guard_heading_cos": 0.55,
        "speed": {
            "lane_damp_lateral": 0.30, "heading_damp_cos": 0.85,
            "limit_lateral_ref": 0.18, "limit_heading_ref": 0.88,
            "brake_lateral": 0.42, "brake_heading_cos": 0.72,
            "sharp_lateral": 0.24, "sharp_heading_cos": 0.88,
            # Legacy keeps the archived per-tile curvature heuristic.
            "lat_accel_max": None, "sharp_radius_m": None,
        },
    },
    # The corrected channel reports a true left-positive cross-track offset in
    # half-widths. The environment's own joint-clearance teacher holds a racing
    # lane at 4.4 units = 0.66 half-widths and the simulated road edge is at
    # 1.0, so a guard that fires at the archived 0.62 would interrupt the
    # manoeuvre it is supposed to protect. Guard thresholds are set between the
    # outer racing lane and the roadside.
    "corrected_v2": {
        "lane_free": 0.40,
        "pass_open": 0.55,
        "edge": 0.80,
        # 1 - hull half-width / road half-width: the offset at which the wheel
        # body reaches the road edge. Measured on 664k corrected-v2 samples,
        # P(on grass) is 0.000 for |lat| <= 0.9 and 0.983 for |lat| >= 1.0, so
        # 1.0 is the road edge and 0.76 is where the hull touches it.
        "guard_lateral": 0.76,
        # Grass is the more severe state, so the guard must fire earlier there:
        # the joint-clearance teacher's own outer lane offset (4.4 units at
        # joint_half_width/settlement scale = 0.66 half-widths).
        "guard_grass_lateral": 0.66,
        "guard_heading_cos": 0.55,
        # The speed limiter inherited legacy thresholds that were written for a
        # channel under-reporting the offset by 5.8x. In corrected half-widths
        # an outer-lane pass sits at 0.5-0.7, so the inherited 0.30/0.42 gates
        # braked the vehicle whenever it moved out to pass, which is why it
        # never caught the traffic. Thresholds now sit at the outer lane and the
        # roadside, and the guard band is unchanged in intent.
        "speed": {
            "lane_damp_lateral": 0.62, "heading_damp_cos": 0.72,
            "limit_lateral_ref": 0.55, "limit_heading_ref": 0.72,
            "brake_lateral": 0.80, "brake_heading_cos": 0.55,
            "sharp_lateral": 0.50, "sharp_heading_cos": 0.80,
            # Cornering limit expressed as a physical lateral-acceleration
            # budget. ``curvature`` is measured in rad per track tile, so the
            # limiter converts it with the tile spacing (3.5 m here) into
            # ``v_curve = sqrt(a_lat / kappa)``. The smallest radius on the
            # procedural layouts is ~26 m, which the earlier per-tile
            # threshold mis-scaled: it flagged 70-75 % of steps as a sharp
            # turn and clamped the throttle to 0.42 everywhere. The budget is
            # calibrated to the reference controller's demonstrated envelope:
            # the p95 of the realised v^2 * kappa over 88 664 near-aligned
            # rule-expert steps is 16.7 m/s^2, so a 16 m/s^2 limit does not
            # bind below what the baseline already achieves on these layouts.
            "lat_accel_max": 16.0, "sharp_radius_m": 55.0,
        },
    },
}

class GraphWorldModelPolicy:
    # Fallbacks for policies that are constructed without ``__init__`` (unit
    # tests build the scoring helpers directly).
    overtake_clear_margin = 4.0
    shield_escalation_steps = 0
    escalation_fallback = "recovery"
    ensemble_epistemic = True

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
        planner_liveness_weight=None,
        planner_liveness_speed=None,
        maneuver_hold_steps=None,
        corridor_feasibility=None,
        planner_progress_mode=None,
        corridor_selection=None,
        clearance_feasibility=None,
        clearance_alongside_length=None,
        clearance_lateral_min=None,
        shield_escalation_steps=None,
        shield_escalation_bypass=None,
        escalation_fallback=None,
        relevance_memory=None,
        maneuver_commit_steps=None,
        maneuver_commit_forward_m=None,
        maneuver_commit_lateral_m=None,
        maneuver_commit_release_m=None,
        reverse_slot_order=False,
        overtake_clear_margin=None,
        corridor_return_weight=None,
        corridor_return_candidates=None,
        corridor_return_gain=None,
        corridor_return_heading_gain=None,
        corridor_return_gate=None,
        corridor_recovery_cross_track=None,
        hard_safety_shield=None,
        shield_mode=None,
        shield_lateral=None,
        shield_grass_lateral=None,
        shield_heading_cos=None,
        guard_penalty_weight=None,
        separation_scale=None,
        dump_rollouts=False,
        use_rule_anchor=True,
        use_handcrafted_candidates=True,
        use_geometry_recovery=True,
        recovery_enabled=True,
        head_ablation=None,
        world_model_mode="full",
        decision_utility_compare_mode=None,
        ensemble_epistemic=True,
    ):
        if torch is None:
            raise ImportError("GraphWorldModelPolicy requires torch")
        self.device = torch.device(device)
        if isinstance(model_path, (list, tuple)):
            ensemble_paths = [str(path) for path in model_path]
        else:
            ensemble_paths = [str(model_path)]
        self.bundles = [GraphWorldModelBundle.load(path, map_location=self.device)
                        for path in ensemble_paths]
        for bundle in self.bundles:
            bundle.transition.to(self.device)
            bundle.proposal_actor.to(self.device)
        # The first member supplies the metadata that fixes the protocol: the
        # observation layout, the neighbour selector and the planner constants.
        self.bundle = self.bundles[0]
        self.ensemble_paths = ensemble_paths
        self.ensemble_size = len(self.bundles)
        # When the epistemic term is off the fused variance is the mean of the
        # members' own variances, so the disagreement between members never
        # reaches the planner.
        self.ensemble_epistemic = bool(ensemble_epistemic)
        if self.ensemble_size > 1:
            self._check_ensemble_compatibility()
        self.quality_bundle = None
        self.quality_expected_obs_dim = None
        if quality_proposal_path:
            self.quality_bundle = GraphActorBundle.load(quality_proposal_path, map_location=self.device)
            self.quality_bundle.actor.to(self.device)
            self.quality_expected_obs_dim = int(
                self.quality_bundle.meta.get("obs_dim", self.quality_bundle.obs_mean.shape[-1])
            )
        self.name = self.bundle.meta.get("name", "graph_world_model")
        self.telemetry_version = self.bundle.meta.get('telemetry_version', 'legacy_v1')
        if self.quality_bundle is not None and self.quality_bundle.meta.get('telemetry_version', 'legacy_v1') != self.telemetry_version:
            raise ValueError('Quality actor and world model must use the same telemetry version')
        self.neighbor_mode = str(neighbor_mode)
        self.max_neighbors = None if max_neighbors is None else int(max_neighbors)
        self.slot_budget = self._derive_slot_budget()
        self.neighbor_selection_mode = str(neighbor_selection_mode or "legacy")
        if self.telemetry_version == 'corrected_v2' and self.neighbor_selection_mode == 'legacy':
            self.neighbor_selection_mode = self.bundle.meta.get('neighbor_selection', 'interaction')
        self.target_agent = int(self.bundle.meta.get("target_agent", max(self.bundle.meta.get("num_agents", 2) - 1, 0)))
        self.target_agent_mode = str(self.bundle.meta.get("target_agent_mode", "last"))
        self.background_policy_names = normalize_items(
            self.bundle.meta.get("background_policies", "telemetry_cruise,telemetry_yield,telemetry_lane")
        )
        if self.telemetry_version == 'corrected_v2' and self.bundle.meta.get('background_profile') == 'lane13':
            self.background_policy_names = ['telemetry_lane13']
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
        if (self.telemetry_version == 'corrected_v2' and self.learned_quality_weight > 0
                and self.bundle.meta.get('quality_aux_weight', 0) <= 0):
            raise ValueError('Cannot score with an untrained quality head')
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
        self.recovery_enabled = bool(recovery_enabled)
        self.world_model_mode = str(world_model_mode or "full")
        if self.world_model_mode not in {"full", "no_world_model"}:
            raise ValueError(f"unknown world_model_mode: {self.world_model_mode}")
        self.decision_utility_compare_mode = decision_utility_compare_mode
        if head_ablation is None:
            self.disabled_heads = set()
        elif isinstance(head_ablation, str):
            self.disabled_heads = {item.strip().lower() for item in head_ablation.split(",") if item.strip()}
        else:
            self.disabled_heads = {str(item).strip().lower() for item in head_ablation if str(item).strip()}
        unknown_heads = self.disabled_heads - {"state", "reward", "risk", "uncertainty"}
        if unknown_heads:
            raise ValueError(f"unknown head ablation(s): {sorted(unknown_heads)}")
        guard_defaults = self.planner_geometry
        self.shield_lateral = float(
            shield_lateral if shield_lateral is not None
            else self.bundle.meta.get("shield_lateral", guard_defaults["guard_lateral"])
        )
        self.shield_heading_cos = float(
            shield_heading_cos if shield_heading_cos is not None
            else self.bundle.meta.get("shield_heading_cos", guard_defaults["guard_heading_cos"])
        )
        self.shield_grass_lateral = float(
            shield_grass_lateral if shield_grass_lateral is not None
            else self.bundle.meta.get("shield_grass_lateral", guard_defaults["guard_grass_lateral"])
        )
        if shield_mode is None:
            shield_mode = "takeover" if self.telemetry_version == "legacy_v1" else "filter"
        if shield_mode not in {"takeover", "filter"}:
            raise ValueError(f"unknown shield_mode: {shield_mode}")
        self.shield_mode = str(shield_mode)
        if guard_penalty_weight is None:
            guard_penalty_weight = 0.0 if self.shield_mode == "takeover" else 2.0
        self.guard_penalty_weight = float(guard_penalty_weight)
        self._guard_active = False
        self._last_rollout_violation = 0.0
        self._score_debug = os.environ.get('GWM_SCORE_DEBUG') == '1'
        self._last_score_terms = None
        self._last_pool_terms = None
        if separation_scale is None:
            separation_scale = 0.0 if self.telemetry_version == 'legacy_v1' else 1.0
        self.separation_scale = float(separation_scale)
        if planner_liveness_weight is None:
            planner_liveness_weight = float(self.bundle.meta.get("planner_liveness_weight", 0.0))
        self.liveness_weight = float(planner_liveness_weight)
        if planner_liveness_speed is None:
            planner_liveness_speed = float(self.bundle.meta.get("planner_liveness_speed", 4.0))
        self.liveness_speed = max(float(planner_liveness_speed), 1e-3)
        if maneuver_hold_steps is None:
            maneuver_hold_steps = int(self.bundle.meta.get("planner_maneuver_hold_steps", 1))
        self.maneuver_hold_steps = max(1, min(int(maneuver_hold_steps), self.horizon))
        if corridor_feasibility is None:
            # The lateral corridor is only meaningful in true half-width units;
            # under the archived projection channel it cannot be evaluated.
            corridor_feasibility = self.telemetry_version == 'corrected_v2'
        self.corridor_feasibility = bool(corridor_feasibility)
        if planner_progress_mode is None:
            # ``tile_delta`` differences the cumulative visited-tile fraction
            # obs[9] (1/304 per new tile) and ``speed_norm`` scores predicted
            # speed against the cruise reference. The two were compared head to
            # head on both layouts; the normalised speed term is *worse* and is
            # not used (sw_speednorm vs sw_tiledelta in the 2026-09-20 sweep:
            # 1 vs 5 overtakes and grass 0.772 vs 0.280 on the dense layout,
            # 4 vs 5 overtakes on the sparse one). The archived term stays the
            # default for both protocols.
            planner_progress_mode = 'tile_delta'
        if planner_progress_mode not in {'tile_delta', 'speed_norm'}:
            raise ValueError(f'unknown planner_progress_mode: {planner_progress_mode}')
        self.progress_mode = str(planner_progress_mode)
        if corridor_selection is None:
            corridor_selection = 'penalty' if self.telemetry_version == 'legacy_v1' else 'lexicographic'
        if corridor_selection not in {'penalty', 'lexicographic'}:
            raise ValueError(f'unknown corridor_selection: {corridor_selection}')
        self.corridor_selection = str(corridor_selection)
        # Lateral-clearance feasibility: a candidate whose predicted trajectory
        # runs alongside another vehicle with less than one vehicle width of
        # lateral separation is declared infeasible, exactly like a corridor
        # violation. Contacts in the corrected protocol are dominated by
        # side-by-side squeezes (the hull including its wheels spans 3.2 m), and
        # neither the corridor term nor a soft lane penalty sees them because
        # both vehicles are still inside the road edge. Off by default so that
        # archived runs keep their behaviour.
        if clearance_feasibility is None:
            clearance_feasibility = bool(self.bundle.meta.get('clearance_feasibility', False))
        self.clearance_feasibility = bool(clearance_feasibility)
        if clearance_alongside_length is None:
            clearance_alongside_length = float(self.bundle.meta.get('clearance_alongside_length', 5.5))
        self.clearance_alongside_length = max(float(clearance_alongside_length), 0.0)
        if clearance_lateral_min is None:
            clearance_lateral_min = float(self.bundle.meta.get('clearance_lateral_min', 3.5))
        self.clearance_lateral_min = max(float(clearance_lateral_min), 0.0)
        if shield_escalation_steps is None:
            shield_escalation_steps = self.bundle.meta.get('shield_escalation_steps', 0)
        shield_escalation_steps = int(shield_escalation_steps)
        # ``filter`` keeps the planner in charge and only prices infeasible
        # states. That is enough while the vehicle is nominally on track, but it
        # has no fallback when the filtered planner drives the vehicle off the
        # road and then keeps it there (the 2026-09-20 CLRL trace sits at
        # |lat| ~ 5.3 half-widths with speed 0 for 2000 steps). The shield
        # therefore escalates to a direct takeover once the vehicle has been in
        # an infeasible state for this many consecutive steps. Zero disables the
        # escalation and reproduces the archived filter-only behaviour.
        self.shield_escalation_steps = max(shield_escalation_steps, 0)
        self._infeasible_streak = 0
        # ``filter`` mode prices infeasible candidates instead of replacing the
        # controller, but a filtered planner can still hold an infeasible state
        # for ever (the 2026-09-20 CLRL trace sits off the road for 2000 steps).
        # Escalation therefore exists, but by default it now restricts the
        # candidate pool to zero-violation candidates rather than bypassing the
        # planner; since the scoring pass runs on every escalation step, the
        # neighbourhood and quality terms stay live. Set the bypass flag to
        # recover the archived behaviour where escalation hands control to the
        # geometry recovery action.
        if shield_escalation_bypass is None:
            shield_escalation_bypass = bool(self.bundle.meta.get("shield_escalation_bypass", False))
        self.shield_escalation_bypass = bool(shield_escalation_bypass)
        # ``recovery`` is the archived behaviour: an escalation whose candidate
        # pool holds no zero-violation member hands the vehicle to the geometry
        # recovery action. ``best_available`` keeps the planner on the
        # least-violating candidates instead, which matters whenever the
        # vehicle is already inside the guard band and no clean rollout exists.
        if escalation_fallback is None:
            escalation_fallback = self.bundle.meta.get("escalation_fallback", "recovery")
        if escalation_fallback not in {"recovery", "best_available"}:
            raise ValueError(f"unknown escalation_fallback: {escalation_fallback}")
        self.escalation_fallback = str(escalation_fallback)
        if relevance_memory is None:
            relevance_memory = bool(self.bundle.meta.get("relevance_memory", False))
        self.relevance_memory = bool(relevance_memory)
        # Manoeuvre commitment: hold the vehicle the ego is currently passing in
        # the admitted set for a fixed number of decisions after the last step in
        # which it satisfied the criterion. ``0`` leaves the rule stateless, which
        # is the released configuration.
        if maneuver_commit_steps is None:
            maneuver_commit_steps = int(self.bundle.meta.get("maneuver_commit_steps", 0))
        self.maneuver_commit_steps = max(int(maneuver_commit_steps), 0)
        if maneuver_commit_forward_m is None:
            maneuver_commit_forward_m = float(
                self.bundle.meta.get("maneuver_commit_forward_m", 22.0)
            )
        self.maneuver_commit_forward_m = float(maneuver_commit_forward_m)
        if maneuver_commit_lateral_m is None:
            maneuver_commit_lateral_m = float(
                self.bundle.meta.get("maneuver_commit_lateral_m", 12.0)
            )
        self.maneuver_commit_lateral_m = float(maneuver_commit_lateral_m)
        if maneuver_commit_release_m is None:
            maneuver_commit_release_m = float(
                self.bundle.meta.get("maneuver_commit_release_m", 6.0)
            )
        self.maneuver_commit_release_m = float(maneuver_commit_release_m)
        self._commit_partner = {}
        self._decision_step = 0
        self.reverse_slot_order = bool(reverse_slot_order)
        self._relevance_memory = {}
        if overtake_clear_margin is None:
            overtake_clear_margin = float(self.bundle.meta.get('overtake_clear_margin', 4.0))
        # Lead (in metres, along the local track tangent) by which the vehicle
        # that was blocking the racing line must move behind the ego before the
        # crossing is credited.
        self.overtake_clear_margin = max(float(overtake_clear_margin), 0.0)
        # Corridor-return terms. All three are inert at their defaults, so an
        # archived configuration reproduces bit for bit; a configuration that
        # enables them states the intent explicitly.
        if corridor_return_weight is None:
            corridor_return_weight = float(self.bundle.meta.get('corridor_return_weight', 0.0))
        self.corridor_return_weight = float(corridor_return_weight)
        if corridor_return_candidates is None:
            corridor_return_candidates = int(self.bundle.meta.get('corridor_return_candidates', 0))
        self.corridor_return_candidates = max(int(corridor_return_candidates), 0)
        if corridor_return_gain is None:
            corridor_return_gain = float(self.bundle.meta.get('corridor_return_gain', 1.4))
        self.corridor_return_gain = float(corridor_return_gain)
        if corridor_return_heading_gain is None:
            corridor_return_heading_gain = float(
                self.bundle.meta.get('corridor_return_heading_gain', 1.6)
            )
        self.corridor_return_heading_gain = float(corridor_return_heading_gain)
        if corridor_return_gate is None:
            corridor_return_gate = self.bundle.meta.get('corridor_return_gate')
        self.corridor_return_gate = (
            float(self.shield_lateral) if corridor_return_gate is None else float(corridor_return_gate)
        )
        self.corridor_return_defer_lateral = float(
            self.bundle.meta.get('corridor_return_defer_lateral', 1.0)
        )
        if corridor_recovery_cross_track is None:
            corridor_recovery_cross_track = bool(
                self.bundle.meta.get('corridor_recovery_cross_track', False)
            )
        self.corridor_recovery_cross_track = bool(corridor_recovery_cross_track)
        self.dump_rollouts = bool(dump_rollouts)
        self._rollout_buffer = []
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
        self._frozen_slot_order = {}
        self._relevance_memory = {}
        self._commit_partner = {}
        self._decision_step = 0
        self._infeasible_streak = 0

    def _selected_neighbor_ids(self, obs_raw, exposed, target_agent, frozen_order, sticky_order=None, commit=None):
        """Identities the admission rule kept, taken from the source slots.

        The previous record mapped packed slot positions onto the exposed-id
        list, which only agrees with the truth when the ranking happens to
        preserve the environment's slot order. Reading the source indices the
        rule actually admitted removes that coincidence.
        """
        row = exposed[target_agent]
        source_slot_dim, _, source_use_mask = _infer_source_layout(
            np.asarray(obs_raw, dtype=np.float32).shape[-1]
        )
        if frozen_order is not None:
            indices = list(frozen_order[target_agent])
        else:
            if self.neighbor_mode == "fixed_k":
                selection_mode = "fixed"
            else:
                selection_mode = self.neighbor_selection_mode
            entries = _rank_opponent_slot_entries(
                np.asarray(obs_raw, dtype=np.float32)[target_agent],
                slot_dim=int(source_slot_dim),
                use_slot_mask=bool(source_use_mask),
                selection_mode=selection_mode,
                telemetry_version=self.telemetry_version,
                min_keep=self._min_neighbor_backfill(),
                sticky=None if sticky_order is None else sticky_order[target_agent],
                commit=None if commit is None else commit[target_agent],
            )
            indices = [index for index, _ in entries][: self.slot_budget]
        if self.reverse_slot_order:
            indices = list(indices)[::-1]
        return [int(row[index]) for index in indices if index < len(row)]

    def _min_neighbor_backfill(self):
        """Backfill budget for the relevance ranking, or ``None``.

        Only the backfilled relevance rule fills slots that its own relevance
        test rejected, which is what stops the graph from emptying while
        opponents are still on the road.
        """
        if self.neighbor_selection_mode == "interaction_backfill":
            return self.slot_budget
        return None

    def _maneuver_commit_order(self, obs_raw, exposed, target_agent, agent_count):
        """Per-agent source-slot indices that must stay admitted this step.

        The released admission rule is stateless: the car the ego is closing on
        leaves the graph as soon as the relative geometry shifts, so the
        interaction prediction that the manoeuvre depends on can disappear
        mid-pass. This holds the nearest car ahead inside the approach band for
        ``maneuver_commit_steps`` decisions after the last step in which it was
        live, and releases it once it is more than ``maneuver_commit_release_m``
        metres behind the ego, i.e. once the pass is over.

        Returns ``None`` when the commitment is off, so the released
        configuration stays bit-identical.
        """
        if self.maneuver_commit_steps <= 0 or not self.slot_budget:
            return None
        obs = np.asarray(obs_raw, dtype=np.float32)
        slot_dim, feat_dim, use_mask = _infer_source_layout(obs.shape[-1])
        commit_order = [[] for _ in range(int(agent_count))]
        row = None
        if exposed is not None and target_agent < len(exposed):
            row = exposed[target_agent]
        if row is None or feat_dim < 5:
            return commit_order

        present = {}
        for index in range(len(row)):
            start = EGO_DIM + index * slot_dim
            slot = obs[target_agent, start:start + slot_dim]
            if slot.shape[0] < slot_dim:
                break
            if use_mask and float(slot[-1]) <= 0.0:
                continue
            present[int(row[index])] = (float(slot[0]) * PLAYFIELD, float(slot[1]) * PLAYFIELD)

        live = [vid for vid, (forward_m, left_m) in present.items()
                if 0.0 < forward_m <= self.maneuver_commit_forward_m
                and abs(left_m) <= self.maneuver_commit_lateral_m]
        if os.environ.get("GWM_COMMIT_DEBUG") and self._decision_step <= 400:
            print(f"[commit] step={self._decision_step} budget={self.maneuver_commit_steps} "
                  f"band=({self.maneuver_commit_forward_m},{self.maneuver_commit_lateral_m}) "
                  f"fwd={[round(v[0], 1) for v in present.values()]} "
                  f"lat={[round(v[1], 1) for v in present.values()]} live={live}",
                  flush=True)
        live_ids = {min(live, key=lambda vid: present[vid][0])} if live else set()
        remembered, last_step = self._commit_partner.get(target_agent, (set(), -10 ** 9))
        still_relevant = {vid for vid in remembered
                          if vid in present
                          and present[vid][0] > -self.maneuver_commit_release_m}
        if live_ids:
            keep = live_ids
            self._commit_partner[target_agent] = (keep, self._decision_step)
        elif still_relevant and (self._decision_step - last_step) <= self.maneuver_commit_steps:
            keep = still_relevant
        else:
            keep = set()
            self._commit_partner.pop(target_agent, None)
        if keep:
            commit_order[target_agent] = [index for index, vid in enumerate(row)
                                          if int(vid) in keep]
        return commit_order

    def _source_layout(self, obs_raw):
        return _infer_source_layout(np.asarray(obs_raw, dtype=np.float32).shape[-1])

    def _relevance_sticky_order(self, obs_raw):
        """Per-agent sets of vehicles the previous step admitted.

        A purely instantaneous relevance score makes the graph churn: a vehicle
        that the ego is mid-manoeuvre against can be dropped by a small change
        in the relative geometry. The sticky term keeps that commitment for one
        more step. Returns ``None`` unless relevance memory is enabled, so the
        plain rule stays stateless.
        """
        if not self.relevance_memory or not self.slot_budget:
            return None
        agent_count = int(np.asarray(obs_raw, dtype=np.float32).shape[0])
        return [
            set(self._relevance_memory.get(agent_id, ())) or None
            for agent_id in range(agent_count)
        ]

    def _update_relevance_memory(self, obs_raw, target_agent, sticky_order):
        if not self.relevance_memory or not self.slot_budget or sticky_order is None:
            return
        source_slot_dim, _, source_use_mask = self._source_layout(obs_raw)
        sticky = sticky_order[target_agent] if target_agent < len(sticky_order) else None
        entries = _rank_opponent_slot_entries(
            np.asarray(obs_raw, dtype=np.float32)[target_agent],
            slot_dim=source_slot_dim,
            use_slot_mask=source_use_mask,
            selection_mode=self.neighbor_selection_mode,
            telemetry_version=self.telemetry_version,
            min_keep=self._min_neighbor_backfill(),
            sticky=sticky,
        )
        self._relevance_memory[target_agent] = [index for index, _ in entries][: self.slot_budget]

    def _frozen_neighbor_order(self, obs):
        """Source slot indices frozen at the first decision step.

        This backs the ablation the paper calls "roles assigned once and reused":
        the vehicles that the relevance ranking admitted at the first decision
        step keep their slots for the rest of the episode, even after the binding
        constraint has moved to a different car. Without it the frozen baseline
        is indistinguishable from the dynamic one whenever the number of
        opponents equals the slot budget, which is what made the archived
        selector ablation uninformative.
        """
        if not self.slot_budget:
            return None
        values = np.asarray(obs, dtype=np.float32)
        if values.ndim == 1:
            values = values[None, :]
        agent_count = int(values.shape[0])
        if self._frozen_slot_order and len(self._frozen_slot_order) == agent_count:
            return [self._frozen_slot_order[agent_id] for agent_id in range(agent_count)]
        source_slot_dim, _, source_use_mask = _infer_source_layout(values.shape[1])
        orders = {}
        for agent_id in range(agent_count):
            entries = _rank_opponent_slot_entries(
                values[agent_id],
                slot_dim=source_slot_dim,
                use_slot_mask=source_use_mask,
                selection_mode="interaction",
                telemetry_version=self.telemetry_version,
            )
            orders[agent_id] = [index for index, _ in entries][: self.slot_budget]
        self._frozen_slot_order = orders
        return [orders[agent_id] for agent_id in range(agent_count)]

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
        from types import SimpleNamespace
        context = None
        if self.telemetry_version == 'corrected_v2':
            context = SimpleNamespace(unwrapped=SimpleNamespace(
                telemetry_version=self.telemetry_version,
                observation_type='telemetry_dynamic' if self.bundle.meta.get('use_slot_mask') else 'telemetry'))
        actions = np.zeros((obs.shape[0], 3), dtype=np.float32)
        for agent_id, policy in enumerate(policies):
            if policy is None:
                continue
            actions[agent_id] = policy.act(context, obs)[agent_id]
        return actions

    def _proposal_actions(self, obs):
        obs_norm = self.bundle.normalize_obs(obs)
        obs_tensor = torch.as_tensor(obs_norm, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            return self.bundle.proposal_actor(obs_tensor).cpu().numpy()

    @property
    def planner_geometry(self):
        """Lateral thresholds in half-width units for this telemetry protocol."""
        return PLANNER_GEOMETRY.get(self.telemetry_version, PLANNER_GEOMETRY["legacy_v1"])

    @property
    def planner_speed_limits(self):
        """Speed-limiter thresholds in half-width units for this protocol."""
        return self.planner_geometry["speed"]

    def _derive_slot_budget(self):
        """Opponent slots the trained world model can actually consume.

        ``max_neighbors=None`` means "the environment exposes every vehicle and
        the policy performs its own relevance selection", not "feed the network
        an unbounded number of slots". The transition model has a fixed slot
        count baked into its input width, so packing must still respect it.
        """
        if self.max_neighbors is not None and self.max_neighbors > 0:
            return int(self.max_neighbors)
        meta = self.bundle.meta
        obs_dim = int(meta.get("obs_dim", 0))
        ego_dim = int(meta.get("ego_dim", 17))
        slot_dim = int(meta.get("slot_feature_dim", 7)) + (1 if meta.get("use_slot_mask", False) else 0)
        if obs_dim > ego_dim and slot_dim > 0 and (obs_dim - ego_dim) % slot_dim == 0:
            return (obs_dim - ego_dim) // slot_dim
        return None

    def _quality_proposal_actions(self, obs):
        if self.quality_bundle is None:
            return None
        target_obs_dim = self.quality_expected_obs_dim if self.slot_budget else obs.shape[1]
        selection_mode = "fixed" if self.neighbor_mode == "fixed_k" else self.neighbor_selection_mode
        quality_obs = pack_dynamic_neighbor_obs(
            obs,
            fill=_opponent_fill_vector(self.quality_bundle),
            target_obs_dim=target_obs_dim,
            max_neighbors=self.slot_budget,
            selection_mode=selection_mode,
            telemetry_version=self.telemetry_version,
            min_neighbors=self._min_neighbor_backfill(),
            reverse_ranked=self.reverse_slot_order,
        )
        obs_norm = self.quality_bundle.normalize_obs(quality_obs)
        obs_tensor = torch.as_tensor(obs_norm, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            return self.quality_bundle.actor(obs_tensor).cpu().numpy()

    def _quality_planner_enabled(self):
        return self.quality_bundle is not None and self.quality_planner_mode not in {"", "proposal_only", "off", "none"}

    def _rollout_target_action(self, imagined, proposal_actions, quality_actions, target_agent, candidate, step):
        if step < self.maneuver_hold_steps:
            # A candidate is a manoeuvre primitive: it is evaluated as a held
            # action sequence whenever ``maneuver_hold_steps > 1``. Evaluating
            # only the first step against a continuation policy made four out of
            # five horizon steps candidate-independent, so the pool scores
            # differed by ~1e-2 and selection degenerated to noise.
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

    def _liveness_penalty(self, predicted_speed):
        """Dynamic-feasibility violation: a rollout that leaves the vehicle
        below the minimum controllable speed is scored as infeasible.

        Without this term the planner has no objective gradient once the
        vehicle is slow: the learned heads are out of distribution there and
        all candidates score alike, so the controller settles on a do-nothing
        action and the vehicle never restarts.
        """
        if self.liveness_weight <= 0.0:
            return 0.0
        return float(max(0.0, self.liveness_speed - float(predicted_speed)) / self.liveness_speed)

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
            elif remainder % PRIORITY_RELATION_DIM == 0:
                opponent_dim = PRIORITY_RELATION_DIM
                use_slot_mask = True
            elif remainder % RELATION_DIM == 0:
                opponent_dim = RELATION_DIM
                use_slot_mask = False
        slot_feature_dim = opponent_dim - 1 if use_slot_mask else opponent_dim
        return opponent_dim, slot_feature_dim, use_slot_mask

    def _separation_conflict(self, obs_row):
        """Swept-separation violation of the imagined next state.

        Uses the reference controller's own clearance model (pair half-length
        6.0 m, half-width 3.3 m) so that the planner is scored against the same
        side-by-side criterion the environment exposes as contact.
        """
        if self.separation_scale <= 0.0:
            return 0.0
        opponent_dim, slot_feature_dim, use_slot_mask = self._slot_meta(obs_row)
        if opponent_dim <= 0:
            return 0.0
        worst = 0.0
        for start in range(EGO_DIM, len(obs_row), opponent_dim):
            slot = np.asarray(obs_row[start:start + opponent_dim], dtype=np.float32)
            if slot.shape[0] < opponent_dim:
                break
            if use_slot_mask and float(slot[-1]) <= 0.0:
                continue
            rel = slot[:slot_feature_dim]
            if rel.shape[0] < 2:
                continue
            along = abs(float(rel[0]) * PLAYFIELD)
            lateral = abs(float(rel[1]) * PLAYFIELD)
            margin = max(along / SEPARATION_HALF_LENGTH, lateral / SEPARATION_HALF_WIDTH)
            worst = max(worst, max(0.0, 1.0 - min(margin, 2.0)))
        return float(np.clip(worst, 0.0, 1.0))

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
                    if self.telemetry_version == 'corrected_v2':
                        # Relative velocity remains in world coordinates.
                        forward = np.array([-float(obs_row[5]), float(obs_row[6])])
                        forward /= max(float(np.linalg.norm(forward)), 1e-8)
                        features['nearest_closing_speed'] = max(-float(np.dot([rel_vx, rel_vy], forward)), 0.0)
            if abs(rel_forward) <= 14.0 and abs(rel_left) < 14.0:
                features["alongside_count"] += 1
        return features

    def _recovery_action(self, obs_row, base_action):
        action = np.asarray(base_action, dtype=np.float32).copy()
        lateral = float(obs_row[12])
        if self.telemetry_version == 'corrected_v2':
            lateral = -lateral  # steering formulas below are right-positive
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
        if self.corridor_recovery_cross_track:
            # Outside the racing lane the lookahead controller is the wrong
            # instrument: its cross-track correction is scaled for lane keeping
            # and its steering command saturates at a fraction of the lock the
            # manoeuvre needs. Replace the steering command with the bounded
            # cross-track law for as long as the vehicle is out of the lane.
            # Both entry paths honour the alongside deferral: an override that
            # fires while a car is next to the ego and the ego is still inside
            # the road edge is a cut-in, whatever heading error triggered it.
            if (self._corridor_return_active(obs_row)
                    or (heading_cos < 0.90
                        and abs(self._cross_track_lateral(obs_row)) > self.shield_lateral
                        and not self._corridor_return_deferred(obs_row))):
                action[0] = self._cross_track_return_steer(obs_row)
        return self._speed_limited_action(action, obs_row)

    def _cross_track_lateral(self, obs_row):
        """Cross-track offset in half-widths, signed like the recovering steer.

        ``obs[12]`` is the offset in half-widths, but which side of the
        centreline it calls positive is a property of the telemetry protocol
        rather than of the vehicle: the corrected channel reports a
        left-positive offset in a body frame whose physical forward axis is
        local +Y, so it points the opposite way from the archived projection.
        The mapping below was measured closed-loop - a vehicle placed 17 m off
        the centreline recovers with full lock in this direction and diverges
        in the other - instead of being read off the protocol comment.
        """
        lateral = float(obs_row[12])
        if self.telemetry_version == 'corrected_v2':
            return lateral
        return -lateral

    def _cross_track_return_steer(self, obs_row):
        """Bounded, monotone cross-track return command in [-1, 1].

        The archived recovery law folded the cross-track offset into a heading
        command, ``desired_angle + gain * e / 40``, and wrapped the result to
        ``(-pi, pi]``. That is monotone only while ``gain * e / 40 < pi``: past
        roughly 7 m of offset the wrap inverts the command and drives the
        vehicle further out, which is exactly the range a recovery manoeuvre
        has to work in. This command is a saturated function of the offset and
        the heading error, so it stays monotone everywhere.
        """
        lateral = self._cross_track_lateral(obs_row)
        heading_error = math.atan2(float(obs_row[13]), float(obs_row[14]))
        steer = self.corridor_return_gain * lateral - self.corridor_return_heading_gain * heading_error
        return float(np.clip(steer, -1.0, 1.0))

    def _corridor_return_active(self, obs_row):
        """Whether the corridor-return layer may act on this state.

        The layer is an edge guard, not a lane-keeping law: it is inert while
        the vehicle is anywhere inside ``corridor_return_gate``, so a pass that
        moves out to the outer lane keeps its full lateral envelope.  Beyond
        the gate it defers while a vehicle is alongside and the ego is still
        inside the road edge, because cutting back to the racing line with a
        car in the adjacent lane is a contact, not a recovery.  Outside the
        road edge the guard always acts.
        """
        lateral = abs(self._cross_track_lateral(obs_row))
        if lateral <= self.corridor_return_gate:
            return False
        return not self._corridor_return_deferred(obs_row)

    def _corridor_return_deferred(self, obs_row):
        """Whether an alongside vehicle suspends the return layer.

        The layer yields while a car is alongside and the ego is still inside
        ``corridor_return_defer_lateral``; past that offset the ego is at the
        road edge and the return acts unconditionally.
        """
        lateral = abs(self._cross_track_lateral(obs_row))
        if lateral > self.corridor_return_defer_lateral:
            return False
        return self._traffic_features(obs_row)["alongside_count"] > 0

    def _anchor_action(self, env, obs, target_agent, fallback_action):
        if not self.use_rule_anchor:
            return self._speed_limited_action(fallback_action, obs[target_agent])
        try:
            action = self.anchor_policy.act(env, obs)[target_agent]
        except Exception:
            action = fallback_action
        return self._speed_limited_action(action, obs[target_agent])

    @staticmethod
    def _track_tile_length(track_xy):
        """Mean spacing between consecutive centre-line tiles, in metres."""
        if len(track_xy) < 2:
            return 1.0
        closed = np.vstack([track_xy, track_xy[:1]])
        step = np.linalg.norm(np.diff(closed, axis=0), axis=1)
        return float(np.mean(step))

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
            speed_table = self.planner_speed_limits
            obs_row = np.asarray(obs[target_agent], dtype=np.float32)
            lateral = abs(float(obs_row[12]))
            heading_cos = float(obs_row[14])
            lateral_term = self.geometry_lateral_speed_weight * max(
                0.0, lateral - speed_table["limit_lateral_ref"])
            heading_term = self.geometry_heading_speed_weight * max(
                0.0, speed_table["limit_heading_ref"] - heading_cos)
            lat_accel_max = speed_table.get("lat_accel_max")
            if lat_accel_max:
                # Physical cornering limit: kappa is rad per tile, so dividing
                # by the tile spacing turns it into rad/m and the admissible
                # speed is sqrt(a_lat / kappa).
                tile_length = self._track_tile_length(track_xy)
                curvature_per_m = curvature / max(tile_length, 1e-6)
                radius_m = 1e4 if curvature_per_m <= 1e-9 else min(1.0 / curvature_per_m, 1e4)
                v_curve = math.sqrt(float(lat_accel_max) * radius_m)
                speed_limit = min(base_speed, v_curve) - lateral_term - heading_term
                sharp_turn = bool(radius_m < float(speed_table["sharp_radius_m"]))
            else:
                curvature_per_m = None
                radius_m = None
                speed_limit = base_speed - self.geometry_curvature_speed_weight * curvature - lateral_term - heading_term
                sharp_turn = bool(curvature > 0.030 or (curvature > 0.020 and lateral > speed_table["sharp_lateral"]))
            context = {
                "curvature": float(curvature),
                "curvature_per_m": None if curvature_per_m is None else float(curvature_per_m),
                "radius_m": None if radius_m is None else float(radius_m),
                "target_speed": float(max(self.geometry_min_speed, min(base_speed, speed_limit))),
                "sharp_turn": sharp_turn,
            }
        except Exception:
            context = {"curvature": 0.0, "target_speed": base_speed, "sharp_turn": False}
        self._geometry_context = context
        return context

    def _speed_limited_action(self, action, obs_row):
        action = np.asarray(action, dtype=np.float32).copy()
        gate = self.planner_speed_limits
        speed = float(obs_row[4]) * 50.0
        lateral = abs(float(obs_row[12]))
        heading_cos = float(obs_row[14])
        on_grass = float(obs_row[15]) > 0.5
        safe_speed = float(self._geometry_context.get("target_speed", self.target_speed))
        if heading_cos < gate["heading_damp_cos"]:
            safe_speed -= 5.0
        if lateral > gate["lane_damp_lateral"]:
            safe_speed -= 4.0
        safe_speed = max(self.geometry_min_speed if self.geometry_generalization else 10.0, safe_speed)
        if self.geometry_generalization and self._geometry_context.get("sharp_turn", False):
            if lateral > gate["sharp_lateral"] or heading_cos < gate["sharp_heading_cos"]:
                action[0] *= 0.82
            # The cornering limit is enforced through ``safe_speed``: the
            # throttle cap only binds once the vehicle is already at the
            # admissible speed, so the limiter no longer prevents a slow
            # vehicle from accelerating up to it.
            if speed >= safe_speed - 1.0 and (lateral > gate["sharp_lateral"] or heading_cos < gate["sharp_heading_cos"]):
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
        if (heading_cos < gate["brake_heading_cos"] or lateral > gate["brake_lateral"]) and speed > 12.0:
            action[1] = min(action[1], 0.08)
            action[2] = max(action[2], 0.28)
        action[0] = np.clip(action[0], -1.0, 1.0)
        action[1:] = np.clip(action[1:], 0.0, 1.0)
        return action

    def _needs_hard_recovery(self, obs_row):
        if not self.recovery_enabled or not self.overtake_aware_planner or not self.hard_safety_shield:
            return False
        lateral = abs(float(obs_row[12]))
        heading_cos = float(obs_row[14])
        on_grass = float(obs_row[15]) > 0.5
        backward = float(obs_row[16]) > 0.5
        severe_grass = on_grass and (lateral > self.shield_grass_lateral or heading_cos < 0.70)
        return bool(backward or severe_grass or lateral > self.shield_lateral or heading_cos < self.shield_heading_cos)

    def _guard_violation(self, target_row):
        """Severity of the state the safety guard is meant to prevent.

        Used by ``shield_mode='filter'`` to score candidates that keep the
        vehicle in an unsafe state instead of bypassing the planner.
        """
        lateral = abs(float(target_row[12]))
        heading_cos = float(target_row[14])
        on_grass = float(target_row[15]) > 0.5
        backward = float(target_row[16]) > 0.5
        severity = 0.0
        severity += 1.0 if backward else 0.0
        if on_grass:
            severity += 1.0 + max(0.0, lateral - self.shield_grass_lateral)
        severity += max(0.0, lateral - self.shield_lateral)
        severity += max(0.0, self.shield_heading_cos - heading_cos)
        return float(severity)

    def _clearance_violation(self, obs_row, target_agent):
        """Severity of a predicted pass that is geometrically too tight.

        Read from the same relative-neighbour slots the planner already uses,
        so it needs no additional world-model head. A slot that is
        longitudinally overlapping (|rel_forward| <= clearance_alongside_length)
        must also be laterally separated by at least clearance_lateral_min;
        the shortfall is the violation. Vehicles that are clearly behind or
        clearly ahead are left to the existing gap terms.
        """
        row = np.asarray(obs_row[target_agent], dtype=np.float32)
        opponent_dim, slot_feature_dim, use_slot_mask = self._slot_meta(row)
        if opponent_dim <= 0:
            return 0.0
        severity = 0.0
        for start in range(EGO_DIM, len(row), opponent_dim):
            slot = np.asarray(row[start:start + opponent_dim], dtype=np.float32)
            if slot.shape[0] < opponent_dim or slot_feature_dim < 5:
                break
            if use_slot_mask and float(slot[-1]) <= 0.0:
                continue
            rel_forward = float(slot[0]) * PLAYFIELD
            rel_left = float(slot[1]) * PLAYFIELD
            if abs(rel_forward) <= self.clearance_alongside_length:
                severity += max(0.0, self.clearance_lateral_min - abs(rel_left))
        return float(severity)

    def _candidate_pool(self, proposal_target, background_target, target_obs=None, extra_targets=None,
                        head_targets=None):
        base = np.asarray(proposal_target, dtype=np.float32)
        background = np.asarray(background_target, dtype=np.float32)
        pools = [base, background]
        for item in extra_targets or []:
            pools.append(np.asarray(item, dtype=np.float32))
        for item in reversed(list(head_targets or [])):
            pools.insert(0, np.asarray(item, dtype=np.float32))
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
            if self.telemetry_version == 'corrected_v2':
                lateral = -lateral
            heading_error = math.atan2(float(target_obs[13]), float(target_obs[14]))
            on_grass = float(target_obs[15]) > 0.5
            backward = float(target_obs[16]) > 0.5
            geometry = self.planner_geometry
            recovery_needed = self.recovery_enabled and (
                abs(lateral) > geometry["edge"] or float(target_obs[14]) < 0.66 or backward
            )
            geom_target_speed = float(self._geometry_context.get("target_speed", self.target_speed))
            sharp_turn = bool(self._geometry_context.get("sharp_turn", False))

            if self.corridor_return_candidates > 0:
                return_lateral = self._cross_track_lateral(target_obs)
                if self._corridor_return_active(target_obs):
                    # Graded return primitives: the pool otherwise carries only
                    # manoeuvre candidates whose lane-keeping steering is far
                    # too gentle to close a large cross-track offset, and the
                    # learned rollouts of the remaining candidates differ by
                    # less than the planner noise floor. These are inserted at
                    # the head of the pool because the pool is truncated to
                    # ``self.candidates``.
                    heading_error_return = math.atan2(float(target_obs[13]), float(target_obs[14]))
                    for index in range(self.corridor_return_candidates):
                        gain = self.corridor_return_gain * (1.0 + 0.8 * index)
                        steer = float(np.clip(
                            gain * return_lateral
                            - self.corridor_return_heading_gain * heading_error_return,
                            -1.0,
                            1.0,
                        ))
                        cand = base.copy()
                        cand[0] = steer
                        cand[1] = max(float(base[1]), 0.45)
                        cand[2] = 0.0 if speed < 16.0 else 0.18
                        pools.insert(index, cand)

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

            allow_pass = (not recovery_needed and abs(lateral) < geometry["pass_open"]
                          and float(target_obs[14]) > 0.84)
            if self.geometry_generalization and sharp_turn:
                allow_pass = (allow_pass and abs(lateral) < 0.6 * geometry["pass_open"]
                              and traffic["nearest_forward"] is not None
                              and traffic["nearest_forward"] < 18.0)
            if allow_pass and (traffic["nearest_forward"] is not None or traffic["alongside_count"] > 0):
                pass_side = -1.0 if traffic["nearest_left"] >= 0.0 else 1.0
                if self.telemetry_version == 'corrected_v2':
                    pass_side = -pass_side
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
                    if self.telemetry_version == 'corrected_v2':
                        brake[0] = -brake[0]
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

    def _track_frame_slots(self, obs_row):
        """Neighbour-slot positions in the *track* frame rather than the body frame.

        The stored slots are body-relative, so a yaw command alone moves a
        vehicle that is dead ahead of the ego out of the forward cone. The
        overtake term below is a function of these slots, and a body-frame
        version of it is therefore maximised by steering hard rather than by
        passing: in the frozen 2026-09-20 trace two hard-steer candidates
        collect +4.5 of the +2.4-weighted overtake credit while the fastest
        candidate collects +0.3, and the selected action holds |steer| ~ 0.3
        for hundreds of steps. Rotating the slots into the local track frame
        with the recorded heading error makes every manoeuvre term invariant to
        the ego's yaw, so the only way to earn the credit is to change the
        actual lead.

        heading error e (obs[13], obs[14]) satisfies
            t = cos(e) * f + sin(e) * l,   n = -sin(e) * f + cos(e) * l
        for the body axes (f = forward, l = left) and the track axes
        (t = tangent, n = left normal), hence
            along = rf * cos(e) + rl * sin(e)
            cross = -rf * sin(e) + rl * cos(e)
        Only ``along`` and ``|cross|`` enter the manoeuvre terms, so the sign
        convention of the lateral component is not observable downstream.
        """
        sin_e = float(obs_row[13])
        cos_e = float(obs_row[14])
        opponent_dim, slot_feature_dim, use_slot_mask = self._slot_meta(obs_row)
        slots = []
        if opponent_dim <= 0 or slot_feature_dim < 2:
            return slots
        for start in range(EGO_DIM, len(obs_row), opponent_dim):
            slot = np.asarray(obs_row[start:start + opponent_dim], dtype=np.float32)
            if slot.shape[0] < opponent_dim:
                break
            if use_slot_mask and float(slot[-1]) <= 0.0:
                continue
            rel_forward = float(slot[0]) * PLAYFIELD
            rel_left = float(slot[1]) * PLAYFIELD
            slots.append((rel_forward * cos_e + rel_left * sin_e,
                          -rel_forward * sin_e + rel_left * cos_e))
        return slots

    def _state_quality_terms(self, previous_obs, next_obs, target_agent):
        prev_target = previous_obs[target_agent]
        next_target = next_obs[target_agent]
        prev_traffic = self._traffic_features(prev_target)
        next_traffic = self._traffic_features(next_target)
        geometry = self.planner_geometry
        lateral = abs(float(next_target[12]))
        heading_cos = float(next_target[14])
        heading_error = math.acos(float(np.clip(heading_cos, -1.0, 1.0)))
        on_grass = float(next_target[15]) > 0.5
        backward = float(next_target[16]) > 0.5
        speed = float(next_target[4]) * 50.0

        # Manoeuvre credit, evaluated in the track frame. A vehicle is "on the
        # racing line" while it is ahead of the ego by less than the cone length
        # and laterally close in track coordinates.
        ahead_cone = 65.0
        lateral_cone = 18.0
        prev_slots = self._track_frame_slots(prev_target)
        next_slots = self._track_frame_slots(next_target)
        prev_ahead = [(index, along) for index, (along, cross) in enumerate(prev_slots)
                      if 0.0 < along < ahead_cone and abs(cross) < lateral_cone]
        next_ahead = [(index, along) for index, (along, cross) in enumerate(next_slots)
                      if 0.0 < along < ahead_cone and abs(cross) < lateral_cone]
        overtake_score = 0.0
        if prev_ahead:
            cleared = 0
            for index, _ in prev_ahead:
                if index < len(next_slots) and next_slots[index][0] <= -self.overtake_clear_margin:
                    cleared += 1
            if cleared:
                overtake_score += 1.2 * cleared
            elif next_ahead:
                prev_lead = min(along for _, along in prev_ahead)
                next_lead = min(along for _, along in next_ahead)
                gap_delta = (prev_lead - next_lead) / ahead_cone
                overtake_score += float(np.clip(gap_delta, -0.4, 0.8))
            overtake_score += 0.35 * max(len(prev_ahead) - len(next_ahead), 0)
        overtake_score += 0.03 * max(speed - min(self.target_speed, 18.0), 0.0)

        lane_penalty = lateral + 0.55 * heading_error
        if lateral > geometry["lane_free"]:
            lane_penalty += 1.8 * (lateral - geometry["lane_free"])
        if heading_cos < 0.82:
            lane_penalty += 1.2 * (0.82 - heading_cos)
        if on_grass or backward or lateral > geometry["edge"]:
            overtake_score = min(overtake_score, 0.0)
        grass_penalty = 2.5 * float(on_grass) + 1.2 * float(backward)
        if lateral > geometry["edge"]:
            grass_penalty += 0.8 * (lateral - geometry["edge"])
        close_gap_penalty = 0.0
        if next_traffic["nearest_forward"] is not None:
            close_gap_penalty = max(0.0, 10.0 - next_traffic["nearest_forward"]) / 10.0
        close_gap_penalty = max(close_gap_penalty, self._separation_conflict(next_target))
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
            geometry_barrier += max(0.0, lateral - geometry["lane_free"]) * (1.0 + 8.0 * curvature)
            geometry_barrier += max(0.0, 0.78 - heading_cos) * (1.0 + 10.0 * curvature)
            geometry_barrier += 1.2 * float(on_grass) * (1.0 + 6.0 * curvature)
            elegance_barrier += self.geometry_barrier_weight * geometry_barrier
        return overtake_score, lane_penalty, grass_penalty, close_gap_penalty, elegance_barrier

    def _preserve_rollout_masks(self, current, predicted):
        # Slot presence is determined by the latest real telemetry graph.
        # Preserve it for every telemetry protocol so imagined rollout cannot
        # invent a vehicle or remove a selected one between real observations.
        if not self.bundle.meta.get('use_slot_mask', False):
            return predicted
        predicted = np.asarray(predicted, dtype=np.float32).copy()
        if not np.isfinite(predicted).all():
            raise ValueError('Nonfinite world-model prediction')
        current = np.asarray(current, dtype=np.float32)
        if current.shape[-1] < 17 or predicted.shape[-1] < 17:
            raise ValueError('Packed observations must contain the 17-dimensional self block')
        slot_dim, _, _ = _infer_source_layout(current.shape[-1])
        mask_index = slot_dim - 1
        before_slots = current.shape[-1] - 17
        after_slots = predicted.shape[-1] - 17
        if before_slots % slot_dim or after_slots % slot_dim or before_slots != after_slots:
            raise ValueError(f'Current and predicted packed observations must share one masked slot layout: current={current.shape}, predicted={predicted.shape}')
        before = current[..., 17:].reshape(*current.shape[:-1], -1, slot_dim)
        after = predicted[..., 17:].reshape(*predicted.shape[:-1], -1, slot_dim)
        # Real-step selection defines presence; a decoder cannot invent a new vehicle.
        after[..., mask_index] = before[..., mask_index]
        inactive = before[..., mask_index] <= .5
        after[inactive] = before[inactive]
        return predicted

    def _check_ensemble_compatibility(self):
        """Refuse to ensemble members that do not share one observation layout."""
        first = self.bundle.meta
        keys = (
            "telemetry_version",
            "obs_dim",
            "action_dim",
            "use_slot_mask",
            "opponent_dim",
            "slot_dim",
            "neighbor_selection",
            "num_agents",
        )
        for bundle in self.bundles[1:]:
            for key in keys:
                if bundle.meta.get(key) != first.get(key):
                    raise ValueError(
                        f"Ensemble members disagree on {key}: "
                        f"{first.get(key)!r} against {bundle.meta.get(key)!r}"
                    )

    def _ensemble_transition(self, obs_tensor, act_tensor):
        """One transition from every member, fused into a single prediction.

        The state head is averaged in normalized space. The aleatoric head keeps
        the mean of the per-member variances and is inflated by the variance of
        the member means, so disagreement between members shows up as the
        epistemic part of the uncertainty the planner already penalizes. Reward,
        risk and the auxiliary quality head are averaged in the same way.
        """
        outs = [bundle.transition(obs_tensor, act_tensor) for bundle in self.bundles]
        if len(outs) == 1:
            return outs[0]
        merged = dict(outs[0])
        with torch.no_grad():
            next_mu = torch.stack([out["next_mu"] for out in outs], dim=0)
            merged["next_mu"] = next_mu.mean(dim=0)
            epistemic = (next_mu.var(dim=0, unbiased=False)
                         if self.ensemble_epistemic else torch.zeros_like(next_mu[0]))
            aleatoric = torch.stack([out["next_logvar"] for out in outs], dim=0).exp().mean(dim=0)
            merged["next_logvar"] = torch.log(aleatoric + epistemic + 1e-8)
            for key in ("reward_mu", "reward_logvar", "risk_logits"):
                merged[key] = torch.stack([out[key] for out in outs], dim=0).mean(dim=0)
            if outs[0].get("quality_pred") is not None:
                merged["quality_pred"] = torch.stack(
                    [out["quality_pred"] for out in outs], dim=0
                ).mean(dim=0)
            if outs[0].get("attn_entropy") is not None:
                merged["attn_entropy"] = torch.stack(
                    [out["attn_entropy"] for out in outs], dim=0
                ).mean(dim=0)
        return merged

    def _probe_one_step(self, env, obs, action):
        """Diagnostic: one real environment step predicted by the world model."""
        obs = np.asarray(obs, dtype=np.float32)
        target_obs_dim = self.bundle.meta.get("obs_dim") if self.slot_budget else obs.shape[1]
        selection_mode = "fixed" if self.neighbor_mode == "fixed_k" else self.neighbor_selection_mode
        packed = pack_dynamic_neighbor_obs(
            obs,
            fill=_opponent_fill_vector(self.bundle),
            target_obs_dim=target_obs_dim,
            max_neighbors=self.slot_budget,
            selection_mode=selection_mode,
            telemetry_version=self.telemetry_version,
            min_neighbors=self._min_neighbor_backfill(),
            reverse_ranked=self.reverse_slot_order,
        )
        full_action = np.asarray(action, dtype=np.float32).copy()
        with torch.no_grad():
            out = self._ensemble_transition(
                torch.as_tensor(self.bundle.normalize_obs(packed)[None, ...], dtype=torch.float32, device=self.device),
                torch.as_tensor(self.bundle.normalize_action(full_action)[None, ...], dtype=torch.float32, device=self.device),
            )
            next_obs = self.bundle.denormalize_obs(out["next_mu"].cpu().numpy()[0])
        next_obs = self._preserve_rollout_masks(packed, next_obs)
        return next_obs

    def _score_candidate(self, obs, proposal_actions, background_policies, candidate, target_agent, quality_actions=None):
        imagined = np.asarray(obs, dtype=np.float32).copy()
        score = 0.0
        discount = 1.0
        violation_total = 0.0
        rollout_states = [np.asarray(imagined)[:, [0, 1, 4]].tolist()] if self.dump_rollouts else None
        terms = None
        if self._score_debug:
            terms = {key: 0.0 for key in (
                'reward', 'progress', 'liveness', 'overtake', 'learned_quality', 'risk',
                'uncertainty', 'imitation', 'lane', 'grass', 'close_gap', 'elegance',
                'corridor_return')}
            terms['speed_mean'] = 0.0
            terms['discount_sum'] = 0.0
        proposal = np.asarray(proposal_actions, dtype=np.float32)
        quality = None if quality_actions is None else np.asarray(quality_actions, dtype=np.float32)
        # Model-free corridor-return credit. The learned rollout is smooth in
        # its lateral channel: over a four-step horizon every candidate in the
        # pool predicts almost the same cross-track offset, so ranking by
        # imagined lateral error alone leaves the return primitive and the
        # lane-keeping primitive indistinguishable. This term scores the
        # commanded steering against the direction that reduces the *observed*
        # offset, which is what the geometric recovery law acts on, and is
        # applied only outside the lane.
        corridor_return_term = 0.0
        if self.corridor_return_weight > 0.0:
            return_lateral = self._cross_track_lateral(imagined[target_agent])
            if self._corridor_return_active(imagined[target_agent]):
                command = float(np.clip(self.corridor_return_gain * return_lateral, -1.0, 1.0))
                steer = float(np.asarray(candidate, dtype=np.float32).reshape(-1)[0])
                corridor_return_term = self.corridor_return_weight * command * steer
        for step in range(self.horizon):
            if step == 0 and corridor_return_term != 0.0:
                score += discount * corridor_return_term
                if terms is not None:
                    terms['corridor_return'] += discount * corridor_return_term
            if self.world_model_mode == "no_world_model":
                # Matched planner control: retain the same candidate pool and
                # action selection, but score from the current observation with
                # a deterministic one-step proxy instead of a learned rollout.
                action = np.asarray(candidate, dtype=np.float32)
                ego_obs = imagined[target_agent]
                throttle = float(action[1]) if action.shape[0] > 1 else 0.0
                brake = float(action[2]) if action.shape[0] > 2 else 0.0
                steer = float(action[0]) if action.shape[0] else 0.0
                speed_norm = float(np.clip(abs(ego_obs[4]), 0.0, 2.0))
                progress = 0.02 * (throttle - brake) * max(speed_norm, 0.25)
                lateral_now = float(ego_obs[12]) if len(ego_obs) > 12 else 0.0
                heading_now = float(ego_obs[14]) if len(ego_obs) > 14 else 1.0
                grass_now = float(ego_obs[15]) if len(ego_obs) > 15 else 0.0
                reverse_now = float(ego_obs[16]) if len(ego_obs) > 16 else 0.0
                lane_penalty = abs(lateral_now + 0.08 * steer)
                grass_penalty = grass_now + 0.25 * max(abs(lateral_now + 0.08 * steer) - 0.45, 0.0)
                close_gap_penalty = max(0.0, 0.5 - (throttle - brake)) * 0.1
                risk = grass_now + reverse_now + max(0.0, 0.82 - heading_now)
                uncertainty = 0.0
                imitation = self._imitation_penalty(action, proposal[target_agent],
                                                    quality[target_agent] if quality is not None else None)
                liveness = self._liveness_penalty(abs(speed_norm) * 50.0)
                score += discount * (
                    self.progress_weight * progress
                    - self.liveness_weight * liveness
                    - self.risk_weight * risk
                    - self.uncertainty_weight * uncertainty
                    - self.imitation_weight * imitation
                    - self.lane_quality_weight * lane_penalty
                    - self.grass_penalty_weight * grass_penalty
                    - self.close_gap_penalty_weight * close_gap_penalty
                )
                if terms is not None:
                    terms['progress'] += discount * self.progress_weight * progress
                    terms['liveness'] += discount * (-self.liveness_weight) * liveness
                    terms['risk'] += discount * (-self.risk_weight) * risk
                    terms['imitation'] += discount * (-self.imitation_weight) * imitation
                    terms['lane'] += discount * (-self.lane_quality_weight) * lane_penalty
                    terms['grass'] += discount * (-self.grass_penalty_weight) * grass_penalty
                    terms['close_gap'] += discount * (-self.close_gap_penalty_weight) * close_gap_penalty
                    terms['speed_mean'] += discount * abs(speed_norm) * 50.0
                    terms['discount_sum'] += discount
                if self._guard_active or self.corridor_feasibility:
                    # One-step proxy: the violating state is the current one, so
                    # only the action's steering/throttle response is visible.
                    proxied = np.asarray(imagined, dtype=np.float32).copy()
                    proxied[target_agent, 12] = lateral_now + 0.08 * steer
                    proxied[target_agent, 15] = max(grass_now, float(abs(proxied[target_agent, 12]) > 0.94))
                    proxied[target_agent, 16] = reverse_now
                    violation_total += discount * self._guard_violation(proxied[target_agent])
                    if self.clearance_feasibility:
                        violation_total += discount * self._clearance_violation(proxied, target_agent)
                if rollout_states is not None:
                    rollout_states.append(np.asarray(proxied)[:, [0, 1, 4]].tolist())
                # (guard/feasibility penalty already accumulated above)
                discount *= self.gamma
                continue
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
                out = self._ensemble_transition(obs_tensor, act_tensor)
                if "state" in self.disabled_heads:
                    next_obs = np.asarray(imagined, dtype=np.float32).copy()
                else:
                    next_norm = out["next_mu"].cpu().numpy()[0]
                    next_obs = self.bundle.denormalize_obs(next_norm)
                    next_obs = self._preserve_rollout_masks(imagined, next_obs)
                reward = 0.0 if "reward" in self.disabled_heads else float(out["reward_mu"].cpu().numpy()[0, target_agent])
                risk = 0.0 if "risk" in self.disabled_heads else float(torch.sigmoid(out["risk_logits"])[0, target_agent].cpu().numpy())
                uncertainty = 0.0 if "uncertainty" in self.disabled_heads else float(
                    np.clip(
                        out["next_logvar"].cpu().numpy()[0, target_agent, 0]
                        + out["reward_logvar"].cpu().numpy()[0, target_agent],
                        -2.0,
                        4.0,
                    )
            )
            predicted_speed = float(next_obs[target_agent, 4]) * 50.0
            tile_delta = float(next_obs[target_agent, 9] - imagined[target_agent, 9])
            if self.progress_mode == 'speed_norm':
                progress = float(np.clip(predicted_speed / max(self.target_speed, 1e-3), 0.0, 1.0))
            else:
                progress = tile_delta
            liveness = self._liveness_penalty(predicted_speed)
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
                - self.liveness_weight * liveness
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
            if terms is not None:
                terms['reward'] += discount * reward
                terms['progress'] += discount * self.progress_weight * progress
                terms['liveness'] += discount * (-self.liveness_weight) * liveness
                terms['overtake'] += discount * overtake_weight * overtake
                terms['learned_quality'] += discount * learned_quality_score
                terms['risk'] += discount * (-self.risk_weight) * risk
                terms['uncertainty'] += discount * (-self.uncertainty_weight) * uncertainty
                terms['imitation'] += discount * (-self.imitation_weight) * imitation
                terms['lane'] += discount * (-lane_weight) * lane_penalty
                terms['grass'] += discount * (-grass_weight) * grass_penalty
                terms['close_gap'] += discount * (-close_gap_weight) * close_gap_penalty
                terms['elegance'] += discount * (-self.elegance_barrier_weight) * elegance_barrier
                terms['speed_mean'] += discount * predicted_speed
                terms['discount_sum'] += discount
            if self._guard_active or self.corridor_feasibility:
                violation_total += discount * self._guard_violation(next_obs[target_agent])
            if self.clearance_feasibility:
                violation_total += discount * self._clearance_violation(next_obs, target_agent)
            if rollout_states is not None:
                rollout_states.append(np.asarray(next_obs)[:, [0, 1, 4]].tolist())
            imagined = next_obs
            discount *= self.gamma
        if self._guard_active or self.corridor_feasibility or self.clearance_feasibility:
            score -= self.guard_penalty_weight * violation_total
        self._last_rollout_violation = float(violation_total)
        if terms is not None:
            terms['guard_violation'] = -self.guard_penalty_weight * violation_total
            terms['total'] = float(score)
            terms['speed_mean'] = terms['speed_mean'] / max(terms['discount_sum'], 1e-9)
            self._last_score_terms = terms
        if rollout_states is not None:
            self._rollout_buffer.append(rollout_states)
        return score

    def _score_candidate_pool(self, obs, proposal_actions, background_policies, candidate_pool,
                              target_agent, quality_actions=None):
        scores = []
        violations = []
        pool_terms = [] if self._score_debug else None
        for candidate in candidate_pool:
            scores.append(self._score_candidate(obs, proposal_actions, background_policies, candidate,
                                                target_agent, quality_actions=quality_actions))
            violations.append(float(self._last_rollout_violation))
            if pool_terms is not None:
                pool_terms.append(self._last_score_terms)
        self._last_pool_terms = pool_terms
        self._last_pool_violations = violations
        if self.corridor_selection == 'lexicographic' and (
                self.corridor_feasibility or self.clearance_feasibility):
            # Constrained-MPC ordering: feasibility first, objective second.
            # Candidates are grouped by their predicted corridor-violation
            # severity rounded to 1e-2, and the score is shifted by a constant
            # that dominates any objective difference, so the pool is ranked
            # lexicographically by (violation, -score). A soft penalty alone was
            # not enough: the selected action stayed outside the corridor on
            # 43 % of the closed-loop steps while the underlying imitation actor
            # used alone kept |lat| <= 0.95 with grass 0.000.
            scores = [
                float(score) - 1.0e3 * round(float(violation), 2)
                for score, violation in zip(scores, violations)
            ]
        return scores

    def act(self, env, obs):
        from dlc.observation_layout import require_checkpoint_version
        require_checkpoint_version(env, self.bundle.meta)
        if (getattr(env.unwrapped, 'telemetry_version', 'legacy_v1') == 'corrected_v2'
                and self.neighbor_mode == 'fixed_k'
                and env.unwrapped.neighbor_order != 'identity'):
            raise ValueError('Fixed identity requires identity-ordered environment observations')
        obs_raw = np.asarray(obs, dtype=np.float32)
        target_agent = self._active_target_agent(obs_raw.shape[0])
        frozen_order = None
        sticky_order = None
        commit_order = None
        selected_ids = None
        obs = obs_raw
        if self.neighbor_mode in {"dynamic", "fixed_k"}:
            target_obs_dim = self.bundle.meta.get("obs_dim") if self.slot_budget else obs_raw.shape[1]
            selection_mode = "fixed" if self.neighbor_mode == "fixed_k" else self.neighbor_selection_mode
            if self.neighbor_selection_mode == "fixed_initial":
                frozen_order = self._frozen_neighbor_order(obs_raw)
            sticky_order = self._relevance_sticky_order(obs_raw)
            exposed = getattr(env.unwrapped, "last_dynamic_neighbor_ids", None)
            if self.maneuver_commit_steps > 0:
                self._decision_step += 1
                commit_order = self._maneuver_commit_order(
                    obs_raw, exposed, target_agent, obs_raw.shape[0]
                )
            if exposed is not None and self.slot_budget:
                selected_ids = self._selected_neighbor_ids(
                    obs_raw, exposed, target_agent, frozen_order, sticky_order, commit_order
                )
            obs = pack_dynamic_neighbor_obs(
                obs_raw,
                fill=_opponent_fill_vector(self.bundle),
                target_obs_dim=target_obs_dim,
                max_neighbors=self.slot_budget,
                selection_mode=selection_mode,
                telemetry_version=self.telemetry_version,
                slot_order=frozen_order,
                min_neighbors=self._min_neighbor_backfill(),
                sticky_order=sticky_order,
                reverse_ranked=self.reverse_slot_order,
                commit_order=commit_order,
            )
            self._update_relevance_memory(obs_raw, target_agent, sticky_order)
        self._update_geometry_context(env, obs, target_agent)
        proposal_actions = self._proposal_actions(obs)
        quality_actions = self._quality_proposal_actions(obs)
        background_policies = self._make_background_policies(obs.shape[0])
        background_actions = self._background_action(obs, background_policies)
        anchor_target = self._anchor_action(env, obs, target_agent, background_actions[target_agent])
        self.last_decision_debug = {
            "target_agent": int(target_agent),
            "exposed_neighbor_ids": None if getattr(env.unwrapped, "last_dynamic_neighbor_ids", None) is None
            else [int(item) for item in env.unwrapped.last_dynamic_neighbor_ids[target_agent]],
            "selected_neighbor_ids": selected_ids,
            "committed_neighbor_ids": None if commit_order is None else list(commit_order[target_agent]),
            "geometry_generalization": bool(self.geometry_generalization),
            "geometry_context": dict(self._geometry_context),
            "hard_recovery": False,
            "candidate_count": 0,
            "best_score": None,
            "anchor_action": np.asarray(anchor_target, dtype=float).tolist(),
            "use_rule_anchor": self.use_rule_anchor,
            "use_handcrafted_candidates": self.use_handcrafted_candidates,
            "hard_safety_shield": self.hard_safety_shield,
            "shield_mode": self.shield_mode,
            "shield_lateral": self.shield_lateral,
            "shield_grass_lateral": self.shield_grass_lateral,
            "use_geometry_recovery": self.use_geometry_recovery,
            "recovery_enabled": self.recovery_enabled,
            "disabled_heads": sorted(self.disabled_heads),
            "world_model_mode": self.world_model_mode,
        }
        guard_trigger = self._needs_hard_recovery(obs[target_agent])
        if guard_trigger:
            self._infeasible_streak += 1
        else:
            self._infeasible_streak = 0
        escalated = bool(
            guard_trigger
            and self.shield_mode == "filter"
            and self.shield_escalation_steps > 0
            and self._infeasible_streak >= self.shield_escalation_steps
        )
        self.last_decision_debug["infeasible_streak"] = int(self._infeasible_streak)
        self.last_decision_debug["shield_escalated"] = escalated
        if (guard_trigger and self.shield_mode == "takeover") or (
            escalated and self.shield_escalation_bypass
        ):
            actions = background_actions.copy()
            actions[target_agent] = self._geometry_recovery_action(env, obs, target_agent, anchor_target)
            self.last_decision_debug.update(
                {
                    "hard_recovery": True,
                    "planner_bypassed": True,
                    "selected_action": np.asarray(actions[target_agent], dtype=float).tolist(),
                }
            )
            return actions.astype(np.float32)
        guard_action = None
        if guard_trigger and self.shield_mode == "filter":
            # The guard no longer replaces the controller; it injects its
            # recovery action into the candidate pool and scores the remaining
            # candidates by how far their rollout stays in an unsafe state.
            guard_action = self._geometry_recovery_action(env, obs, target_agent, anchor_target)
            self._guard_active = True
        # The quality proposal is a first-class member of the candidate set when
        # the quality planner is enabled; otherwise archived proposal-only
        # behaviour is preserved unchanged.
        head_targets = []
        if quality_actions is not None and self._quality_planner_enabled():
            head_targets.append(quality_actions[target_agent])
        if guard_action is not None:
            head_targets.append(guard_action)
        candidate_pool = self._candidate_pool(
            proposal_actions[target_agent],
            anchor_target,
            target_obs=obs[target_agent],
            extra_targets=[quality_actions[target_agent]] if quality_actions is not None else None,
            head_targets=head_targets or None,
        )

        best_action = candidate_pool[0]
        best_score = -np.inf
        candidate_records = []
        try:
            self._rollout_buffer = []
            scores = self._score_candidate_pool(obs, proposal_actions, background_policies, candidate_pool,
                                                target_agent, quality_actions=quality_actions)
            guard_violations = list(getattr(self, "_last_pool_violations", []))
            rollout_buffer = list(self._rollout_buffer)
        finally:
            self._guard_active = False
            self._rollout_buffer = []
        counterfactual_scores = None
        if self.decision_utility_compare_mode in {"full", "no_world_model"} and self.decision_utility_compare_mode != self.world_model_mode:
            original_mode = self.world_model_mode
            self.world_model_mode = self.decision_utility_compare_mode
            try:
                counterfactual_scores = self._score_candidate_pool(
                    obs, proposal_actions, background_policies, candidate_pool,
                    target_agent, quality_actions=quality_actions)
            finally:
                self.world_model_mode = original_mode
        best_index = 0
        escalation_allowed = None
        if escalated:
            # Escalation keeps the planner in the loop: only candidates whose
            # imagined rollout never enters the guarded state stay eligible.
            escalation_allowed = escalation_feasible_indices(
                guard_violations,
                allow_best=self.escalation_fallback == "best_available",
            )
            self.last_decision_debug["escalation_fallback"] = self.escalation_fallback
            if not escalation_allowed:
                forced = self._geometry_recovery_action(env, obs, target_agent, anchor_target)
                actions = background_actions.copy()
                actions[target_agent] = forced
                self.last_decision_debug.update(
                    {
                        "hard_recovery": True,
                        "planner_bypassed": False,
                        "escalation_pool_feasible": False,
                        "guard_candidate_violations": guard_violations,
                        "selected_action": np.asarray(forced, dtype=float).tolist(),
                    }
                )
                return actions.astype(np.float32)
        for index, (candidate, score) in enumerate(zip(candidate_pool, scores)):
            record = {'action': np.asarray(candidate, dtype=float).tolist(), 'score': float(score)}
            pool_terms = getattr(self, '_last_pool_terms', None)
            if pool_terms is not None and index < len(pool_terms):
                record['terms'] = pool_terms[index]
            candidate_records.append(record)
            if escalation_allowed is not None and index not in escalation_allowed:
                continue
            if score > best_score:
                best_score = score
                best_action = candidate
                best_index = index

        actions = background_actions.copy()
        actions[target_agent] = best_action
        self.last_decision_debug.update(
            {
                "candidate_count": int(len(candidate_pool)),
                "candidate_scores": candidate_records,
                "best_score": float(best_score),
                "guard_trigger": bool(guard_trigger),
                "hard_recovery": bool(guard_trigger),
                "planner_bypassed": False,
                "guard_action": None if guard_action is None else np.asarray(guard_action, dtype=float).tolist(),
                "guard_candidate_violations": guard_violations,
                "escalation_pool_feasible": None if escalation_allowed is None else True,
                "selected_action": np.asarray(best_action, dtype=float).tolist(),
            }
        )
        if self.dump_rollouts and best_index < len(rollout_buffer):
            # Imagined state sequence [s0 .. sH] of the selected candidate, with
            # [x, y, speed] per agent, for predicted-versus-realised figures.
            self.last_decision_debug["imagined_rollout"] = rollout_buffer[best_index]
        if counterfactual_scores is not None:
            self.last_decision_debug["counterfactual_world_model_mode"] = self.decision_utility_compare_mode
            self.last_decision_debug["counterfactual_candidate_scores"] = [
                {"action": np.asarray(candidate, dtype=float).tolist(), "score": float(score)}
                for candidate, score in zip(candidate_pool, counterfactual_scores)
            ]
        return actions.astype(np.float32)
