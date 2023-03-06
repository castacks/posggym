"""The Predator-Prey Grid World Environment.

A co-operative 2D grid world problem involving multiple predator agents working together
to catch prey agents in the environment.

Reference
---------
- Ming Tan. 1993. Multi-Agent Reinforcement Learning: Independent vs. Cooperative Agents
  In Proceedings of the Tenth International Conference on Machine Learning. 330–337.
- J. Z. Leibo, V. F. Zambaldi, M. Lanctot, J. Marecki, and T. Graepel. 2017. Multi-Agent
  Reinforcement Learning in Sequential Social Dilemmas. In AAMAS, Vol. 16. ACM, 464–473

"""
import math
from itertools import product
from typing import (
    Dict,
    List,
    NamedTuple,
    Optional,
    SupportsFloat,
    Tuple,
)
import numpy as np

from gymnasium import spaces

import posggym.envs.grid_world.render as render_lib
import posggym.model as M
from posggym.core import DefaultEnv
from posggym.envs.continous.core import ContinousWorld, Object, Position
from posggym.utils import seeding
import math
class PPState(NamedTuple):
    """A state in the Predator-Prey Environment."""
    predator_coords: Tuple[Position, ...]
    prev_predator_coords: Tuple[Position, ...]
    prey_coords: Position
    prev_prey_coords : Position


# Actions
PPAction = float

PREY = 0
PREDATOR = 1
AGENT_TYPE = [PREDATOR, PREY] 


# Observations
# Obs = (adj_obs)
PPObs = Tuple[float, ...]
# Cell Obs

collision_distance = 1

class PPContinousEnv(DefaultEnv[PPState, PPObs, PPAction]):


    metadata = {
        "render_modes": ["human"],
        "render_fps": 4,
    }

    def __init__(
        self,
        num_predators: int,
        num_prey: int,
        cooperative: bool,
        prey_strength: int,
        obs_dim: int,
        render_mode: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            PPModel(
                num_predators,
                num_prey,
                cooperative,
                prey_strength,
                obs_dim,
                **kwargs,
            ),
            render_mode=render_mode,
        )
        self._obs_dim = obs_dim
        self._viewer = None
        self._renderer: Optional[render_lib.GWContinousRender] = None
        self.render_mode = render_mode

    def render(self):
        if self.render_mode == "human":
            import posggym.envs.continous.render as render_lib

            if self._renderer is None:
                self._renderer = render_lib.GWContinousRender(
                    self.render_mode,
                    self.model.grid,
                    render_fps=self.metadata["render_fps"],
                    env_name="PredatorPreyContinous",
                    domain_size=self.model.grid.width,
                    num_colors=3
                )
            colored_pred =  tuple(t + (0,) for t in self._state.predator_coords)
            colored_prey =  tuple(t + (1 + caught,) for t, caught in zip(self._state.prey_coords, self.state.prey_caught))

            self._renderer.render(colored_prey + colored_pred)


   
class PPModel(M.POSGModel[PPState, PPObs, PPAction]):
    """Predator-Prey Problem Model.

    Parameters
    ----------
    size : int
        the size of the grid (height and width)
    num_predators : int
        the number of predator (and thus controlled agents)
    num_prey : int
        the number of prey
    cooperative : bool
        whether environment rewards are fully shared (True) or only awarded to
        capturing predators (i.e. mixed) (False)
    prey_strenth : int
        the minimum number of predators needed to capture a prey
    obs_dims : int
        number of cells in each direction around the agent that the agent can
        observe

    """

    R_MAX = 1.0
    PREY_CAUGHT_COORD = (0, 0)

    def __init__(
        self,
        # grid: Union[str, "PPGrid"],
        num_agents: int,
        n_communicating_purusers : int,
        velocity_control : bool = False,
        use_curriculum : bool = False
        **kwargs,
    ):
        assert 1 < num_agents <= 8


        self.n_pursuers = num_agents

        self.vel_pur = 10
        self.vel_tar = 20
        self.omega_max_pur = math.pi / 10
        self.omega_max_tar = math.pi / 10


        self.obs_each_pursuer_evader = 2
        self.obs_self_evader = 3

        self.obs_each_pursuer_pursuer = 2
        self.obs_self_pursuer = 6

        self.obs_self = self.obs_self_pursuer
        self.obs_pursuer = self.obs_each_pursuer_pursuer

        self.velocity_control = False
        self.n_pursuers_com = n_communicating_purusers
        self.arena_dim_square = 1000


        ACT_DIM =2 if self.velocity_control else 1

        OBS_DIM = (
            self.obs_self_pursuer
            + (self.n_pursuers_com - 1) * self.obs_each_pursuer_pursuer
        )

        self.cap_rad = 60

        high = np.ones((self.n_pursuers, OBS_DIM), dtype=np.float64) * np.inf
        acthigh = np.array(
            [1] * ACT_DIM
        )  # useful range is -1 .. +1, but spikes can be higher

        self.observation_space = spaces.Box(-high, high, dtype=np.float64)

        self.action_space = (
          spaces.Box(-acthigh, acthigh, dtype=np.float32)
        )

        self.grid = PPWorld(grid_size=6, block_coords=None)


    def get_agents(self, state: PPState) -> List[M.AgentID]:
        return list(self.possible_agents)


    def get_observation(self, state : PPState):
        # Get observation for all pursuers

        observation = []
        
        for i in range(self.n_pursuers):

            target = state.prey_coords
            

            """ getting the target engagement """
            alpha_t, _, dist_t, Xit, Yit = self.engagmment(state.predator_coords[i], state.predator_coords[j], dist_factor=self.arena_dim_square)
            
            yaw = state.predator_coords[i][2]
            alpha_t_prev, _, dist_t_prev, Xit_prev, Yit_prev = self.engagmment(state.prev_predator_coords[i], state.prev_prey_coords, dist_factor=self.arena_dim_square)

            engagment = []

            """ getting the relative engagement """
            for j in range(self.n_pursuers):
                if j != i:
                    eng = self. engagmment(state.predator_coords[i], state.predator_coords[j], 
                        dist_factor=self.arena_dim_square,
                    )
                    engagment.append(eng)

            engagment = sorted(engagment, key=lambda x: x[2])
            alphas, _, dists, Xs, Ys = list(zip(*engagment))

           
            # change in alpha
            alpha_rate = alpha_t - alpha_t_prev
            alpha_rate = math.asin(math.sin(alpha_rate)) / 4

            # change in distance
            dist_rate = (dist_t - dist_t_prev) / 0.03

            # yaw + yaw rate
            north = -state.predator_coords[i][2] / math.pi
            north_prev = -state.prev_predator_coords[i][2] / math.pi
            turn_rate = (north - north_prev) / 2

            # normalise the alpha
            alpha_t = alpha_t / math.pi

            temp_observation = [
                alpha_t,
                dist_t,
                north,
                alpha_rate,
                dist_rate,
                turn_rate,
            ]

            # alpha and distance to each pursuer
            for index in range(self.n_pursuers_com - 1):
                temp_observation.append(alphas[index] / math.pi)
                temp_observation.append(dists[index])

            observation.append(temp_observation)

        observation = np.array(observation)

        return observation



    def sample_initial_state(self) -> PPState:

        assert self.grid.prey_start_coords is not None

        predator_coords = []
        for i in range(self.n_pursuers):
                x = 50 * (-math.floor(self.n_pursuers / 2) + i)  # distributes the agents based in their number
                predator_coords.append([50, 0, 0])


        x=random.randint(-300, 300),
        y=random.randint(100, 300)

        self.pursuer_vel=random.randint(0, self.vel_tar),

        prey_coords = (x,y,0)

        return PPState(tuple(predator_coords), prey_coordss)

    def sample_initial_obs(self, state: PPState) -> Dict[M.AgentID, PPObs]:
        # print(state, state)
        return self._get_obs(state, state)
    def step(
        self, state: PPState, actions: Dict[M.AgentID, PPAction]
    ) -> M.JointTimestep[PPState, PPObs]:

        next_state = self._get_next_state(state, actions)
        obs = self._get_obs(state, next_state)
        rewards = self._get_rewards(state, next_state)

        # print(rewards)

        all_done = all(next_state.prey_caught)
        truncated = {i: False for i in self.possible_agents}
        terminated = {i: all_done for i in self.possible_agents}

        info: Dict[M.AgentID, Dict] = {i: {} for i in self.possible_agents}
        if all_done:
            for i in self.possible_agents:
                info[i]["outcome"] = M.Outcome.WIN

        return M.JointTimestep(
            next_state, obs, rewards, terminated, truncated, all_done, info
        )
        def abs_sum(self, vector):
        return sum(map(abs, vector))
    def _get_obs(self, state):

    def engagmment(self, agent_i : Position, agent_j : Position, dist_factor : float):
        dist = np.linalg.norm([agent_i[0] - agent_j[0], agent_i[1] - agent_j[1]])

        yaw = agent_i[2]

        R = np.array(
            [[math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]]
        )

        T_p =np.array([agent_i[0] - agent_j[0], agent_i[1] - agent_j[1]])
        Los_angle = math.atan2(T_p[1], T_p[0])
        T_p = R.dot(T_p)
        alpha = math.atan2(T_p[1], T_p[0])

        return (
            alpha,
            Los_angle,
            dist / dist_factor,
            T_p[0] / dist_factor,
            T_p[1] / dist_factor,
        )

        
    def scale_vector(self, vector, scale, final_vector, factor=1.0):
        div = self.abs_sum(vector)
        if div < 0.00001:
            div = 0.00001
        f = -factor * scale(self.abs_sum(vector)) / div
        vector = f * vector
        return list(map(lambda x, y: x + y, final_vector, vector))

    def target_move_repulsive(self, position : Position, state : PPState):
        xy_pos = np.array(position[:2])
        x,y = xy_pos

        scale = lambda x: 50000 / (abs(x) + 200) ** 2
        n_pursuer = len(state.predator_coords)
        final_vector = (0.0, 0.0)

        for i in state.predator_coords:
            vector = np.array(i[:2]) - xy_pos
            final_vector = self.scale_vector(vector, scale, final_vector)

        # Find closest point !!!! then put it in to the vectorial sum

        self.r_arena = 430
        r_wall = self.r_arena
        # r = numpy.linalg.norm([self.y, self.x])
        gamma = math.atan2(y, x)

        # if r > r_wall*0.0:
        virtual_wall = [r_wall * math.cos(gamma), r_wall * math.sin(gamma)]
        vector = virtual_wall - xy_pos
        final_vector = self.scale_vector(vector, scale, final_vector, 0.5 * n_pursuer)

        self.enemy_speed = 1
        scaled_move_dir = [
            self.enemy_speed * i / self.abs_sum(final_vector) for i in final_vector
        ]

        return scaled_move_dir[0], scaled_move_dir[1]


    @property
    def reward_ranges(self) -> Dict[M.AgentID, Tuple[SupportsFloat, SupportsFloat]]:
        return {i: (0.0, self.R_MAX) for i in self.possible_agents}

    @property
    def rng(self) -> seeding.RNG:
        if self._rng is None:
            self._rng, seed = seeding.std_random()
        return self._rng

import random
class PPWorld(ContinousWorld):
    """A grid for the Predator-Prey Problem."""

    def __init__(
        self,
        grid_size: int,
        block_coords: Optional[List[Object]],
        predator_start_coords: Optional[List[Position]] = None,
        prey_start_coords: Optional[List[Position]] = None,
        predator_angles: Optional[List[float]] = None,
    ):
        assert grid_size >= 3
        super().__init__(grid_size, grid_size, block_coords)
        self.size = grid_size
        # predators start in corners or half-way along a side
        if predator_start_coords is None:
            predator_start_coords_ : List[Tuple[float, float]] = list(
                (float(c[0]), float(c[1]))  # type: ignore
                for c in product([0, grid_size // 2, grid_size - 1], repeat=2)
                if c[0] in (0, grid_size - 1) or c[1] in (0, grid_size - 1)
            )
            predator_angles = [random.random() * math.pi for _ in range(len(predator_start_coords_))]

            predator_start_coords = [x + (y,) for x,y in zip(predator_start_coords_, predator_angles)]

        self.predator_start_coords = predator_start_coords
        self.prey_start_coords = prey_start_coords


    def get_unblocked_center_coords(self, num: int) -> List[Position]:
        """Get at least num closest coords to the center of grid.

        May return more than num, since can be more than one coord at equal
        distance from the center.
        """
        # assert num < self.n_coords - len(self.block_coords)
        center = (self.width / 2, self.height / 2, 0)
        min_dist_from_center = math.ceil(math.sqrt(num)) - 1

        coords = [self.sample_coords_within_dist(center, min_dist_from_center, ignore_blocks=False) for _ in range(num)]

        return coords
    

