#!/usr/bin/env python
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dlc.policies import OvertakeTrackPolicy, TelemetryLanePolicy, TelemetryOvertakePolicy, TrackFollowPolicy
from dlc.rollout import make_env
from scripts.generate_multicar_overtake_gif import StableLanePolicy


class StableLanePositiveSteer(StableLanePolicy):
    def act(self, env, obs):
        action = super().act(env, obs)
        action[:, 0] *= -1.0
        return action


class FastWrapPolicy:
    def __init__(self, lookahead=9, target_speed=26.0, lateral_gain=0.8, heading_gain=1.9):
        self.lookahead = lookahead
        self.target_speed = target_speed
        self.lateral_gain = lateral_gain
        self.heading_gain = heading_gain

    def reset(self):
        pass

    def act(self, env, obs):
        base_env = env.unwrapped
        action = np.zeros((base_env.num_agents, 3), dtype=np.float32)
        track = np.asarray(base_env.track, dtype=np.float32)
        track_xy = track[:, 2:]
        for agent_id, car in enumerate(base_env.cars):
            pos = np.asarray(car.hull.position, dtype=np.float32)
            idx = int(np.argmin(np.linalg.norm(pos.reshape(1, 2) - track_xy, axis=1)))
            tgt = (idx + self.lookahead) % len(base_env.track)
            desired = float(base_env.track[tgt][1])
            local = float(base_env.track[idx][1])
            if base_env.episode_direction == "CW":
                desired += math.pi
                local += math.pi
            center = np.asarray(base_env.track[idx][2:], dtype=np.float32)
            normal = np.asarray([-math.sin(local), math.cos(local)], dtype=np.float32)
            lateral = float(np.dot(pos - center, normal))
            corrected = desired - self.lateral_gain * lateral / 40.0
            err = ((corrected - car.hull.angle + math.pi) % (2 * math.pi)) - math.pi
            speed = float(np.linalg.norm(car.hull.linearVelocity))
            action[agent_id, 0] = np.clip(-self.heading_gain * err, -1.0, 1.0)
            action[agent_id, 1] = 0.72 if speed < self.target_speed else 0.25
            action[agent_id, 2] = 0.0
        return action


class PurePursuitPolicy:
    def __init__(
        self,
        lookahead=14,
        target_speed=24.0,
        steer_gain=1.7,
        steer_sign=-1.0,
        throttle=0.65,
        brake_speed_margin=8.0,
    ):
        self.lookahead = int(lookahead)
        self.target_speed = float(target_speed)
        self.steer_gain = float(steer_gain)
        self.steer_sign = float(steer_sign)
        self.throttle = float(throttle)
        self.brake_speed_margin = float(brake_speed_margin)

    def reset(self):
        pass

    def act(self, env, obs):
        del obs
        base_env = env.unwrapped
        action = np.zeros((base_env.num_agents, 3), dtype=np.float32)
        track = np.asarray(base_env.track, dtype=np.float32)
        track_xy = track[:, 2:]
        for agent_id, car in enumerate(base_env.cars):
            pos = np.asarray(car.hull.position, dtype=np.float32)
            idx = int(np.argmin(np.linalg.norm(pos.reshape(1, 2) - track_xy, axis=1)))
            target = track_xy[(idx + self.lookahead) % len(track_xy)]
            target_angle = math.atan2(float(target[1] - pos[1]), float(target[0] - pos[0]))
            heading_error = ((target_angle - float(car.hull.angle) + math.pi) % (2 * math.pi)) - math.pi
            speed = float(np.linalg.norm(car.hull.linearVelocity))
            curvature_slowdown = min(abs(heading_error) * 10.0, 10.0)
            target_speed = max(10.0, self.target_speed - curvature_slowdown)
            action[agent_id, 0] = np.clip(self.steer_sign * self.steer_gain * heading_error, -1.0, 1.0)
            action[agent_id, 1] = self.throttle if speed < target_speed else 0.12
            action[agent_id, 2] = 0.0 if speed < target_speed + self.brake_speed_margin else 0.35
        return action


def run_policy(policy, args):
    env = make_env(
        num_agents=args.num_agents,
        seed=args.seed,
        observation_type="telemetry",
        start_order=list(range(args.num_agents)),
    )
    if hasattr(env, "_max_episode_steps"):
        env._max_episode_steps = args.steps + 1
    obs = env.reset()
    policy.reset()
    total_reward = np.zeros(args.num_agents, dtype=np.float64)
    grass_steps = np.zeros(args.num_agents, dtype=np.float64)
    done = False
    steps_run = 0
    try:
        for step in range(args.steps):
            action = policy.act(env, obs)
            obs, reward, done, _ = env.step(action)
            steps_run = step + 1
            total_reward += reward
            grass_steps += obs[:, 15] > 0.5
            if done:
                break
        return {
            "steps": steps_run,
            "done": bool(done),
            "track_tiles": len(env.unwrapped.track),
            "tiles": list(env.unwrapped.tile_visited_count),
            "grass_rate": (grass_steps / max(steps_run, 1)).tolist(),
            "total_reward": total_reward.tolist(),
        }
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-agents", type=int, default=1)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--steps", type=int, default=1800)
    parser.add_argument("--sweep-stable", action="store_true")
    args = parser.parse_args()

    if args.sweep_stable:
        results = []
        for lookahead in [4, 6, 8, 10]:
            for target_speed in [8.0, 10.0, 12.0]:
                for lateral_gain in [0.25, 0.45, 0.7]:
                    for heading_gain in [1.2, 1.8]:
                        policy = StableLanePolicy(
                            lookahead=lookahead,
                            target_speed=target_speed,
                            lateral_gain=lateral_gain,
                            heading_gain=heading_gain,
                        )
                        result = run_policy(policy, args)
                        score = (
                            result["tiles"][0]
                            - 80.0 * result["grass_rate"][0]
                            + 1000.0 * int(result["tiles"][0] >= result["track_tiles"])
                        )
                        results.append((score, lookahead, target_speed, lateral_gain, heading_gain, result))
        results.sort(key=lambda item: item[0], reverse=True)
        for item in results[:20]:
            score, lookahead, target_speed, lateral_gain, heading_gain, result = item
            print(
                {
                    "score": score,
                    "lookahead": lookahead,
                    "target_speed": target_speed,
                    "lateral_gain": lateral_gain,
                    "heading_gain": heading_gain,
                    "result": result,
                },
                flush=True,
            )
        return

    policies = {
        "track_follow": TrackFollowPolicy(target_speed=14.0),
        "overtake_track": OvertakeTrackPolicy(target_speed=14.0, pass_speed=16.0),
        "telemetry_lane": TelemetryLanePolicy(),
        "telemetry_overtake": TelemetryOvertakePolicy(),
        "stable_lane": StableLanePolicy(target_speed=13.0),
        "stable_lane_positive_steer": StableLanePositiveSteer(target_speed=13.0),
        "fast_wrap": FastWrapPolicy(),
        "pure_pursuit_neg": PurePursuitPolicy(steer_sign=-1.0),
        "pure_pursuit_pos": PurePursuitPolicy(steer_sign=1.0),
        "pure_pursuit_slow": PurePursuitPolicy(lookahead=10, target_speed=18.0, steer_sign=-1.0, throttle=0.45),
    }
    for name, policy in policies.items():
        print(name, run_policy(policy, args), flush=True)


if __name__ == "__main__":
    main()
