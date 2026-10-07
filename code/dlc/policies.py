import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from dlc.state_models import StateModelBundle
from dlc.observation_layout import rule_observation, require_checkpoint_version

PLAYFIELD = 2000 / 6.0
TRACK_WIDTH = 40 / 6.0

try:
    import torch
    from dlc.torch_models import TorchDLCBundle
except ImportError:
    torch = None
    TorchDLCBundle = None


def wrap_to_pi(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


class Policy(Protocol):
    name: str

    def reset(self):
        ...

    def act(self, env, obs):
        ...


@dataclass
class RandomPolicy:
    seed: int = 0
    name: str = "random"

    def __post_init__(self):
        self.rng = np.random.default_rng(self.seed)

    def reset(self):
        pass

    def act(self, env, obs):
        num_agents = env.unwrapped.num_agents
        return np.column_stack(
            [
                self.rng.uniform(-1.0, 1.0, size=num_agents),
                self.rng.uniform(0.0, 1.0, size=num_agents),
                self.rng.uniform(0.0, 1.0, size=num_agents),
            ]
        ).astype(np.float32)


@dataclass
class TrackFollowPolicy:
    lookahead: int = 6
    target_speed: float = 18.0
    lateral_gain: float = 0.9
    heading_gain: float = 1.35
    name: str = "track_follow"

    def reset(self):
        pass

    def act(self, env, obs):
        base_env = env.unwrapped
        action = np.zeros((base_env.num_agents, 3), dtype=np.float32)
        track_xy = np.array(base_env.track)[:, 2:]

        for agent_id, car in enumerate(base_env.cars):
            car_pos = np.array(car.hull.position).reshape((1, 2))
            track_index = int(np.argmin(np.linalg.norm(car_pos - track_xy, axis=1)))
            target_index = min(track_index + self.lookahead, len(base_env.track) - 1)
            corrected = getattr(base_env, 'telemetry_version', 'legacy_v1') == 'corrected_v2'
            if corrected:
                direction = -1 if base_env.episode_direction == 'CW' else 1
                target_index = (track_index + direction * self.lookahead) % len(base_env.track)
            desired_angle = base_env.track[target_index][1]
            if base_env.episode_direction == "CW":
                desired_angle += math.pi

            _, _, center_x, center_y = base_env.track[track_index]
            center_delta = np.asarray(car.hull.position, dtype=np.float32) - np.array(
                [center_x, center_y],
                dtype=np.float32,
            )
            normal = np.array([-math.sin(desired_angle), math.cos(desired_angle)])
            if corrected:
                # Existing correction is right-positive, unlike corrected telemetry.
                local_angle = float(base_env.track[track_index][1])
                if base_env.episode_direction == 'CW':
                    local_angle += math.pi
                normal = np.array([math.cos(local_angle), math.sin(local_angle)])
            lateral_error = float(np.dot(center_delta, normal))
            corrected_angle = desired_angle - self.lateral_gain * lateral_error / 40.0
            if corrected:
                # Right-positive displacement requires a left (positive-angle)
                # correction because physical forward is local +Y.
                corrected_angle = desired_angle + self.lateral_gain * lateral_error / 40.0

            angle_error = wrap_to_pi(corrected_angle - car.hull.angle)
            speed = np.linalg.norm(car.hull.linearVelocity)
            corner_slowdown = min(abs(angle_error) * 9.0, 7.0)
            lateral_slowdown = min(abs(lateral_error) / 3.5, 6.0)
            target_speed = max(12.0, self.target_speed - corner_slowdown - lateral_slowdown)

            action[agent_id, 0] = np.clip(-self.heading_gain * angle_error, -1.0, 1.0)
            action[agent_id, 1] = 0.55 if speed < target_speed else 0.08
            action[agent_id, 2] = 0.0 if speed < target_speed + 3.0 else 0.45

        return action


@dataclass
class OvertakeTrackPolicy:
    lookahead: int = 6
    target_speed: float = 19.0
    pass_speed: float = 24.0
    lane_offset: float = 8.0
    lateral_gain: float = 1.1
    name: str = "overtake_track"

    def reset(self):
        pass

    def act(self, env, obs):
        base_env = env.unwrapped
        action = np.zeros((base_env.num_agents, 3), dtype=np.float32)
        track = np.asarray(base_env.track, dtype=np.float32)
        track_xy = track[:, 2:]

        car_positions = [
            np.asarray(car.hull.position, dtype=np.float32)
            for car in base_env.cars
        ]

        for agent_id, car in enumerate(base_env.cars):
            car_pos = car_positions[agent_id]
            distance_to_track = np.linalg.norm(car_pos.reshape(1, 2) - track_xy, axis=1)
            track_index = int(np.argmin(distance_to_track))
            target_index = (track_index + self.lookahead) % len(base_env.track)
            desired_angle = float(base_env.track[target_index][1])
            local_angle = float(base_env.track[track_index][1])
            if base_env.episode_direction == "CW":
                desired_angle += math.pi
                local_angle += math.pi

            normal = np.array([-math.sin(local_angle), math.cos(local_angle)], dtype=np.float32)
            center = np.array(base_env.track[track_index][2:], dtype=np.float32)
            center_delta = car_pos - center
            lateral_error = float(np.dot(center_delta, normal))

            target_offset = 0.0
            speed_target = self.target_speed
            for other_id, other_pos in enumerate(car_positions):
                if other_id == agent_id:
                    continue
                rel = other_pos - car_pos
                forward_vec = np.array([math.cos(local_angle), math.sin(local_angle)], dtype=np.float32)
                other_forward = float(np.dot(rel, forward_vec))
                other_lateral = float(np.dot(other_pos - center, normal))
                close_ahead = 0.0 < other_forward < 45.0 and abs(other_lateral - lateral_error) < 18.0
                alongside = abs(other_forward) <= 15.0 and abs(other_lateral - lateral_error) < 20.0
                if close_ahead or alongside:
                    pass_side = -1.0 if other_lateral >= 0.0 else 1.0
                    target_offset = pass_side * self.lane_offset
                    speed_target = self.pass_speed
                    break

            target_offset = float(np.clip(target_offset, -0.45 * 40.0, 0.45 * 40.0))
            corrected_angle = desired_angle - self.lateral_gain * (lateral_error - target_offset) / 40.0
            angle_error = wrap_to_pi(corrected_angle - car.hull.angle)
            speed = np.linalg.norm(car.hull.linearVelocity)
            corner_slowdown = min(abs(angle_error) * 8.0, 7.0)
            lateral_slowdown = min(abs(lateral_error - target_offset) / 4.0, 6.0)
            speed_target = max(13.0, speed_target - corner_slowdown - lateral_slowdown)

            action[agent_id, 0] = np.clip(-1.45 * angle_error, -1.0, 1.0)
            action[agent_id, 1] = 0.62 if speed < speed_target else 0.08
            action[agent_id, 2] = 0.0 if speed < speed_target + 3.0 else 0.45

        return action


@dataclass
class TelemetryLanePolicy:
    target_speed: float = 20.0
    lane_offset: float = 0.0
    heading_gain: float = 1.6
    lateral_gain: float = 0.4
    gas: float = 0.65
    brake: float = 0.35
    min_speed: float = 5.0
    name: str = "telemetry_lane"

    def reset(self):
        pass

    def _target_lane_offset(self, agent_id, obs):
        del agent_id, obs
        return self.lane_offset

    def _target_speed(self, agent_id, obs):
        del agent_id, obs
        return self.target_speed

    def act(self, env, obs):
        obs = rule_observation(env, obs)
        del env
        obs_array = np.asarray(obs, dtype=np.float32)
        action = np.zeros((obs_array.shape[0], 3), dtype=np.float32)

        for agent_id in range(obs_array.shape[0]):
            heading_error = math.atan2(
                float(obs_array[agent_id, 13]),
                float(obs_array[agent_id, 14]),
            )
            lane_error = float(obs_array[agent_id, 12]) - (
                self._target_lane_offset(agent_id, obs_array) / TRACK_WIDTH
            )
            speed = float(obs_array[agent_id, 4]) * 50.0

            steer = -(self.heading_gain * heading_error + self.lateral_gain * lane_error)
            target_speed = max(
                self.min_speed,
                self._target_speed(agent_id, obs_array)
                - min(abs(heading_error) * 5.0, 4.0)
                - min(abs(lane_error) * 1.2, 3.0),
            )

            action[agent_id, 0] = np.clip(steer, -1.0, 1.0)
            action[agent_id, 1] = self.gas if speed < target_speed else 0.03
            action[agent_id, 2] = 0.0 if speed < target_speed + 2.0 else self.brake

        return action


@dataclass
class TelemetryOvertakePolicy(TelemetryLanePolicy):
    pass_speed: float = 23.0
    pass_lane_offset: float = 2.4
    trigger_distance: float = 45.0
    trigger_lateral: float = 12.0
    name: str = "telemetry_overtake"

    def _target_lane_offset(self, agent_id, obs):
        target_offset = self.lane_offset
        feature_start = 17
        feature_width = 7
        for start in range(feature_start, obs.shape[1], feature_width):
            rel_forward = float(obs[agent_id, start]) * PLAYFIELD
            rel_left = float(obs[agent_id, start + 1]) * PLAYFIELD
            close_ahead = (
                0.0 < rel_forward < self.trigger_distance
                and abs(rel_left) < self.trigger_lateral
            )
            alongside = (
                abs(rel_forward) <= 14.0
                and abs(rel_left) < self.trigger_lateral
            )
            if close_ahead or alongside:
                pass_side = -1.0 if rel_left >= 0.0 else 1.0
                target_offset = pass_side * self.pass_lane_offset
                break
        return target_offset

    def _target_speed(self, agent_id, obs):
        lane_offset = self._target_lane_offset(agent_id, obs)
        return self.pass_speed if lane_offset != self.lane_offset else self.target_speed


@dataclass
class TelemetryAdaptiveGatePolicy(TelemetryLanePolicy):
    pass_speed: float = 23.0
    pass_lane_offset: float = 2.4
    trigger_distance: float = 45.0
    trigger_lateral: float = 12.0
    recovery_lateral: float = 0.65
    recovery_heading_cos: float = 0.35
    recovery_hold: int = 24
    pass_hold: int = 18
    clear_hold: int = 12
    name: str = "telemetry_adaptive"

    def reset(self):
        self.mode = None
        self.hold = None

    def _init_state(self, num_agents):
        if self.mode is None or len(self.mode) != num_agents:
            self.mode = ["lane"] * num_agents
            self.hold = [0] * num_agents

    def _close_traffic(self, agent_id, obs):
        for start in range(17, obs.shape[1], 7):
            rel_forward = float(obs[agent_id, start]) * PLAYFIELD
            rel_left = float(obs[agent_id, start + 1]) * PLAYFIELD
            close_ahead = (
                0.0 < rel_forward < self.trigger_distance
                and abs(rel_left) < self.trigger_lateral
            )
            alongside = (
                abs(rel_forward) <= 14.0
                and abs(rel_left) < self.trigger_lateral
            )
            if close_ahead or alongside:
                return rel_left
        return None

    def act(self, env, obs):
        obs = rule_observation(env, obs)
        del env
        obs_array = np.asarray(obs, dtype=np.float32)
        self._init_state(obs_array.shape[0])
        action = np.zeros((obs_array.shape[0], 3), dtype=np.float32)

        for agent_id in range(obs_array.shape[0]):
            heading_error = math.atan2(
                float(obs_array[agent_id, 13]),
                float(obs_array[agent_id, 14]),
            )
            lane_error_raw = float(obs_array[agent_id, 12])
            heading_cos = float(obs_array[agent_id, 14])
            speed = float(obs_array[agent_id, 4]) * 50.0
            on_grass = float(obs_array[agent_id, 15]) > 0.5
            backward = float(obs_array[agent_id, 16]) > 0.5
            rel_left = self._close_traffic(agent_id, obs_array)
            recovery = (
                abs(lane_error_raw) > self.recovery_lateral
                or heading_cos < self.recovery_heading_cos
                or on_grass
                or backward
            )

            if recovery:
                self.mode[agent_id] = "lane"
                self.hold[agent_id] = self.recovery_hold
            elif rel_left is not None:
                self.mode[agent_id] = "overtake"
                self.hold[agent_id] = self.pass_hold
            elif self.hold[agent_id] > 0:
                self.hold[agent_id] -= 1
            else:
                self.mode[agent_id] = "lane"

            if (
                self.mode[agent_id] == "overtake"
                and rel_left is None
                and self.hold[agent_id] <= self.clear_hold
            ):
                self.mode[agent_id] = "lane"

            target_offset = self.lane_offset
            target_speed = self.target_speed
            if self.mode[agent_id] == "overtake":
                pass_side = -1.0 if (rel_left is not None and rel_left >= 0.0) else 1.0
                target_offset = pass_side * self.pass_lane_offset
                target_speed = self.pass_speed

            lane_error = lane_error_raw - (target_offset / TRACK_WIDTH)
            steer = -(self.heading_gain * heading_error + self.lateral_gain * lane_error)
            target_speed = max(
                self.min_speed,
                target_speed
                - min(abs(heading_error) * 5.0, 4.0)
                - min(abs(lane_error) * 1.2, 3.0),
            )

            action[agent_id, 0] = np.clip(steer, -1.0, 1.0)
            action[agent_id, 1] = self.gas if speed < target_speed else 0.03
            action[agent_id, 2] = 0.0 if speed < target_speed + 2.0 else self.brake

        return action


@dataclass
class TelemetryRecoveryAdaptivePolicy(TelemetryAdaptiveGatePolicy):
    pass_lane_offset: float = 1.6
    trigger_distance: float = 34.0
    trigger_lateral: float = 9.0
    recovery_lateral: float = 0.42
    recovery_heading_cos: float = 0.55
    recovery_hold: int = 54
    pass_hold: int = 10
    clear_hold: int = 6
    lateral_gain: float = 0.52
    gas: float = 0.58
    brake: float = 0.42
    name: str = "telemetry_adaptive_recovery"


@dataclass
class TelemetryConservativeAdaptivePolicy(TelemetryAdaptiveGatePolicy):
    pass_lane_offset: float = 0.8
    trigger_distance: float = 30.0
    trigger_lateral: float = 8.0
    recovery_lateral: float = 0.38
    recovery_heading_cos: float = 0.58
    recovery_hold: int = 48
    pass_hold: int = 8
    clear_hold: int = 5
    target_speed: float = 15.0
    pass_speed: float = 18.0
    lateral_gain: float = 0.50
    gas: float = 0.50
    brake: float = 0.50
    name: str = "telemetry_adaptive_conservative"


class TelemetryExpertGatePolicy:
    def __init__(
        self,
        lane_policy=None,
        overtake_policy=None,
        adaptive_policy=None,
        recovery_lateral=0.48,
        recovery_heading_cos=0.52,
        grass_recovery_hold=40,
        overtake_lateral_limit=0.42,
        name="telemetry_expert_gate",
    ):
        self.lane_policy = lane_policy or TelemetryLanePolicy(
            target_speed=21.0,
            lane_offset=0.0,
            heading_gain=1.7,
            lateral_gain=0.52,
            gas=0.58,
            brake=0.42,
            name="expert_gate_lane",
        )
        self.overtake_policy = overtake_policy or TelemetryOvertakePolicy(
            target_speed=22.0,
            pass_speed=26.0,
            pass_lane_offset=2.4,
            name="expert_gate_overtake",
        )
        self.adaptive_policy = adaptive_policy or TelemetryAdaptiveGatePolicy(
            target_speed=22.0,
            pass_speed=25.0,
            pass_lane_offset=1.6,
            recovery_lateral=0.55,
            recovery_heading_cos=0.45,
            name="expert_gate_adaptive",
        )
        self.recovery_lateral = float(recovery_lateral)
        self.recovery_heading_cos = float(recovery_heading_cos)
        self.grass_recovery_hold = int(grass_recovery_hold)
        self.overtake_lateral_limit = float(overtake_lateral_limit)
        self.recovery_hold = None
        self.name = name

    def reset(self):
        self.lane_policy.reset()
        self.overtake_policy.reset()
        self.adaptive_policy.reset()
        self.recovery_hold = None

    def _init_state(self, num_agents):
        if self.recovery_hold is None or len(self.recovery_hold) != num_agents:
            self.recovery_hold = [0] * num_agents

    def _has_close_traffic(self, agent_id, obs):
        for start in range(17, obs.shape[1], 7):
            rel_forward = float(obs[agent_id, start]) * PLAYFIELD
            rel_left = float(obs[agent_id, start + 1]) * PLAYFIELD
            if 0.0 < rel_forward < 45.0 and abs(rel_left) < 12.0:
                return True
            if abs(rel_forward) <= 14.0 and abs(rel_left) < 12.0:
                return True
        return False

    def act(self, env, obs):
        obs_array = np.asarray(obs, dtype=np.float32)
        self._init_state(obs_array.shape[0])
        lane = self.lane_policy.act(env, obs_array)
        overtake = self.overtake_policy.act(env, obs_array)
        adaptive = self.adaptive_policy.act(env, obs_array)
        action = np.zeros_like(lane)

        for agent_id in range(obs_array.shape[0]):
            lateral = abs(float(obs_array[agent_id, 12]))
            heading_cos = float(obs_array[agent_id, 14])
            on_grass = float(obs_array[agent_id, 15]) > 0.5
            backward = float(obs_array[agent_id, 16]) > 0.5
            recovery = (
                lateral > self.recovery_lateral
                or heading_cos < self.recovery_heading_cos
                or on_grass
                or backward
            )
            if recovery:
                self.recovery_hold[agent_id] = self.grass_recovery_hold
            elif self.recovery_hold[agent_id] > 0:
                self.recovery_hold[agent_id] -= 1

            close_traffic = self._has_close_traffic(agent_id, rule_observation(env, obs_array))
            if self.recovery_hold[agent_id] > 0:
                action[agent_id] = lane[agent_id]
                if on_grass and heading_cos > 0.25:
                    action[agent_id, 1] = max(action[agent_id, 1], 0.45)
                    action[agent_id, 2] = min(action[agent_id, 2], 0.05)
            elif close_traffic and lateral < self.overtake_lateral_limit:
                action[agent_id] = overtake[agent_id]
            else:
                action[agent_id] = adaptive[agent_id]

        action[:, 0] = np.clip(action[:, 0], -1.0, 1.0)
        action[:, 1:] = np.clip(action[:, 1:], 0.0, 1.0)
        return action.astype(np.float32)


class TelemetryFastExpertGatePolicy(TelemetryExpertGatePolicy):
    def __init__(self, name="telemetry_expert_fast"):
        super().__init__(
            lane_policy=TelemetryLanePolicy(
                target_speed=23.5,
                lane_offset=0.0,
                heading_gain=1.72,
                lateral_gain=0.50,
                gas=0.66,
                brake=0.36,
                name="fast_expert_lane",
            ),
            overtake_policy=TelemetryOvertakePolicy(
                target_speed=23.0,
                pass_speed=27.0,
                pass_lane_offset=2.1,
                trigger_distance=42.0,
                trigger_lateral=11.0,
                heading_gain=1.65,
                lateral_gain=0.44,
                gas=0.68,
                brake=0.34,
                name="fast_expert_overtake",
            ),
            adaptive_policy=TelemetryAdaptiveGatePolicy(
                target_speed=23.0,
                pass_speed=26.0,
                pass_lane_offset=1.35,
                trigger_distance=38.0,
                trigger_lateral=10.0,
                recovery_lateral=0.48,
                recovery_heading_cos=0.50,
                recovery_hold=34,
                pass_hold=12,
                clear_hold=6,
                heading_gain=1.68,
                lateral_gain=0.50,
                gas=0.64,
                brake=0.36,
                name="fast_expert_adaptive",
            ),
            recovery_lateral=0.42,
            recovery_heading_cos=0.56,
            grass_recovery_hold=34,
            overtake_lateral_limit=0.38,
            name=name,
        )


class TelemetryBarrierExpertGatePolicy(TelemetryExpertGatePolicy):
    def __init__(self, name="telemetry_expert_barrier"):
        super().__init__(
            lane_policy=TelemetryLanePolicy(
                target_speed=21.5,
                lane_offset=0.0,
                heading_gain=1.78,
                lateral_gain=0.56,
                gas=0.60,
                brake=0.40,
                name="barrier_expert_lane",
            ),
            overtake_policy=TelemetryOvertakePolicy(
                target_speed=21.5,
                pass_speed=25.0,
                pass_lane_offset=2.0,
                trigger_distance=40.0,
                trigger_lateral=11.5,
                heading_gain=1.70,
                lateral_gain=0.48,
                gas=0.64,
                brake=0.36,
                name="barrier_expert_overtake",
            ),
            adaptive_policy=TelemetryAdaptiveGatePolicy(
                target_speed=21.5,
                pass_speed=24.0,
                pass_lane_offset=1.45,
                trigger_distance=38.0,
                trigger_lateral=10.5,
                recovery_lateral=0.52,
                recovery_heading_cos=0.48,
                recovery_hold=30,
                pass_hold=14,
                clear_hold=8,
                heading_gain=1.72,
                lateral_gain=0.52,
                gas=0.60,
                brake=0.40,
                name="barrier_expert_adaptive",
            ),
            recovery_lateral=0.44,
            recovery_heading_cos=0.57,
            grass_recovery_hold=42,
            overtake_lateral_limit=0.36,
            name=name,
        )
        self.density_radius = 42.0
        self.density_speed_penalty = 2.4
        self.density_pass_penalty = 1.2
        self.density_hold = 14
        self.barrier_lateral = 0.34
        self.barrier_heading_cos = 0.60
        self.barrier_min_speed = 4.5
        self.lane_offset = 0.0
        self.target_speed = 21.5
        self.pass_speed = 25.0
        self.pass_lane_offset = 2.0
        self.heading_gain = 1.78
        self.lateral_gain = 0.56
        self.gas = 0.60
        self.brake = 0.40
        self.min_speed = 4.5
        self.pass_hold = 14
        self.clear_hold = 8

    def reset(self):
        self.lane_policy.reset()
        self.overtake_policy.reset()
        self.adaptive_policy.reset()
        self.mode = None
        self.hold = None

    def _init_state(self, num_agents):
        if self.mode is None or len(self.mode) != num_agents:
            self.mode = ["lane"] * num_agents
            self.hold = [0] * num_agents

    def _traffic_density(self, agent_id, obs):
        count = 0
        nearest_forward = None
        nearest_lateral = None
        for start in range(17, obs.shape[1], 7):
            rel_forward = float(obs[agent_id, start]) * PLAYFIELD
            rel_left = float(obs[agent_id, start + 1]) * PLAYFIELD
            if abs(rel_forward) <= self.density_radius and abs(rel_left) < 18.0:
                count += 1
            if 0.0 < rel_forward < self.density_radius and abs(rel_left) < 12.0:
                if nearest_forward is None or rel_forward < nearest_forward:
                    nearest_forward = rel_forward
                    nearest_lateral = rel_left
        return count, nearest_forward, nearest_lateral

    def act(self, env, obs):
        obs = rule_observation(env, obs)
        del env
        obs_array = np.asarray(obs, dtype=np.float32)
        self._init_state(obs_array.shape[0])
        action = np.zeros((obs_array.shape[0], 3), dtype=np.float32)

        for agent_id in range(obs_array.shape[0]):
            heading_error = math.atan2(
                float(obs_array[agent_id, 13]),
                float(obs_array[agent_id, 14]),
            )
            lane_error_raw = float(obs_array[agent_id, 12])
            heading_cos = float(obs_array[agent_id, 14])
            speed = float(obs_array[agent_id, 4]) * 50.0
            on_grass = float(obs_array[agent_id, 15]) > 0.5
            backward = float(obs_array[agent_id, 16]) > 0.5
            density, rel_forward, rel_left = self._traffic_density(agent_id, obs_array)
            recovery = (
                abs(lane_error_raw) > self.recovery_lateral
                or heading_cos < self.recovery_heading_cos
                or on_grass
                or backward
            )

            if recovery:
                self.mode[agent_id] = "lane"
                self.hold[agent_id] = max(self.grass_recovery_hold, self.density_hold)
            elif rel_forward is not None:
                self.mode[agent_id] = "overtake"
                self.hold[agent_id] = self.pass_hold
            elif density >= 2:
                self.mode[agent_id] = "adaptive"
                self.hold[agent_id] = self.density_hold
            elif self.hold[agent_id] > 0:
                self.hold[agent_id] -= 1
            else:
                self.mode[agent_id] = "lane"

            if (
                self.mode[agent_id] == "overtake"
                and rel_forward is None
                and self.hold[agent_id] <= self.clear_hold
            ):
                self.mode[agent_id] = "lane"

            target_offset = self.lane_offset
            target_speed = self.target_speed
            if self.mode[agent_id] == "overtake":
                pass_side = -1.0 if (rel_left is not None and rel_left >= 0.0) else 1.0
                target_offset = pass_side * self.pass_lane_offset
                target_speed = self.pass_speed - self.density_pass_penalty
            elif self.mode[agent_id] == "adaptive" and density >= 2:
                target_speed = self.target_speed - self.density_speed_penalty * min(density, 4)
            elif density >= 1:
                target_speed = self.target_speed - self.density_speed_penalty * min(density, 3)

            lane_error = lane_error_raw - (target_offset / TRACK_WIDTH)
            steer = -(self.heading_gain * heading_error + self.lateral_gain * lane_error)
            target_speed = max(
                self.barrier_min_speed,
                target_speed
                - min(abs(heading_error) * 5.0, 4.0)
                - min(abs(lane_error) * 1.2, 3.0),
            )
            if abs(lane_error_raw) > self.barrier_lateral or heading_cos < self.barrier_heading_cos:
                steer = np.clip(-1.9 * heading_error - 0.95 * lane_error, -1.0, 1.0)
                target_speed = min(target_speed, self.target_speed - 4.0)

            action[agent_id, 0] = np.clip(steer, -1.0, 1.0)
            action[agent_id, 1] = self.gas if speed < target_speed else 0.03
            action[agent_id, 2] = 0.0 if speed < target_speed + 2.0 else self.brake

        return action.astype(np.float32)


class TelemetryRecoveryExpertGatePolicy(TelemetryBarrierExpertGatePolicy):
    def __init__(self, name="telemetry_expert_recovery"):
        super().__init__(name=name)
        self.density_radius = 36.0
        self.density_speed_penalty = 3.0
        self.density_pass_penalty = 2.0
        self.density_hold = 24
        self.barrier_lateral = 0.24
        self.barrier_heading_cos = 0.72
        self.barrier_min_speed = 3.5
        self.target_speed = 18.5
        self.pass_speed = 21.0
        self.pass_lane_offset = 1.0
        self.heading_gain = 1.95
        self.lateral_gain = 0.78
        self.gas = 0.48
        self.brake = 0.55
        self.pass_hold = 8
        self.clear_hold = 5
        self.grass_recovery_hold = 72
        self.recovery_lateral = 0.30
        self.recovery_heading_cos = 0.70
        self.overtake_lateral_limit = 0.24


@dataclass
class TelemetryYieldPolicy(TelemetryLanePolicy):
    yield_distance: float = 28.0
    yield_lateral: float = 10.0
    yield_speed: float = 11.0
    name: str = "telemetry_yield"

    def _target_speed(self, agent_id, obs):
        for start in range(17, obs.shape[1], 7):
            rel_forward = float(obs[agent_id, start]) * PLAYFIELD
            rel_left = float(obs[agent_id, start + 1]) * PLAYFIELD
            car_behind = (
                -self.yield_distance < rel_forward < 0.0
                and abs(rel_left) < self.yield_lateral
            )
            if car_behind:
                return min(self.target_speed, self.yield_speed)
        return self.target_speed


@dataclass
class TelemetryCruisePolicy(TelemetryLanePolicy):
    heading_gain: float = 1.25
    lateral_gain: float = 0.28
    gas: float = 0.46
    brake: float = 0.45
    name: str = "telemetry_cruise"


class MixedPolicy:
    def __init__(self, policies):
        self.policies = policies
        self.name = "_vs_".join(policy.name for policy in policies)

    def reset(self):
        for policy in self.policies:
            policy.reset()

    def act(self, env, obs):
        actions = []
        for agent_id, policy in enumerate(self.policies):
            if hasattr(policy, "set_controlled_agent"):
                policy.set_controlled_agent(agent_id)
            policy_action = policy.act(env, obs)
            actions.append(policy_action[agent_id])
        return np.asarray(actions, dtype=np.float32)


class SafeTrackBlendPolicy:
    def __init__(
        self,
        learned_policy,
        base_policy=None,
        base_policy_name="overtake_track",
        blend=0.35,
        unsafe_blend=0.85,
        lateral_threshold=1.2,
        heading_cos_threshold=0.1,
    ):
        self.learned_policy = learned_policy
        if base_policy is None:
            if base_policy_name == "track_follow":
                base_policy = TrackFollowPolicy()
            elif base_policy_name == "overtake_track":
                base_policy = OvertakeTrackPolicy()
            elif base_policy_name == "telemetry_lane":
                base_policy = TelemetryLanePolicy()
            elif base_policy_name == "telemetry_overtake":
                base_policy = TelemetryOvertakePolicy()
            elif base_policy_name == "telemetry_yield":
                base_policy = TelemetryYieldPolicy()
            elif base_policy_name == "telemetry_cruise":
                base_policy = TelemetryCruisePolicy()
            elif base_policy_name == "stable_lane":
                base_policy = TelemetryLanePolicy(name="stable_lane")
            else:
                raise ValueError(f"unknown safe base policy: {base_policy_name}")
        self.base_policy = base_policy
        self.blend = float(blend)
        self.unsafe_blend = float(unsafe_blend)
        self.lateral_threshold = float(lateral_threshold)
        self.heading_cos_threshold = float(heading_cos_threshold)
        self.controlled_agent = 0
        self.name = f"safe_{learned_policy.name}"

    def reset(self):
        self.learned_policy.reset()
        self.base_policy.reset()

    def set_controlled_agent(self, agent_id):
        self.controlled_agent = int(agent_id)
        if hasattr(self.learned_policy, "set_controlled_agent"):
            self.learned_policy.set_controlled_agent(agent_id)

    def act(self, env, obs):
        learned = self.learned_policy.act(env, obs)
        base = self.base_policy.act(env, obs)
        blend = np.full((env.unwrapped.num_agents, 1), self.blend, dtype=np.float32)

        obs_array = np.asarray(obs, dtype=np.float32)
        if obs_array.ndim == 2 and obs_array.shape[1] >= 17:
            lateral = np.abs(obs_array[:, 12])
            heading_cos = obs_array[:, 14]
            on_grass = obs_array[:, 15] > 0.5
            backward = obs_array[:, 16] > 0.5
            unsafe = (
                (lateral > self.lateral_threshold)
                | (heading_cos < self.heading_cos_threshold)
                | on_grass
                | backward
            )
            blend[unsafe, 0] = self.unsafe_blend

        action = blend * base + (1.0 - blend) * learned
        action[:, 0] = np.clip(action[:, 0], -1.0, 1.0)
        action[:, 1] = np.clip(action[:, 1], 0.0, 1.0)
        action[:, 2] = np.clip(action[:, 2], 0.0, 1.0)
        return action.astype(np.float32)


class ModelPlannerPolicy:
    def __init__(self, model_path, seed=0, horizon=5, candidates=64):
        self.model_path = Path(model_path)
        self.model = StateModelBundle.load(self.model_path)
        self.rng = np.random.default_rng(seed)
        self.horizon = int(horizon)
        self.candidates = int(candidates)
        self.controlled_agent = 0
        self.name = self.model.model_type

    def reset(self):
        pass

    def set_controlled_agent(self, agent_id):
        self.controlled_agent = int(agent_id)

    def act(self, env, obs):
        del env
        obs = np.asarray(obs, dtype=np.float64)
        best_action = None
        best_score = -np.inf

        for _ in range(self.candidates):
            first_action = self._sample_action()
            imagined_obs = obs.copy()
            score = 0.0
            discount = 1.0
            for step in range(self.horizon):
                action = first_action if step == 0 else self._sample_action()
                imagined_obs, reward = self.model.predict(
                    imagined_obs,
                    action,
                    ego_agent=self.controlled_agent,
                )
                score += discount * float(reward[self.controlled_agent])
                discount *= 0.99

            if score > best_score:
                best_score = score
                best_action = first_action

        return np.asarray(best_action, dtype=np.float32)

    def _sample_action(self):
        steer = self.rng.uniform(-1.0, 1.0, size=self.model.num_agents)
        gas = self.rng.uniform(0.0, 1.0, size=self.model.num_agents)
        brake = self.rng.uniform(0.0, 0.4, size=self.model.num_agents)
        return np.column_stack([steer, gas, brake])


class TorchActorPolicy:
    def __init__(self, model_path, seed=0, device="cpu"):
        del seed
        if torch is None or TorchDLCBundle is None:
            raise ImportError("TorchActorPolicy requires torch to be installed")
        self.device = torch.device(device)
        self.bundle = TorchDLCBundle.load(model_path, map_location=self.device)
        self.bundle.actor.to(self.device)
        self.name = self.bundle.meta["model_type"]
        self.controlled_agent = None

    def reset(self):
        pass

    def set_controlled_agent(self, agent_id):
        self.controlled_agent = int(agent_id)

    def _legacy_opponent_features(self, obs_row):
        obs_row = np.asarray(obs_row, dtype=np.float32)
        ego_dim = 17
        opponent_dim = 7
        if obs_row.shape[0] == ego_dim + opponent_dim:
            return obs_row[ego_dim : ego_dim + opponent_dim]
        if obs_row.shape[0] > ego_dim and (obs_row.shape[0] - ego_dim) % (opponent_dim + 1) == 0:
            slots = []
            for start in range(ego_dim, obs_row.shape[0], opponent_dim + 1):
                features = obs_row[start : start + opponent_dim]
                mask = obs_row[start + opponent_dim]
                if mask > 0.5:
                    slots.append(features)
            if slots:
                return min(slots, key=lambda item: float(item[4]))
        if obs_row.shape[0] > ego_dim and (obs_row.shape[0] - ego_dim) % opponent_dim == 0:
            slots = [
                obs_row[start : start + opponent_dim]
                for start in range(ego_dim, obs_row.shape[0], opponent_dim)
            ]
            if slots:
                return min(slots, key=lambda item: float(item[4]))
        return np.zeros((opponent_dim,), dtype=np.float32)

    def _adapt_legacy_two_agent_obs(self, env, obs):
        obs = np.asarray(obs, dtype=np.float32)
        shape = np.asarray(self.bundle.obs_mean).shape
        if len(shape) == 2:
            expected_agents, expected_dim = int(shape[0]), int(shape[1])
        else:
            # Retrained checkpoints store one pooled row of normalisation
            # constants; the field size comes from the bundle metadata.
            expected_agents = int(self.bundle.meta.get("num_agents", 0)) or None
            expected_dim = int(shape[-1])
        if obs.shape == (expected_agents, expected_dim):
            return obs, None
        if expected_agents != 2 or expected_dim != 24 or obs.ndim != 2 or obs.shape[1] < 17:
            return obs, None
        agent_id = self.controlled_agent
        if agent_id is None:
            agent_id = min(obs.shape[0] - 1, 0)
        agent_id = int(np.clip(agent_id, 0, obs.shape[0] - 1))
        legacy_obs = np.zeros((2, 24), dtype=np.float32)
        legacy_obs[0, :17] = obs[agent_id, :17]
        legacy_obs[0, 17:24] = self._legacy_opponent_features(obs[agent_id])
        return legacy_obs, agent_id

    def act(self, env, obs):
        num_agents = env.unwrapped.num_agents
        if (getattr(env.unwrapped, 'telemetry_version', 'legacy_v1') == 'corrected_v2'
                and self.bundle.meta.get('telemetry_version', 'legacy_v1') == 'legacy_v1'
                and getattr(env.unwrapped, 'allow_legacy_checkpoint_migration', False)):
            # The archived two-agent checkpoints use the legacy right-positive
            # telemetry convention.  Convert only for this explicitly marked
            # exploratory migration; the physical simulator remains unchanged.
            obs = rule_observation(env, obs)
        require_checkpoint_version(env, self.bundle.meta)
        obs, legacy_target_agent = self._adapt_legacy_two_agent_obs(env, obs)
        normalized_obs = self.bundle.normalize_obs(obs)
        obs_tensor = torch.as_tensor(normalized_obs, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            action = self.bundle.actor(obs_tensor).cpu().numpy()
        if legacy_target_agent is not None:
            full_action = np.zeros((num_agents, 3), dtype=np.float32)
            full_action[legacy_target_agent] = np.asarray(action[0], dtype=np.float32)
            full_action[:, 0] = np.clip(full_action[:, 0], -1.0, 1.0)
            full_action[:, 1:] = np.clip(full_action[:, 1:], 0.0, 1.0)
            return full_action
        return np.asarray(action, dtype=np.float32)


class PackedActorPolicy:
    """Actor wrapper that repacks the observation before the network sees it.

    A checkpoint trained on the packed slot layout expects a fixed number of
    ranked relation slots, while the run may expose every vehicle whenever the
    neighbour budget is unbounded. Repacking applies the same selection and the
    same slot order that produced the training rows, so the actor is scored on
    the observation it was trained for; without it the network reads whichever
    vehicles happen to sit in the first slots.
    """

    def __init__(self, inner, max_neighbors=3, selection_mode="interaction",
                 telemetry_version="corrected_v2"):
        self.inner = inner
        self.name = getattr(inner, "name", "packed_actor")
        self.max_neighbors = int(max_neighbors)
        self.selection_mode = str(selection_mode)
        self.telemetry_version = str(telemetry_version)
        self.controlled_agent = None

    def reset(self):
        self.inner.reset()

    def set_controlled_agent(self, agent_id):
        self.controlled_agent = int(agent_id)
        if hasattr(self.inner, "set_controlled_agent"):
            self.inner.set_controlled_agent(agent_id)

    def expected_obs_dim(self):
        mean = getattr(getattr(self.inner, "bundle", None), "obs_mean", None)
        if mean is None:
            return None
        return int(np.asarray(mean).shape[-1])

    def act(self, env, obs):
        from dlc.graph_policy import pack_dynamic_neighbor_obs

        expected = self.expected_obs_dim()
        obs = np.asarray(obs, dtype=np.float32)
        if expected is not None and obs.shape[-1] != expected:
            obs = pack_dynamic_neighbor_obs(
                obs,
                target_obs_dim=expected,
                max_neighbors=self.max_neighbors,
                selection_mode=self.selection_mode,
                telemetry_version=self.telemetry_version,
            )
        return self.inner.act(env, obs)


class StableBaselinesActorPolicy:
    def __init__(self, model_path, seed=0, device="cpu"):
        del seed
        self.model_path = Path(model_path)
        meta_path = self.model_path.with_suffix(self.model_path.suffix + ".meta.json")
        if not meta_path.exists() and self.model_path.name.endswith(".sb3.zip"):
            meta_path = self.model_path.with_name(self.model_path.name.replace(".sb3.zip", ".meta.json"))
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        self.meta = meta
        algorithm = str(meta.get("algorithm", self.model_path.name.split("_", 1)[0])).lower()
        try:
            from stable_baselines3 import PPO, SAC, TD3
        except ImportError as exc:
            raise ImportError("StableBaselinesActorPolicy requires stable_baselines3 to be installed") from exc
        loaders = {"ppo": PPO, "sac": SAC, "td3": TD3}
        if algorithm not in loaders:
            raise ValueError(f"unknown stable-baselines3 algorithm: {algorithm}")
        self.model = loaders[algorithm].load(str(self.model_path), device=device)
        self.controlled_agent = int(meta.get("target_agent", -1))
        self.name = meta.get("name", self.model_path.stem)
        self.expected_obs_dim = int(self.model.observation_space.shape[0])

    def reset(self):
        pass

    def set_controlled_agent(self, agent_id):
        self.controlled_agent = int(agent_id)

    def _adapt_observation(self, env, obs):
        obs = np.asarray(obs, dtype=np.float32)
        migrated = False
        if (getattr(env.unwrapped, 'telemetry_version', 'legacy_v1') == 'corrected_v2'
                and self.meta.get('telemetry_version', 'legacy_v1') == 'legacy_v1'
                and getattr(env.unwrapped, 'allow_legacy_checkpoint_migration', False)):
            migrated = True
            obs = rule_observation(env, obs)
            expected_agents, expected_dim = obs.shape[0], self.expected_obs_dim
            if expected_dim == 24 and obs.shape[1] >= 24:
                packed = np.zeros((obs.shape[0], 24), dtype=np.float32)
                packed[:, :17] = obs[:, :17]
                for agent_id, row in enumerate(obs):
                    slots = row[17:].reshape(-1, 7)
                    if len(slots):
                        valid = slots[np.isfinite(slots).all(axis=1)]
                        if len(valid):
                            packed[agent_id, 17:24] = valid[np.argmin(valid[:, 0])]
                obs = packed
        # An agent trained with ``--pack-observation`` saw interaction-ranked
        # slots even when the field was small enough that every opponent fit the
        # budget, so the order was not the environment's own. The evaluator
        # exposes every vehicle and the loader used to pack only when the row
        # width differed from the checkpoint, which left those agents ranked by
        # identity at the fleet sizes whose width happens to match. The
        # checkpoint declares the packing it was trained with, so honour it
        # whenever it is declared; checkpoints that do not declare it keep the
        # previous behaviour bit for bit.
        runtime_packed = str(self.meta.get("observation_packing", "")).startswith(
            "runtime_interaction_packing"
        )
        if obs.ndim != 2:
            return obs
        if obs.shape[1] == self.expected_obs_dim and not runtime_packed:
            return obs
        if self.expected_obs_dim >= 17 and (
                obs.shape[1] > self.expected_obs_dim
                or (runtime_packed and obs.shape[1] == self.expected_obs_dim)):
            try:
                from dlc.graph_policy import pack_dynamic_neighbor_obs

                return pack_dynamic_neighbor_obs(
                    obs,
                    target_obs_dim=self.expected_obs_dim,
                    max_neighbors=int(self.meta.get("max_neighbors") or 0) or None,
                    selection_mode="interaction",
                    # A migrated observation is in legacy format and has to be
                    # ranked with the legacy rule; an observation the agent was
                    # trained on in the environment's own format is ranked with
                    # that format, so training and evaluation agree.
                    telemetry_version=('legacy_v1' if migrated
                                       else getattr(env.unwrapped, 'telemetry_version', 'legacy_v1')),
                )
            except Exception:
                return obs[:, : self.expected_obs_dim].copy()
        if obs.shape[1] < self.expected_obs_dim:
            adapted = np.zeros((obs.shape[0], self.expected_obs_dim), dtype=np.float32)
            adapted[:, : obs.shape[1]] = obs
            return adapted
        return obs

    def act(self, env, obs):
        require_checkpoint_version(env, self.meta)
        obs = self._adapt_observation(env, obs)
        num_agents = env.unwrapped.num_agents
        agent_id = self.controlled_agent
        if agent_id < 0:
            agent_id = max(num_agents - 1, 0)
        action, _ = self.model.predict(obs[agent_id], deterministic=True)
        actions = np.zeros((num_agents, 3), dtype=np.float32)
        actions[agent_id] = np.asarray(action, dtype=np.float32)
        actions[:, 0] = np.clip(actions[:, 0], -1.0, 1.0)
        actions[:, 1:] = np.clip(actions[:, 1:], 0.0, 1.0)
        return actions


def make_policy(
    name,
    seed=0,
    device="cpu",
    safe=False,
    safe_blend=0.35,
    unsafe_blend=0.85,
    safe_base_policy="overtake_track",
    neighbor_mode="fixed",
    max_neighbors=None,
    neighbor_selection_mode="legacy",
    reverse_slot_order=False,
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
    shield_mode=None,
    shield_lateral=None,
    shield_grass_lateral=None,
    shield_heading_cos=None,
    guard_penalty_weight=None,
    separation_scale=None,
    planner_liveness_weight=None,
    planner_liveness_speed=None,
    maneuver_hold_steps=None,
    corridor_feasibility=None,
    planner_progress_mode=None,
    corridor_selection=None,
    clearance_feasibility=None,
    shield_escalation_steps=None,
    shield_escalation_bypass=None,
    escalation_fallback=None,
    corridor_return_weight=None,
    corridor_return_candidates=None,
    corridor_return_gain=None,
    corridor_return_heading_gain=None,
    corridor_return_gate=None,
    corridor_recovery_cross_track=None,
    relevance_memory=None,
    maneuver_commit_steps=None,
    maneuver_commit_forward_m=None,
    maneuver_commit_lateral_m=None,
    maneuver_commit_release_m=None,
    clearance_alongside_length=None,
    clearance_lateral_min=None,
    dump_rollouts=False,
    use_rule_anchor=True,
    use_handcrafted_candidates=True,
    use_geometry_recovery=True,
    recovery_enabled=True,
    head_ablation=None,
    world_model_mode="full",
    decision_utility_compare_mode=None,
    pack_neighbors=None,
    ensemble_epistemic=True,
):
    def make_safe_base(base_name):
        if base_name == "track_follow":
            return TrackFollowPolicy()
        if base_name == "overtake_track":
            return OvertakeTrackPolicy()
        if base_name == "telemetry_lane":
            return TelemetryLanePolicy(target_speed=22.0)
        if base_name == "telemetry_overtake":
            return TelemetryOvertakePolicy()
        if base_name == "telemetry_adaptive":
            return TelemetryAdaptiveGatePolicy()
        if base_name == "telemetry_adaptive_recovery":
            return TelemetryRecoveryAdaptivePolicy()
        if base_name == "telemetry_adaptive_conservative":
            return TelemetryConservativeAdaptivePolicy()
        if base_name == "telemetry_expert_gate":
            return TelemetryExpertGatePolicy()
        if base_name == "telemetry_expert_fast":
            return TelemetryFastExpertGatePolicy()
        if base_name == "telemetry_expert_barrier":
            return TelemetryBarrierExpertGatePolicy()
        if base_name == "telemetry_expert_recovery":
            return TelemetryRecoveryExpertGatePolicy()
        if base_name == "telemetry_yield":
            return TelemetryYieldPolicy()
        if base_name == "telemetry_cruise":
            return TelemetryCruisePolicy()
        if base_name == "stable_lane":
            return TelemetryLanePolicy(name="stable_lane")
        raise ValueError(f"unknown safe base policy: {base_name}")

    if name == "random":
        policy = RandomPolicy(seed=seed)
        return policy
    if name == "track_follow":
        return TrackFollowPolicy()
    if name == "overtake_track":
        return OvertakeTrackPolicy()
    if name == "telemetry_lane":
        return TelemetryLanePolicy()
    if name == "telemetry_overtake":
        return TelemetryOvertakePolicy()
    if name == "telemetry_adaptive":
        return TelemetryAdaptiveGatePolicy()
    if name == "telemetry_adaptive_recovery":
        return TelemetryRecoveryAdaptivePolicy()
    if name == "telemetry_adaptive_conservative":
        return TelemetryConservativeAdaptivePolicy()
    if name == "telemetry_expert_gate":
        return TelemetryExpertGatePolicy()
    if name == "telemetry_expert_fast":
        return TelemetryFastExpertGatePolicy()
    if name == "telemetry_expert_barrier":
        return TelemetryBarrierExpertGatePolicy()
    if name == "telemetry_expert_recovery":
        return TelemetryRecoveryExpertGatePolicy()
    if name == "telemetry_yield":
        return TelemetryYieldPolicy()
    if name == "telemetry_cruise":
        return TelemetryCruisePolicy()
    if isinstance(name, (list, tuple)):
        name = list(name)
        if not name:
            raise ValueError("An ensemble policy needs at least one member")
        if not all(member.endswith(".graphworld.pt") for member in name):
            raise ValueError(f"Only .graphworld.pt checkpoints can be ensembled, got {name}")
    elif name.endswith(".npz"):
        policy = ModelPlannerPolicy(name, seed=seed)
        return (
            SafeTrackBlendPolicy(
                policy,
                blend=safe_blend,
                unsafe_blend=unsafe_blend,
                base_policy_name=safe_base_policy,
            )
            if safe
            else policy
        )
    if isinstance(name, (list, tuple)) or name.endswith(".pt"):
        if isinstance(name, (list, tuple)) or name.endswith(".graphworld.pt"):
            from dlc.graph_world_model import GraphWorldModelPolicy

            policy = GraphWorldModelPolicy(
                name,
                device=device,
                neighbor_mode=neighbor_mode,
                max_neighbors=max_neighbors,
                neighbor_selection_mode=neighbor_selection_mode,
                reverse_slot_order=reverse_slot_order,
                planner_horizon=planner_horizon,
                planner_candidates=planner_candidates,
                planner_risk_weight=planner_risk_weight,
                planner_progress_weight=planner_progress_weight,
                planner_uncertainty_weight=planner_uncertainty_weight,
                planner_overtake_weight=planner_overtake_weight,
                planner_lane_weight=planner_lane_weight,
                planner_grass_weight=planner_grass_weight,
                planner_close_gap_weight=planner_close_gap_weight,
                overtake_aware_planner=overtake_aware_planner,
                quality_proposal_path=quality_proposal_path,
                quality_planner_mode=quality_planner_mode,
                quality_rollout_blend=quality_rollout_blend,
                quality_overtake_weight=quality_overtake_weight,
                quality_lane_weight=quality_lane_weight,
                quality_grass_weight=quality_grass_weight,
                quality_close_gap_weight=quality_close_gap_weight,
                learned_quality_weight=learned_quality_weight,
                learned_quality_gate=learned_quality_gate,
                learned_quality_min_on_track=learned_quality_min_on_track,
                learned_quality_max_grass=learned_quality_max_grass,
                learned_quality_max_lane_error=learned_quality_max_lane_error,
                learned_quality_gate_penalty=learned_quality_gate_penalty,
                elegance_barrier=elegance_barrier,
                elegance_barrier_weight=elegance_barrier_weight,
                elegance_lateral_limit=elegance_lateral_limit,
                elegance_heading_cos_min=elegance_heading_cos_min,
                elegance_grass_penalty=elegance_grass_penalty,
                elegance_backward_penalty=elegance_backward_penalty,
                elegance_close_gap_limit=elegance_close_gap_limit,
                geometry_generalization=geometry_generalization,
                geometry_curvature_lookahead=geometry_curvature_lookahead,
                geometry_curvature_speed_weight=geometry_curvature_speed_weight,
                geometry_lateral_speed_weight=geometry_lateral_speed_weight,
                geometry_heading_speed_weight=geometry_heading_speed_weight,
                geometry_min_speed=geometry_min_speed,
                geometry_anchor_blend=geometry_anchor_blend,
                geometry_barrier_weight=geometry_barrier_weight,
                hard_safety_shield=hard_safety_shield,
                shield_mode=shield_mode,
                shield_lateral=shield_lateral,
                shield_grass_lateral=shield_grass_lateral,
                shield_heading_cos=shield_heading_cos,
                guard_penalty_weight=guard_penalty_weight,
                separation_scale=separation_scale,
                planner_liveness_weight=planner_liveness_weight,
                planner_liveness_speed=planner_liveness_speed,
                maneuver_hold_steps=maneuver_hold_steps,
                corridor_feasibility=corridor_feasibility,
                planner_progress_mode=planner_progress_mode,
                corridor_selection=corridor_selection,
                clearance_feasibility=clearance_feasibility,
                shield_escalation_steps=shield_escalation_steps,
                shield_escalation_bypass=shield_escalation_bypass,
                escalation_fallback=escalation_fallback,
                corridor_return_weight=corridor_return_weight,
                corridor_return_candidates=corridor_return_candidates,
                corridor_return_gain=corridor_return_gain,
                corridor_return_heading_gain=corridor_return_heading_gain,
                corridor_return_gate=corridor_return_gate,
                corridor_recovery_cross_track=corridor_recovery_cross_track,
                relevance_memory=relevance_memory,
                maneuver_commit_steps=maneuver_commit_steps,
                maneuver_commit_forward_m=maneuver_commit_forward_m,
                maneuver_commit_lateral_m=maneuver_commit_lateral_m,
                maneuver_commit_release_m=maneuver_commit_release_m,
                clearance_alongside_length=clearance_alongside_length,
                clearance_lateral_min=clearance_lateral_min,
                dump_rollouts=dump_rollouts,
                use_rule_anchor=use_rule_anchor,
                use_handcrafted_candidates=use_handcrafted_candidates,
                use_geometry_recovery=use_geometry_recovery,
                recovery_enabled=recovery_enabled,
                head_ablation=head_ablation,
                world_model_mode=world_model_mode,
                decision_utility_compare_mode=decision_utility_compare_mode,
                ensemble_epistemic=ensemble_epistemic,
            )
            if safe:
                return SafeTrackBlendPolicy(
                    policy,
                    blend=safe_blend,
                    unsafe_blend=unsafe_blend,
                    base_policy_name=safe_base_policy,
                )
            return policy
        if name.endswith(".graph.pt"):
            from dlc.graph_policy import GraphActorPolicy, SafetyShieldPolicy

            policy = GraphActorPolicy(
                name,
                device=device,
                neighbor_mode=neighbor_mode,
                max_neighbors=max_neighbors,
                neighbor_selection_mode=neighbor_selection_mode,
            )
            if safe:
                return SafetyShieldPolicy(
                    policy,
                    fallback_policy=make_safe_base(safe_base_policy),
                    safe_blend=1.0 - safe_blend,
                    unsafe_blend=unsafe_blend,
                )
            return policy
        else:
            policy = TorchActorPolicy(name, seed=seed, device=device)
        if pack_neighbors:
            policy = PackedActorPolicy(
                policy,
                max_neighbors=int(pack_neighbors),
                selection_mode=neighbor_selection_mode,
                telemetry_version="corrected_v2",
            )
        if safe:
            return SafeTrackBlendPolicy(
                policy,
                blend=safe_blend,
                unsafe_blend=unsafe_blend,
                base_policy_name=safe_base_policy,
            )
        return policy
    if name.endswith(".sb3.zip"):
        policy = StableBaselinesActorPolicy(name, seed=seed, device=device)
        if safe:
            return SafeTrackBlendPolicy(
                policy,
                blend=safe_blend,
                unsafe_blend=unsafe_blend,
                base_policy_name=safe_base_policy,
            )
        return policy
    raise ValueError(f"unknown policy: {name}")
