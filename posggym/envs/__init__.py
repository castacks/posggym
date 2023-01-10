"""Registers the internal POSGGym environments.

Based on the Farama Foundation Gymnasium API:
https://github.com/Farama-Foundation/Gymnasium/blob/v0.27.0/gymnasium/envs/__init__.py

"""
import math

# import warnings
from itertools import product

from posggym.envs.grid_world import (
    driving,
    predator_prey,
    pursuit_evasion,
    two_paths,
    uav,
)
from posggym.envs.registration import (  # noqa: F401
    make,
    pprint_registry,
    register,
    registry,
    spec,
)


# Classic
# -------------------------------------------

register(id="MABC-v0", entry_point="posggym.envs.classic.mabc:MABCEnv")

register(
    id="MultiAgentTiger-v0", entry_point="posggym.envs.classic.tiger:MultiAgentTigerEnv"
)

register(
    id="RockPaperScissors-v0",
    entry_point="posggym.envs.classic.rock_paper_scissors:RockPaperScissorsEnv",
)


# Grid World
# -------------------------------------------

# Two Paths
for grid_name in two_paths.SUPPORTED_GRIDS:
    register(
        id=f"TwoPaths{grid_name}-v0",
        entry_point="posggym.envs.grid_world.two_paths:TwoPathsEnv",
        max_episode_steps=two_paths.SUPPORTED_GRIDS[grid_name][1],
        kwargs={"grid_name": grid_name, "action_probs": 1.0, "infinite_horizon": False},
    )

    register(
        id=f"TwoPaths{grid_name}Stochastic-v0",
        entry_point="posggym.envs.grid_world.two_paths:TwoPathsEnv",
        max_episode_steps=two_paths.SUPPORTED_GRIDS[grid_name][1],
        kwargs={"grid_name": grid_name, "action_probs": 0.9, "infinite_horizon": False},
    )

    register(
        id=f"TwoPaths{grid_name}Infinite-v0",
        entry_point="posggym.envs.grid_world.two_paths:TwoPathsEnv",
        kwargs={"grid_name": grid_name, "action_probs": 1.0, "infinite_horizon": True},
    )

    register(
        id=f"TwoPaths{grid_name}InfiniteStochastic-v0",
        entry_point="posggym.envs.grid_world.two_paths:TwoPathsEnv",
        kwargs={"grid_name": grid_name, "action_probs": 0.9, "infinite_horizon": True},
    )


# Pursuit-Evasion
for grid_name in pursuit_evasion.SUPPORTED_GRIDS:
    register(
        id=f"PursuitEvasion{grid_name}-v0",
        entry_point=("posggym.envs.grid_world.pursuit_evasion:PursuitEvasionEnv"),
        max_episode_steps=pursuit_evasion.SUPPORTED_GRIDS[grid_name][1],
        kwargs={
            "grid_name": grid_name,
            "action_probs": 1.0,
            "max_obs_distance": 12,
            "normalize_reward": True,
            "use_progress_reward": True,
        },
    )

    register(
        id=f"PursuitEvasion{grid_name}Stochastic-v0",
        entry_point=("posggym.envs.grid_world.pursuit_evasion:PursuitEvasionEnv"),
        max_episode_steps=pursuit_evasion.SUPPORTED_GRIDS[grid_name][1],
        kwargs={
            "grid_name": grid_name,
            "action_probs": 0.9,
            "max_obs_distance": 12,
            "normalize_reward": True,
            "use_progress_reward": True,
        },
    )


# # Unmanned Aerial Vehicle (UAV)
for grid_name in uav.SUPPORTED_GRIDS:
    register(
        id=f"UAV{grid_name}-v0",
        entry_point="posggym.envs.grid_world.uav:UAVEnv",
        kwargs={
            "grid_name": grid_name,
        },
    )


# Driving
for grid_name in driving.SUPPORTED_GRIDS:
    grid_fn, finite_steps = driving.SUPPORTED_GRIDS[grid_name]
    for n in range(2, grid_fn().supported_num_agents + 1):
        env_name_prefix = f"Driving{grid_name}-n{n}"
        register(
            id=f"{env_name_prefix}-v0",
            entry_point="posggym.envs.grid_world.driving:DrivingEnv",
            max_episode_steps=finite_steps,
            kwargs={
                "grid": grid_fn(),
                "num_agents": n,
                "obs_dim": (3, 1, 1),
                "obstacle_collisions": False,
                "infinite_horizon": False,
            },
        )

        register(
            id=f"{env_name_prefix}Infinite-v0",
            entry_point="posggym.envs.grid_world.driving:DrivingEnv",
            kwargs={
                "grid": grid_fn(),
                "num_agents": n,
                "obs_dim": (3, 1, 1),
                "obstacle_collisions": False,
                "infinite_horizon": True,
            },
        )

        register(
            id=f"{env_name_prefix}Hard-v0",
            entry_point="posggym.envs.grid_world.driving:DrivingEnv",
            max_episode_steps=finite_steps,
            kwargs={
                "grid": grid_fn(),
                "num_agents": n,
                "obs_dim": (3, 1, 1),
                "obstacle_collisions": True,
                "infinite_horizon": False,
            },
        )

        register(
            id=f"{env_name_prefix}HardInfinite-v0",
            entry_point="posggym.envs.grid_world.driving:DrivingEnv",
            kwargs={
                "grid": grid_fn(),
                "num_agents": n,
                "obs_dim": (3, 1, 1),
                "obstacle_collisions": True,
                "infinite_horizon": True,
            },
        )


# Driving Gen
for grid_name in driving.SUPPORTED_GEN_PARAMS:
    env_params = driving.SUPPORTED_GEN_PARAMS[grid_name]
    gen_params, finite_steps = env_params  # type: ignore
    register(
        id=f"DrivingGen{grid_name}-v0",
        entry_point="posggym.envs.grid_world.driving:DrivingGenEnv",
        max_episode_steps=finite_steps,
        kwargs={
            "num_agents": 2,
            "obs_dim": (3, 1, 1),
            "obstacle_collisions": False,
            "n_grids": None,
            "generator_params": gen_params,  # type: ignore
            "infinite_horizon": False,
        },
    )


# Predator-Prey
coop = [True, False]
prey_strength = [1, 2, 3, 4]  # min is 1, max is 4 (since 4 adjacent cells)
num_prey = [1, 2, 3, 4]  # could be more, depending on grid size
num_predators = [2, 3, 4]  # max is 8 for default grids

for grid_name, c, s, n_prey, n_pred in product(
    predator_prey.SUPPORTED_GRIDS, coop, prey_strength, num_prey, num_predators
):
    if s > n_pred:
        continue

    pp_grid_fn, finite_steps = predator_prey.SUPPORTED_GRIDS[grid_name]
    coop_str = "-coop" if c else ""
    env_name_suffix = f"{grid_name}-P{n_pred}-p{n_prey}-s{s}{coop_str}-v0"
    register(
        id=f"PredatorPrey{env_name_suffix}",
        entry_point="posggym.envs.grid_world.predator_prey:PPEnv",
        max_episode_steps=finite_steps,
        kwargs={
            "grid": pp_grid_fn(),
            "num_predators": n_pred,
            "num_prey": n_prey,
            "cooperative": c,
            "prey_strength": s,
            "obs_dim": 2,
        },
    )


# Level-Based Foraging
# -------------------------------------------
# Ref: github.com/semitable/lb-foraging/blob/master/lbforaging/__init__.py

sizes = [5, 10, 20]
players = [2, 4]  # reduced
foods = [1, 3, 5, 7, 10]
coop = [True, False]
static_layout = [True, False]

for s, n, f, c, sl in product(sizes, players, foods, coop, static_layout):
    if sl and f > math.floor((s - 1) / 2) ** 2 or n > math.ceil(s / 2) * 4 - 4:
        continue

    coop_str = "-coop" if c else ""
    static_layout_str = "-static" if sl else ""
    suffix = f"{s}x{s}-n{n}-f{f}{coop_str}{static_layout_str}-v2"
    register(
        id=f"LBF{suffix}",
        entry_point="posggym.envs.grid_world.lbf:LBFEnv",
        max_episode_steps=50,
        kwargs={
            "num_agents": n,
            "max_agent_level": 3,
            "field_size": (s, s),
            "max_food": f,
            "sight": 2,
            "force_coop": c,
            "static_layout": sl,
            "normalize_reward": True,
            "observation_mode": "tuple",
            "penalty": 0.0,
        },
    )

    register(
        id=f"LBFVector{suffix}",
        entry_point="posggym.envs.grid_world.lbf:LBFEnv",
        max_episode_steps=50,
        kwargs={
            "num_agents": n,
            "max_agent_level": 3,
            "field_size": (s, s),
            "max_food": f,
            "sight": 2,
            "force_coop": c,
            "static_layout": sl,
            "normalize_reward": True,
            "observation_mode": "vector",
            "penalty": 0.0,
        },
    )

    register(
        id=f"LBFGrid{suffix}",
        entry_point="posggym.envs.grid_world.lbf:LBFEnv",
        max_episode_steps=50,
        kwargs={
            "num_agents": n,
            "max_agent_level": 3,
            "field_size": (s, s),
            "max_food": f,
            "sight": 2,
            "force_coop": c,
            "static_layout": sl,
            "normalize_reward": True,
            "observation_mode": "grid",
            "penalty": 0.0,
        },
    )
