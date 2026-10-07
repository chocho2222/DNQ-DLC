import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


MODEL_TYPES = {
    "joint_transition_observer",
    "joint_transition",
    "individual_transition",
}


def mlp(in_dim, hidden_dim, out_dim, layers=3):
    modules = []
    last_dim = in_dim
    for _ in range(layers):
        modules.append(nn.Linear(last_dim, hidden_dim))
        modules.append(nn.ELU())
        last_dim = hidden_dim
    modules.append(nn.Linear(last_dim, out_dim))
    return nn.Sequential(*modules)


class TelemetryWorldModel(nn.Module):
    """Telemetry analogue of DLC's latent world model.

    The paper learns image encoders and an RSSM latent state. In this state
    reproduction, telemetry itself is the compact latent observation, so the
    learned model predicts next telemetry and rewards directly.
    """

    def __init__(self, obs_dim, action_dim, num_agents=2, model_type="joint_transition_observer", hidden_dim=256):
        super().__init__()
        if model_type not in MODEL_TYPES:
            raise ValueError(f"unknown model_type: {model_type}")
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.num_agents = int(num_agents)
        self.model_type = model_type
        self.hidden_dim = int(hidden_dim)

        if model_type == "individual_transition":
            self.transition = mlp(obs_dim + action_dim, hidden_dim, obs_dim + 1)
        else:
            joint_in = num_agents * (obs_dim + action_dim)
            joint_out = num_agents * obs_dim + num_agents
            self.transition = mlp(joint_in, hidden_dim, joint_out)

        if model_type == "joint_transition_observer":
            self.observer = mlp(obs_dim, hidden_dim, num_agents * obs_dim)
        else:
            self.observer = None

    def forward(self, obs, action, ego_agent=0):
        if self.model_type == "individual_transition":
            return self._forward_individual(obs, action)
        if self.model_type == "joint_transition_observer":
            obs = self.observe_from_ego(obs, ego_agent=ego_agent)
        return self._forward_joint(obs, action)

    def observe_from_ego(self, obs, ego_agent=0):
        ego_obs = obs[:, ego_agent, :]
        joint_obs = self.observer(ego_obs)
        return joint_obs.view(obs.shape[0], self.num_agents, self.obs_dim)

    def _forward_joint(self, obs, action):
        batch = obs.shape[0]
        x = torch.cat([obs.reshape(batch, -1), action.reshape(batch, -1)], dim=-1)
        pred = self.transition(x)
        next_obs = pred[:, : self.num_agents * self.obs_dim].view(batch, self.num_agents, self.obs_dim)
        reward = pred[:, self.num_agents * self.obs_dim :]
        return next_obs, reward

    def _forward_individual(self, obs, action):
        batch = obs.shape[0]
        x = torch.cat([obs, action], dim=-1).reshape(batch * self.num_agents, -1)
        pred = self.transition(x).view(batch, self.num_agents, self.obs_dim + 1)
        return pred[:, :, : self.obs_dim], pred[:, :, self.obs_dim]


class Actor(nn.Module):
    def __init__(self, obs_dim, action_dim=3, hidden_dim=256):
        super().__init__()
        self.net = mlp(obs_dim, hidden_dim, action_dim)

    def forward(self, obs):
        raw = self.net(obs)
        steer = torch.tanh(raw[..., 0:1])
        gas = torch.sigmoid(raw[..., 1:2])
        brake = torch.sigmoid(raw[..., 2:3])
        return torch.cat([steer, gas, brake], dim=-1)


class Value(nn.Module):
    def __init__(self, obs_dim, hidden_dim=256):
        super().__init__()
        self.net = mlp(obs_dim, hidden_dim, 1)

    def forward(self, obs):
        return self.net(obs).squeeze(-1)


@dataclass
class TorchDLCBundle:
    world_model: TelemetryWorldModel
    actor: Actor
    value: Value
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
                "world_model": self.world_model.state_dict(),
                "actor": self.actor.state_dict(),
                "value": self.value.state_dict(),
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
        world_model = TelemetryWorldModel(
            obs_dim=meta["obs_dim"],
            action_dim=meta["action_dim"],
            num_agents=meta["num_agents"],
            model_type=meta["model_type"],
            hidden_dim=meta["hidden_dim"],
        )
        actor = Actor(meta["obs_dim"], meta["action_dim"], meta["hidden_dim"])
        value = Value(meta["obs_dim"], meta["hidden_dim"])
        world_model.load_state_dict(data["world_model"])
        actor.load_state_dict(data["actor"])
        value.load_state_dict(data["value"])
        world_model.eval()
        actor.eval()
        value.eval()
        return cls(
            world_model=world_model,
            actor=actor,
            value=value,
            obs_mean=data["obs_mean"],
            obs_std=data["obs_std"],
            action_mean=data["action_mean"],
            action_std=data["action_std"],
            meta=meta,
        )

    def normalize_obs(self, obs):
        return (np.asarray(obs, dtype=np.float32) - self.obs_mean) / self.obs_std

    def denormalize_action(self, action):
        return action * self.action_std + self.action_mean


def make_tensor_batch(transitions, device):
    obs = torch.as_tensor(np.stack([t["obs"] for t in transitions]), dtype=torch.float32, device=device)
    action = torch.as_tensor(np.stack([t["action"] for t in transitions]), dtype=torch.float32, device=device)
    reward = torch.as_tensor(np.stack([t["reward"] for t in transitions]), dtype=torch.float32, device=device)
    next_obs = torch.as_tensor(np.stack([t["next_obs"] for t in transitions]), dtype=torch.float32, device=device)
    return obs, action, reward, next_obs


def lambda_returns(rewards, values, bootstrap, discount=0.99, lambda_=0.95):
    next_values = torch.cat([values[:, 1:], bootstrap.unsqueeze(1)], dim=1)
    inputs = rewards + discount * next_values * (1.0 - lambda_)
    last = bootstrap
    returns = []
    for t in reversed(range(rewards.shape[1])):
        last = inputs[:, t] + discount * lambda_ * last
        returns.append(last)
    returns.reverse()
    return torch.stack(returns, dim=1)


def train_world_step(world_model, optimizer, batch, model_type, observer_weight=0.5):
    obs, action, reward, next_obs = batch
    pred_next, pred_reward = world_model(obs, action, ego_agent=0)
    loss = F.mse_loss(pred_next, next_obs) + F.mse_loss(pred_reward, reward)

    if model_type == "joint_transition_observer":
        observed = world_model.observe_from_ego(obs, ego_agent=0)
        loss = loss + observer_weight * F.mse_loss(observed, obs)

    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(world_model.parameters(), 100.0)
    optimizer.step()
    return float(loss.detach().cpu())


def train_actor_value_step(
    world_model,
    actor,
    value,
    actor_optimizer,
    value_optimizer,
    start_obs,
    behavior_action=None,
    horizon=15,
    discount=0.99,
    lambda_=0.95,
    behavior_clone_weight=0.0,
    safety_weight=0.0,
):
    world_model.eval()
    obs = start_obs
    imagined_obs = []
    imagined_rewards = []
    safety_losses = []

    for _ in range(horizon):
        action = actor(obs)
        obs, reward = world_model(obs, action, ego_agent=0)
        imagined_obs.append(obs)
        imagined_rewards.append(reward)
        if safety_weight > 0.0:
            lateral_error = obs[..., 12].abs()
            on_grass = obs[..., 15].clamp(min=0.0)
            backward = obs[..., 16].clamp(min=0.0)
            safety_losses.append(
                lateral_error.square().mean() + on_grass.mean() + backward.mean()
            )

    rewards = torch.stack(imagined_rewards, dim=1)
    value_inputs = torch.stack(imagined_obs, dim=1)
    values_for_return = value(value_inputs.reshape(-1, value_inputs.shape[-1])).view(value_inputs.shape[:3])
    bootstrap = value(obs.reshape(-1, obs.shape[-1])).view(obs.shape[:2]).detach()
    returns = lambda_returns(rewards, values_for_return.detach(), bootstrap, discount=discount, lambda_=lambda_)

    actor_loss = -returns.mean()
    if behavior_action is not None and behavior_clone_weight > 0.0:
        actor_loss = actor_loss + behavior_clone_weight * F.mse_loss(actor(start_obs), behavior_action)
    if safety_losses:
        actor_loss = actor_loss + safety_weight * torch.stack(safety_losses).mean()
    actor_optimizer.zero_grad()
    actor_loss.backward()
    nn.utils.clip_grad_norm_(actor.parameters(), 100.0)
    actor_optimizer.step()

    values = value(value_inputs.detach().reshape(-1, value_inputs.shape[-1])).view(value_inputs.shape[:3])
    value_targets = returns.detach()
    value_loss = F.mse_loss(values, value_targets)
    value_optimizer.zero_grad()
    value_loss.backward()
    nn.utils.clip_grad_norm_(value.parameters(), 100.0)
    value_optimizer.step()
    world_model.train()
    return float(actor_loss.detach().cpu()), float(value_loss.detach().cpu())


def train_target_actor_value_step(
    world_model,
    actor,
    value,
    actor_optimizer,
    value_optimizer,
    batch,
    target_agent,
    horizon=15,
    discount=0.99,
    lambda_=0.95,
    behavior_clone_weight=0.0,
    safety_weight=0.0,
    reward_clip=None,
    observation_clip=None,
    return_bound=None,
    normalize_returns=False,
    actor_grad_clip=100.0,
):
    """Imagination update for a single controlled row.

    The original DLC loop makes every vehicle a learner because every vehicle is
    driven by the same agent. In this benchmark only the target car is
    controlled, so the actor is asked about that row alone while the remaining
    rows keep the actions recorded with the batch. Those recorded actions are
    the background-policy actions the opponents actually execute in closed loop,
    so the imagined scene does not drift into a traffic pattern that never
    occurs, and the actor loss is not diluted by rows it never scores.
    """
    world_model.eval()
    obs, recorded_action, _, _ = batch

    def as_bounds(bounds):
        if bounds is None:
            return None
        return tuple(torch.as_tensor(np.asarray(bound), dtype=obs.dtype, device=obs.device)
                     for bound in bounds)

    reward_clip = as_bounds(reward_clip)
    observation_clip = as_bounds(observation_clip)
    target = int(target_agent)
    rewards, observations, safety_losses = [], [], []
    for _ in range(horizon):
        action = recorded_action.clone()
        action[:, target] = actor(obs[:, target])
        obs, reward = world_model(obs, action, ego_agent=target)
        if observation_clip is not None:
            # The same drift that inflates the imagined reward also walks the
            # predicted telemetry outside anything the transition model was fit
            # on. Bounding each predicted channel to its training range keeps the
            # value head, and therefore the returns it bootstraps, finite.
            obs = torch.clamp(obs, observation_clip[0], observation_clip[1])
        observations.append(obs)
        rewards.append(reward[:, target])
        if safety_weight > 0.0:
            lateral_error = obs[:, target, 12].abs()
            on_grass = obs[:, target, 15].clamp(min=0.0)
            backward = obs[:, target, 16].clamp(min=0.0)
            safety_losses.append(
                lateral_error.square().mean() + on_grass.mean() + backward.mean()
            )

    rewards = torch.stack(rewards, dim=1)
    if reward_clip is not None:
        # A one-step transition model used recursively drifts off the states it
        # was fit on, and its reward head then emits values that no episode
        # contains. Bounding the imagined reward to the range observed in the
        # training data keeps the actor objective finite; the same bound is
        # applied to every variant.
        rewards = torch.clamp(rewards, reward_clip[0], reward_clip[1])
    observation_rows = torch.stack(observations, dim=1)[:, :, target, :]
    flat_rows = observation_rows.reshape(-1, observation_rows.shape[-1])
    values_for_return = value(flat_rows).view(rewards.shape)
    bootstrap = value(obs[:, target]).detach()
    returns = lambda_returns(
        rewards, values_for_return.detach(), bootstrap, discount=discount, lambda_=lambda_
    )

    if return_bound is not None:
        # An unrolled one-step model plus a bootstrapped value head can drive the
        # TD(lambda) targets far outside anything the episodes contain; the actor
        # then follows that artefact instead of the expert term. Bounding the
        # target to the discounted horizon sum of the clipped reward range keeps
        # the value regression inside a scale the data supports.
        returns = torch.clamp(returns, -float(return_bound), float(return_bound))
    value_targets = returns.detach()
    actor_returns = returns
    if normalize_returns:
        # Standard advantage normalisation. Without it a return scale of a few
        # thousand makes the expert term (order 1e-3) irrelevant.
        actor_returns = (returns - returns.mean()) / (returns.std() + 1e-6)

    actor_loss = -actor_returns.mean()
    if behavior_clone_weight > 0.0:
        actor_loss = actor_loss + behavior_clone_weight * F.mse_loss(
            actor(batch[0][:, target]), recorded_action[:, target]
        )
    if safety_losses:
        actor_loss = actor_loss + safety_weight * torch.stack(safety_losses).mean()
    actor_optimizer.zero_grad()
    actor_loss.backward()
    nn.utils.clip_grad_norm_(actor.parameters(), float(actor_grad_clip))
    actor_optimizer.step()

    values = value(flat_rows.detach()).view(rewards.shape)
    value_loss = F.mse_loss(values, value_targets)
    value_optimizer.zero_grad()
    value_loss.backward()
    nn.utils.clip_grad_norm_(value.parameters(), 100.0)
    value_optimizer.step()
    world_model.train()
    return float(actor_loss.detach().cpu()), float(value_loss.detach().cpu())


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
