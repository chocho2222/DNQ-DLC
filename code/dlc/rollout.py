import gym
import gym_multi_car_racing  # noqa: F401 - registers MultiCarRacing-v0
import numpy as np


def make_env(
    num_agents=2,
    seed=0,
    observation_type="telemetry",
    start_order=None,
    line_spacing=None,
    lateral_spacing=None,
    track_path=None,
    max_neighbors=None,
    telemetry_version='legacy_v1',
    neighbor_order='relevance',
):
    np.random.seed(seed)
    env_kwargs = dict(
        num_agents=num_agents,
        direction="CCW",
        use_random_direction=False,
        backwards_flag=True,
        h_ratio=0.25,
        use_ego_color=False,
        observation_type=observation_type,
        telemetry_version=telemetry_version,
        neighbor_order=neighbor_order,
    )
    if start_order is not None:
        env_kwargs["start_order"] = start_order
    if line_spacing is not None:
        env_kwargs["line_spacing"] = line_spacing
    if lateral_spacing is not None:
        env_kwargs["lateral_spacing"] = lateral_spacing
    if track_path is not None:
        env_kwargs["track_path"] = track_path
    env_kwargs["max_neighbors"] = None if max_neighbors is None else int(max_neighbors)
    env = gym.make(
        "MultiCarRacing-v0",
        **env_kwargs,
    )
    env.seed(seed)
    return env


def run_episode(env, policy, max_steps=1000):
    obs = env.reset()
    policy.reset()
    total_reward = np.zeros(env.unwrapped.num_agents, dtype=np.float64)
    trajectory = []

    done = False
    for step in range(max_steps):
        action = policy.act(env, obs)
        next_obs, reward, done, info = env.step(action)
        total_reward += reward
        trajectory.append(
            {
                "obs": np.asarray(obs, dtype=np.float32),
                "action": np.asarray(action, dtype=np.float32),
                "reward": np.asarray(reward, dtype=np.float32),
                "next_obs": np.asarray(next_obs, dtype=np.float32),
                "done": bool(done),
                "info": info,
            }
        )
        obs = next_obs
        if done:
            break

    return {
        "steps": len(trajectory),
        "done": bool(done),
        "total_reward": total_reward,
        "tile_visited_count": list(env.unwrapped.tile_visited_count),
        "trajectory": trajectory,
    }
