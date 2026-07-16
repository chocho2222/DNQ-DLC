import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def _augment_bias(x):
    return np.concatenate([x, np.ones((x.shape[0], 1), dtype=x.dtype)], axis=1)


class RidgeRegressor:
    def __init__(self, l2=1e-3):
        self.l2 = float(l2)
        self.coef_ = None

    def fit(self, x, y):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        x_aug = _augment_bias(x)
        gram = x_aug.T @ x_aug
        gram += self.l2 * np.eye(gram.shape[0], dtype=np.float64)
        self.coef_ = np.linalg.solve(gram, x_aug.T @ y)
        return self

    def predict(self, x):
        x = np.asarray(x, dtype=np.float64)
        x_aug = _augment_bias(x)
        return x_aug @ self.coef_


def flatten_joint(obs):
    return np.asarray(obs, dtype=np.float64).reshape(-1)


def flatten_action(action):
    return np.asarray(action, dtype=np.float64).reshape(-1)


def split_agents(vec, num_agents, feature_dim):
    return np.asarray(vec, dtype=np.float64).reshape(num_agents, feature_dim)


@dataclass
class StateModelBundle:
    model_type: str
    num_agents: int
    feature_dim: int
    models: dict
    obs_mean: np.ndarray
    obs_std: np.ndarray
    act_mean: np.ndarray
    act_std: np.ndarray
    meta: dict

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            model_type=self.model_type,
            num_agents=self.num_agents,
            feature_dim=self.feature_dim,
            obs_mean=self.obs_mean,
            obs_std=self.obs_std,
            act_mean=self.act_mean,
            act_std=self.act_std,
            meta_json=json.dumps(self.meta),
            **{f"coef_{name}": model.coef_ for name, model in self.models.items()},
        )

    @classmethod
    def load(cls, path):
        data = np.load(path, allow_pickle=False)
        meta = json.loads(str(data["meta_json"]))
        model_type = str(data["model_type"])
        num_agents = int(data["num_agents"])
        feature_dim = int(data["feature_dim"])
        obs_mean = data["obs_mean"]
        obs_std = data["obs_std"]
        act_mean = data["act_mean"]
        act_std = data["act_std"]

        models = {}
        if model_type == "individual_transition":
            for agent_id in range(num_agents):
                models[f"agent_{agent_id}"] = RidgeRegressor()
                models[f"agent_{agent_id}"].coef_ = data[f"coef_agent_{agent_id}"]
        else:
            models["joint"] = RidgeRegressor()
            models["joint"].coef_ = data["coef_joint"]
            if "coef_observer" in data.files:
                models["observer"] = RidgeRegressor()
                models["observer"].coef_ = data["coef_observer"]

        return cls(
            model_type=model_type,
            num_agents=num_agents,
            feature_dim=feature_dim,
            models=models,
            obs_mean=obs_mean,
            obs_std=obs_std,
            act_mean=act_mean,
            act_std=act_std,
            meta=meta,
        )

    def normalize_obs(self, obs):
        return (np.asarray(obs, dtype=np.float64) - self.obs_mean) / self.obs_std

    def normalize_act(self, action):
        return (np.asarray(action, dtype=np.float64) - self.act_mean) / self.act_std

    def denormalize_obs(self, obs):
        return obs * self.obs_std + self.obs_mean

    def normalize_flat_obs(self, obs):
        return (np.asarray(obs, dtype=np.float64).reshape(-1) - self.obs_mean.reshape(-1)) / self.obs_std.reshape(-1)

    def normalize_flat_act(self, action):
        return (np.asarray(action, dtype=np.float64).reshape(-1) - self.act_mean.reshape(-1)) / self.act_std.reshape(-1)

    def denormalize_flat_obs(self, obs):
        return np.asarray(obs, dtype=np.float64) * self.obs_std.reshape(-1) + self.obs_mean.reshape(-1)

    def predict(self, obs, action, ego_agent=0):
        if self.model_type == "individual_transition":
            return self._predict_individual(obs, action)
        if self.model_type == "joint_transition_observer":
            return self._predict_joint_with_observer(obs, action, ego_agent=ego_agent)
        return self._predict_joint(obs, action)

    def _predict_joint(self, obs, action):
        x = np.concatenate([self.normalize_flat_obs(flatten_joint(obs)), self.normalize_flat_act(flatten_action(action))])
        pred = self.models["joint"].predict(x[None, :])[0]
        next_obs_flat = pred[:-self.num_agents]
        reward = pred[-self.num_agents:]
        return self.denormalize_flat_obs(next_obs_flat).reshape(self.num_agents, self.feature_dim), reward

    def _predict_joint_with_observer(self, obs, action, ego_agent=0):
        obs = np.asarray(obs, dtype=np.float64)
        ego = obs[ego_agent : ego_agent + 1].reshape(1, -1)
        observed = self.models["observer"].predict(
            (ego - self.obs_mean[ego_agent]) / self.obs_std[ego_agent]
        )[0]
        reconstructed = self.denormalize_flat_obs(observed).reshape(self.num_agents, self.feature_dim)
        return self._predict_joint(reconstructed, action)

    def _predict_individual(self, obs, action):
        obs = np.asarray(obs, dtype=np.float64)
        action = np.asarray(action, dtype=np.float64)
        next_obs = np.zeros_like(obs, dtype=np.float64)
        reward = np.zeros(self.num_agents, dtype=np.float64)
        for agent_id in range(self.num_agents):
            model = self.models[f"agent_{agent_id}"]
            x = np.concatenate([
                (obs[agent_id] - self.obs_mean[agent_id]) / self.obs_std[agent_id],
                (action[agent_id] - self.act_mean[agent_id]) / self.act_std[agent_id],
            ])
            pred = model.predict(x[None, :])[0]
            next_obs[agent_id] = pred[:-1] * self.obs_std[agent_id] + self.obs_mean[agent_id]
            reward[agent_id] = pred[-1]
        return next_obs, reward


def fit_state_models(episodes, model_type, num_agents, feature_dim, l2=1e-3):
    obs_samples = []
    act_samples = []
    next_obs_samples = []
    reward_samples = []

    for episode in episodes:
        for transition in episode["trajectory"]:
            obs_samples.append(transition["obs"])
            act_samples.append(transition["action"])
            next_obs_samples.append(transition["next_obs"])
            reward_samples.append(transition["reward"])

    obs_samples = np.asarray(obs_samples, dtype=np.float64)
    act_samples = np.asarray(act_samples, dtype=np.float64)
    next_obs_samples = np.asarray(next_obs_samples, dtype=np.float64)
    reward_samples = np.asarray(reward_samples, dtype=np.float64)

    obs_mean = obs_samples.mean(axis=0)
    obs_std = obs_samples.std(axis=0) + 1e-6
    act_mean = act_samples.mean(axis=0)
    act_std = act_samples.std(axis=0) + 1e-6

    models = {}
    if model_type == "individual_transition":
        for agent_id in range(num_agents):
            x = np.concatenate(
                [
                    (obs_samples[:, agent_id, :] - obs_mean[agent_id]) / obs_std[agent_id],
                    (act_samples[:, agent_id, :] - act_mean[agent_id]) / act_std[agent_id],
                ],
                axis=1,
            )
            y = np.concatenate(
                [
                    (next_obs_samples[:, agent_id, :] - obs_mean[agent_id]) / obs_std[agent_id],
                    reward_samples[:, agent_id : agent_id + 1],
                ],
                axis=1,
            )
            models[f"agent_{agent_id}"] = RidgeRegressor(l2=l2).fit(x, y)
    else:
        x = np.concatenate(
            [
                (obs_samples.reshape(len(obs_samples), -1) - obs_mean.reshape(-1)) / obs_std.reshape(-1),
                (act_samples.reshape(len(act_samples), -1) - act_mean.reshape(-1)) / act_std.reshape(-1),
            ],
            axis=1,
        )
        y = np.concatenate(
            [
                (next_obs_samples.reshape(len(next_obs_samples), -1) - obs_mean.reshape(-1)) / obs_std.reshape(-1),
                reward_samples,
            ],
            axis=1,
        )
        models["joint"] = RidgeRegressor(l2=l2).fit(x, y)

        if model_type == "joint_transition_observer":
            ego = obs_samples.reshape(len(obs_samples) * num_agents, feature_dim)
            full = np.repeat(
                obs_samples.reshape(len(obs_samples), -1),
                repeats=num_agents,
                axis=0,
            )
            ego_mean = np.tile(obs_mean, (len(obs_samples), 1))
            ego_std = np.tile(obs_std, (len(obs_samples), 1))
            models["observer"] = RidgeRegressor(l2=l2).fit(
                (ego - ego_mean) / ego_std,
                (full - obs_mean.reshape(-1)) / obs_std.reshape(-1),
            )

    meta = {
        "l2": l2,
        "training_transitions": int(len(obs_samples)),
    }
    return StateModelBundle(
        model_type=model_type,
        num_agents=num_agents,
        feature_dim=feature_dim,
        models=models,
        obs_mean=obs_mean,
        obs_std=obs_std,
        act_mean=act_mean,
        act_std=act_std,
        meta=meta,
    )
