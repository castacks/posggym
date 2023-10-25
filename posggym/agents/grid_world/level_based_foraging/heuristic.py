"""Heuristic policies for Level-Based Foraging env.

Reference:
https://github.com/uoe-agents/lb-foraging/blob/master/lbforaging/agents/heuristic_agent.py
https://github.com/uoe-agents/BRDiv/blob/master/envs/lb-foraging/lbforaging/agents/heuristic_agent.py

"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast

from posggym.agents.policy import Policy, PolicyID, PolicyState
from posggym.agents.utils import action_distributions
from posggym.envs.grid_world.level_based_foraging import (
    LBFAction,
    LBFObs,
    LevelBasedForagingModel,
)

if TYPE_CHECKING:
    from posggym.envs.grid_world.core import Coord


class LBFHeuristicPolicy(Policy[LBFAction, LBFObs]):
    """Heuristic agent for the Level-Based Foraging env.

    This is the abstract Level-Based Foraging env heuristic policy class.
    Concrete implementations must implement the get_action_from_obs method.
    """

    def __init__(
        self, model: LevelBasedForagingModel, agent_id: str, policy_id: PolicyID
    ):
        super().__init__(model, agent_id, policy_id)
        assert model.observation_mode in ("vector", "tuple")
        self._rng = random.Random()
        self.field_width, self.field_height = model.field_size

    def reset(self, *, seed: int | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng.seed(seed)

    def get_initial_state(self) -> PolicyState:
        state = super().get_initial_state()
        state["last_obs"] = None
        state["agent_pos"] = None
        state["target_pos"] = None
        return state

    def get_next_state(
        self,
        obs: LBFObs,
        state: PolicyState,
    ) -> PolicyState:
        model = cast(LevelBasedForagingModel, self.model)
        agent_obs, food_obs = model.parse_obs(obs)
        other_agent_obs = [o for o in agent_obs[1:] if o[0] > -1]
        return {
            "last_obs": obs,
            "agent_pos": agent_obs[0][:2],
            "target_pos": self._get_target_pos(
                agent_obs[0], food_obs, other_agent_obs, state
            ),
        }

    def sample_action(self, state: PolicyState) -> LBFAction:
        if state["target_pos"] is None:
            return self._rng.choice(list(LBFAction))

        possible_actions = self._move_towards(
            state["agent_pos"], state["target_pos"], load_if_adjacent=True
        )
        action = self._rng.choice(possible_actions)
        return action

    def get_pi(self, state: PolicyState) -> action_distributions.ActionDistribution:
        if state["target_pos"] is None:
            possible_actions = list(LBFAction)
        else:
            possible_actions = self._move_towards(
                state["agent_pos"], state["target_pos"], load_if_adjacent=True
            )
        return action_distributions.DiscreteActionDistribution(
            {a: 1 / len(possible_actions) for a in possible_actions}, self._rng
        )

    def get_value(self, state: PolicyState) -> float:
        raise NotImplementedError(
            f"`get_value()` no implemented by {self.__class__.__name__} policy"
        )

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        """Get target position from observations."""
        raise NotImplementedError

    def _get_food_by_distance(
        self,
        agent_pos: Coord,
        food_obs: List[Tuple[int, int, int]],
        closest: bool = True,
        max_food_level: Optional[int] = None,
    ) -> Optional[Coord]:
        food_distances: Dict[int, List[Coord]] = {}
        for y, x, level in food_obs:
            if x == -1 or (max_food_level is not None and level > max_food_level):
                continue
            distance = (agent_pos[0] - y) ** 2 + (agent_pos[1] - x) ** 2
            if distance not in food_distances:
                food_distances[distance] = []
            food_distances[distance].append((y, x))

        if len(food_distances) == 0:
            # No food in sight
            return None

        desired_dist = min(food_distances) if closest else max(food_distances)
        return self._rng.choice(food_distances[desired_dist])

    def _center_of_agents(self, agent_obs: List[Tuple[int, int, int]]) -> Coord:
        y_mean = sum(o[0] for o in agent_obs) / len(agent_obs)
        x_mean = sum(o[1] for o in agent_obs) / len(agent_obs)
        return round(x_mean), round(y_mean)

    def _move_towards(
        self, agent_pos: Coord, target: Coord, load_if_adjacent: bool = True
    ) -> List[LBFAction]:
        if (
            load_if_adjacent
            and abs(target[0] - agent_pos[0]) + abs(target[1] - agent_pos[1]) == 1
        ):
            return [LBFAction.LOAD]

        valid_actions = []
        # Note positioning is relative to observing agents observation grid, not the
        # global grid. So relative directions are different.
        if target[0] < agent_pos[0]:
            valid_actions.append(LBFAction.WEST)
        elif target[0] > agent_pos[0]:
            valid_actions.append(LBFAction.EAST)

        if target[1] > agent_pos[1]:
            valid_actions.append(LBFAction.SOUTH)
        elif target[1] < agent_pos[1]:
            valid_actions.append(LBFAction.NORTH)

        if not valid_actions:
            valid_actions.append(LBFAction.NONE)
        return valid_actions

    def _get_updated_pos(self, prev_pos: Coord, last_action: LBFAction) -> Coord:
        # Updates relative position based on last action
        if last_action == LBFAction.NORTH:
            return prev_pos[0], prev_pos[1] + 1
        elif last_action == LBFAction.SOUTH:
            return prev_pos[0], prev_pos[1] - 1
        elif last_action == LBFAction.EAST:
            return prev_pos[0] - 1, prev_pos[1]
        elif last_action == LBFAction.WEST:
            return prev_pos[0] + 1, prev_pos[1]
        else:
            return prev_pos


class LBFHeuristicPolicy1(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 1.

    H1 always goes to the closest observed food, irrespective of the foods level.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        agent_pos = agent_obs[:2]
        return self._get_food_by_distance(
            agent_pos, food_obs, closest=True, max_food_level=None
        )


class LBFHeuristicPolicy2(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 2.

    H2 goes towards the visible food that is closest to the centre of visible players,
    irrespective of food level.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        if not other_agent_obs:
            return None

        center_pos = self._center_of_agents(other_agent_obs)
        return self._get_food_by_distance(
            center_pos, food_obs, closest=True, max_food_level=None
        )


class LBFHeuristicPolicy3(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 3.

    H3 goes towards the closest visible food with a compatible level.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        agent_pos, agent_level = agent_obs[:2], agent_obs[2]
        return self._get_food_by_distance(
            agent_pos, food_obs, closest=True, max_food_level=agent_level
        )


class LBFHeuristicPolicy4(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 4.

    H4 goes towards the visible food which is closest to all visible agents such that
    the sum of the visible players level and the policy agent's level is sufficient to
    load the food.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        if not other_agent_obs:
            return None

        center_pos = self._center_of_agents(other_agent_obs)
        level_sum = sum([o[2] for o in other_agent_obs]) + agent_obs[2]
        return self._get_food_by_distance(
            center_pos, food_obs, closest=True, max_food_level=level_sum
        )


class LBFHeuristicPolicy5(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 5.

    H5 selects and goes towards the furthest visible food, irrespective of food level.
    At the start of an episode it will select a target food and move towards it. Each
    time it's current target food is collected it then selects a new target based on
    the heuristic above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        # either no target selected yet or food was collected, or is no longer visible
        return self._get_food_by_distance(
            agent_obs[:2], food_obs, closest=False, max_food_level=None
        )


class LBFHeuristicPolicy6(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 6.

    H6 selects and goes towards the visible food that is furthest from the center of
    visible players, irrespective of food level. At the start of an episode it will
    select a target food and move towards it. Each time it's current target food is
    collected it then selects a new target based on the heuristic above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        # select new target
        if not other_agent_obs:
            # act randomly until we see other agents
            return None

        center_pos = self._center_of_agents(other_agent_obs)
        return self._get_food_by_distance(
            center_pos, food_obs, closest=False, max_food_level=None
        )


class LBFHeuristicPolicy7(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 7.

    H7 selects and goes towards the furthest visible food with a compatible level.
    At the start of an episode it will select a target food and move towards it.
    Each time it's current target food is collected it then selects a new target based
    on the heuristic above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        # either no target selected yet or food was collected, or is no longer visible
        return self._get_food_by_distance(
            agent_obs[:2], food_obs, closest=False, max_food_level=agent_obs[2]
        )


class LBFHeuristicPolicy8(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 8.

    H8 selects and goes towards the visible food that is furthest from the center of
    visible players that is compatible with the agents level. At the start of an episode
    it will select a target food and move towards it. Each time it's current target food
    is collected it then selects a new target based on the heuristic above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        # select new target
        if not other_agent_obs:
            # act randomly until we see other agents
            return None

        center_pos = self._center_of_agents(other_agent_obs)
        return self._get_food_by_distance(
            center_pos, food_obs, closest=False, max_food_level=agent_obs[2]
        )


class LBFHeuristicPolicy9(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 9.

    H9 targets a random visible food. At the start of an episode it will select a target
    food and move towards it. Each time it's current target food is collected it then
    selects a new target based on the heuristic above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        food_coords = [f[:2] for f in food_obs if f[1] > -1]
        if not food_coords:
            return None
        return self._rng.choice(food_coords)


class LBFHeuristicPolicy10(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 10.

    H10 targets a random visible food whose level is compatible the agents. At the start
    of an episode it will select a target food and move towards it. Each time it's
    current target food is collected it then selects a new target based on the heuristic
    above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        food_coords = [f[:2] for f in food_obs if f[1] > -1 and f[2] <= agent_obs[2]]
        if not food_coords:
            return None
        return self._rng.choice(food_coords)


class LBFHeuristicPolicy11(LBFHeuristicPolicy):
    """Level-Based Foraging Heuristic Policy 11.

    H11 targets a random visible food whose level is compatible with all visible
    agents. At the start of an episode it will select a target food and move towards it.
    Each time it's current target food is collected it then selects a new target based
    on the heuristic above.
    """

    def _get_target_pos(
        self,
        agent_obs: Tuple[int, int, int],
        food_obs: List[Tuple[int, int, int]],
        other_agent_obs: List[Tuple[int, int, int]],
        state: PolicyState,
    ) -> Optional[Coord]:
        target_pos = state["target_pos"]
        if target_pos is not None:
            new_target_pos = self._get_updated_pos(target_pos, state["action"])
            if new_target_pos in (f[:2] for f in food_obs):
                return new_target_pos

        level_sum = sum([o[2] for o in other_agent_obs]) + agent_obs[2]
        food_coords = [f[:2] for f in food_obs if f[1] > -1 and f[2] <= level_sum]
        if not food_coords:
            return None
        return self._rng.choice(food_coords)
