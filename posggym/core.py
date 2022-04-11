"""Contains the main POSG environment class and functions.

The implementation is heavily inspired by the Open AI Gym
https://github.com/openai/gym

"""
import abc
from typing import Tuple, Optional, Dict

from gym import spaces

import posggym.model as M

# TODO Handle seeds properly


class Env(abc.ABC):
    """The main POSG environment class.

    It encapsulates an environment and POSG model.

    The main API methods that users of this class need to know are:

        step
        reset
        render
        close
        seed

    And the main attributes:

        n_agents: the number of agents in the environment
        model: the POSG model of the environment (posggym.model.POSGModel)
        action_specs : the action space specs for each agent
        observation_spacs : the observation space specs for each agent
        reward_specs : the reward specs for each agent

    """

    # Set this in SOME subclasses
    metadata: Dict = {"render.modes": []}

    @abc.abstractmethod
    def step(self,
             actions: Tuple[M.Action, ...]
             ) -> Tuple[M.JointObservation, M.JointReward, bool, Dict]:
        """Run one timestep in the environment.

        When the end of an episode is reached, the user is responsible for
        calling `reset()` to reset this environments state.

        Accepts a joint action and returns a tuple (observations, rewards,
        done, info)

        Arguments
        ---------
        actions : object
            a joint action containing one action per agent in the environment.

        Returns
        -------
        observations : object
            the joint observation containing one observation per agent in the
            environment.
        rewards : object
            the joint rewards containing one reward per agent in the
            environment.
        done : bool
            whether the episode has ended, in which case further step() calls
            will return undefined results
        info : dict
            contains auxiliary diagnostic information (helpful for debugging)

        """

    @abc.abstractmethod
    def reset(self, *, seed: Optional[int] = None) -> M.JointObservation:
        """Reset the environment returns the initial observations.

        Arguments
        ---------
        seed : int, optional
            RNG seed (default=None)

        Returns
        -------
        observations : object
            the joint observation containing one observation per agent in the
            environment

        """

    @abc.abstractmethod
    def render(self, mode: str = "human") -> None:
        """Render the environment.

        The set of supported modes varies per environment.

        Arguments
        ---------
        mode : str, optional
            the mode to render with (default='human')

        """

    def close(self) -> None:
        """Close environment and perform any necessary cleanup.

        Should be overriden in subclasses as necessary.
        """

    @property
    @abc.abstractmethod
    def model(self) -> M.POSGModel:
        """Get the model for this environment."""

    @property
    def n_agents(self) -> int:
        """Get the number of agents in this environment."""
        return self.model.n_agents

    @property
    def action_spaces(self) -> Tuple[spaces.Space, ...]:
        """Get the action space for each agent."""
        return self.model.action_spaces

    @property
    def obs_spaces(self) -> Tuple[spaces.Space, ...]:
        """Get the observation space for each agent."""
        return self.model.obs_spaces

    @property
    def reward_ranges(self) -> Tuple[Tuple[M.Reward, M.Reward], ...]:
        """The minimum and maximum  possible rewards for each agent."""
        return self.model.reward_ranges

    @property
    def unwrapped(self) -> 'Env':
        """Completely unwrap this env.

        Returns
        -------
        env: posggym.Env
            The base non-wrapped posggym.Env instance

        """
        return self

    def __str__(self):
        return f"<{type(self).__name__} instance>"

    def __enter__(self):
        """Support with-statement for the environment."""
        return self

    def __exit__(self, *args):
        """Support with-statement for the environment."""
        self.close()
        # propagate exception
        return False


class Wrapper(Env):
    """Wraps the environment to allow a modular transformation.

    This class is the base class for all wrappers. The subclass could override
    some methods to change the bahavior of the original environment without
    touching the original code.

    Don't forget to call ``super().__init__(env)`` if the subclass overrides
    the `__init__` method.
    """

    def __init__(self, env: Env):
        self.env = env

        self._action_spaces: Optional[Tuple[spaces.Space, ...]] = None
        self._obs_spaces: Optional[Tuple[spaces.Space, ...]] = None
        self._reward_ranges: Optional[
            Tuple[Tuple[M.Reward, M.Reward], ...]
        ] = None
        self._metadata: Optional[Dict] = None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(
                f"attempted to get missing private attribute '{name}'"
            )
        return getattr(self.env, name)

    @classmethod
    def class_name(cls):
        """Get the name of the wrapper class."""
        return cls.__name__

    @property
    def model(self) -> M.POSGModel:
        return self.env.model

    @property
    def n_agents(self) -> int:
        return self.env.n_agents

    @property
    def action_spaces(self) -> Tuple[spaces.Space, ...]:
        if self._action_spaces is None:
            return self.env.action_spaces
        return self._action_spaces

    @action_spaces.setter
    def action_spaces(self, action_spaces: Tuple[spaces.Space, ...]):
        self._action_spaces = action_spaces

    @property
    def obs_spaces(self) -> Tuple[spaces.Space, ...]:
        if self._obs_spaces is None:
            return self.env.obs_spaces
        return self._obs_spaces

    @obs_spaces.setter
    def obs_spaces(self, obs_spaces: Tuple[spaces.Space, ...]):
        self._obs_spaces = obs_spaces

    @property
    def reward_ranges(self) -> Tuple[Tuple[M.Reward, M.Reward], ...]:
        if self._reward_ranges is None:
            return self.env.reward_ranges
        return self._reward_ranges

    @property                      # type: ignore
    def metadata(self) -> Dict:    # type: ignore
        """Get wrapper metadata."""
        if self._metadata is None:
            return self.env.metadata
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    def step(self,
             actions: Tuple[M.Action, ...]
             ) -> Tuple[M.JointObservation, M.JointReward, bool, Dict]:
        return self.env.step(actions)

    # pylint: disable=[arguments-differ]
    def reset(self, **kwargs) -> M.JointObservation:    # type: ignore
        return self.env.reset(**kwargs)

    def render(self, mode="human"):
        return self.env.render(mode)

    def close(self):
        return self.env.close()

    @property
    def unwrapped(self) -> Env:
        return self.env.unwrapped

    def __str__(self):
        return f"<{type(self).__name__}{self.env}>"

    def __repr__(self):
        return str(self)


class ObservationWrapper(Wrapper):
    """Wraps environment to allow modular transformations of observations.

    Subclasses should atleast implement the observations function.
    """

    def reset(self, **kwargs):
        observations = self.env.reset(**kwargs)
        return self.observations(observations)

    def step(self, actions):
        observations, reward, done, info = self.env.step(actions)
        return self.observations(observations), reward, done, info

    @abc.abstractmethod
    def observations(self, observations):
        """Transforms observations recieved from wrapped environment."""
        raise NotImplementedError


class RewardWrapper(Wrapper):
    """Wraps environment to allow modular transformations of rewards.

    Subclasses should atleast implement the rewards function.
    """

    def reset(self, **kwargs):
        return self.env.reset(**kwargs)

    def step(self, actions):
        observations, reward, done, info = self.env.step(actions)
        return observations, self.rewards(reward), done, info

    @abc.abstractmethod
    def rewards(self, rewards):
        """Transforms rewards recieved from wrapped environment."""
        raise NotImplementedError


class ActionWrapper(Wrapper):
    """Wraps environment to allow modular transformations of actions.

    Subclasses should atleast implement the actions and reverse_actions
    functions.
    """

    def reset(self, **kwargs):
        return self.env.reset(**kwargs)

    def step(self, actions):
        return self.env.step(self.actions(actions))

    @abc.abstractmethod
    def actions(self, action):
        """Transform actions for wrapped environment."""
        raise NotImplementedError

    @abc.abstractmethod
    def reverse_actions(self, actions):
        """Revers transformation of actions."""
        raise NotImplementedError
