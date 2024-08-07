import time

import gym
from enum import Enum
from random import Random
import numpy as np
import os
import subprocess


class RoboTaxiEnv(gym.Env):

    def __init__(self, config={}):
        """
        Creates RoboTaxi game environment from config dictionary
        :param config: Game configurations dict
        """
        super(RoboTaxiEnv, self).__init__()

        self.random = None  # Set in self.seed()
        self.np_random = None  # Set in self.seed()
        self.map = None  # Set in reset()

        # Game parameters
        self.map_size = config.get('map_size', (12, 12))
        self.max_steps = config.get('max_steps', 1000)
        self.num_bombs = config.get('num_bombs', 3)
        self.rng_seed = config.get('rng_seed', None)
        self.initial_avoidance_dist = config.get('initial_avoidance_dist', 3)
        self.seed(self.rng_seed)
        self.rewards = config.get('rewards', dict(bomb=-20, acorn=10, delivered=50, wall=0, max_steps_exceeded=0, ts=0))
        self.randomize_map = config.get('randomize_map', True)
        self.explore_after_n = config.get('explore_after_n', 3)

        self.rerandomize_player_start = config.get('rerandomize_player_start', False)

        if not self.randomize_map:
            assert ('preset_map' in config)
            assert ('preset_player_orientation' in config)
            assert ('preset_player_location' in config)
            self.preset_map = config['preset_map']
            self.preset_player_orientation = config['preset_player_orientation']
            self.preset_player_location = config['preset_player_location']

        # RL parameters
        self.action_space = gym.spaces.Discrete(len(Action))
        self.observation_space = gym.spaces.Tuple((gym.spaces.Box(low=0, high=(len(CellType) - 1), shape=self.map_size,
                                                                  seed=self.rng_seed),
                                                   gym.spaces.Box(low=np.asarray((0, 0), dtype=np.int),
                                                                  high=np.asarray(self.map_size, dtype=np.int),
                                                                  shape=(2,),
                                                                  seed=self.rng_seed),
                                                   gym.spaces.Discrete(2,
                                                                       seed=self.rng_seed)
                                                   ))  # (map, player_loc, has_acorn)

        # Game state
        self.player_loc = None  # In (x, y) NOT (row, col)!
        self.player_orientation = None
        self.has_acorn = False
        self.ts = 0
        self.cumulative_reward = 0
        self.last_n_actions = [Action.NOP.value] * self.explore_after_n

    def step(self, action):
        print("entering step function")
        timestep_reward = 0
        timestep_reward += self.rewards['ts']
        done = False
        endRound = False

        # Process inputs

        # Add action onto last n state history
        self.last_n_actions.append(action)
        self.last_n_actions.pop(0)

        # Get last non-NOP state if within n steps
        if action == Action.NOP.value:
            for last_act in self.last_n_actions:
                if last_act != Action.NOP.value:
                    action = last_act
        
        proposed_orientation = None
        proposed_player_loc = np.zeros(2)
        if action == Action.UP.value:
            proposed_orientation = Direction.UP
        elif action == Action.DOWN.value:
            proposed_orientation = Direction.DOWN
        elif action == Action.LEFT.value:
            proposed_orientation = Direction.LEFT
        elif action == Action.RIGHT.value:
            proposed_orientation = Direction.RIGHT
        elif action == Action.NOP.value:
            proposed_orientation = self.random.choice(list(Direction))
            #print((f"I am in the else statement"))
            #proposed_orientation = Direction.STILL
 
        else:
            raise ValueError("Invalid Action passed to step(): ", action)

        proposed_player_loc = move_in_direction(self.player_loc, proposed_orientation)

        # Check collisions
        # -----------------

        # Collision with wall
        if self.map[loc2tuple(proposed_player_loc)] == CellType.WALLS.value:
            print("Hit wall")
            timestep_reward += self.rewards['wall']
            map_center_loc = ((self.map_size[0] - 1) / 2, (self.map_size[1] - 1) / 2)

            # Player doesn't move
            proposed_player_loc = self.player_loc

            # Hit wall while moving vertically
            if proposed_orientation == Direction.UP or proposed_orientation == Direction.DOWN:
                print("Hit wall move vertically")
                # If to the left of the center
                if proposed_player_loc[0] <= map_center_loc[0]:
                    # Turn right
                    proposed_orientation = Direction.RIGHT
                else:  # If to the right of center
                    # Turn left
                    proposed_orientation = Direction.LEFT

            # Hit wall while moving horizontally
            else:
                print("Hit wall move horizontally")
                # If above the center
                if proposed_player_loc[1] <= map_center_loc[1]:
                    # Turn down
                    proposed_orientation = Direction.DOWN
                else:  # If below the center
                    # Turn up
                    proposed_orientation = Direction.UP

        # Collision with bomb
        if self.map[loc2tuple(proposed_player_loc)] == CellType.BOMB.value:
            timestep_reward += self.rewards['bomb']
            self.map[loc2tuple(proposed_player_loc)] = CellType.BLANK.value
            done = True

        # Collision with acorn
        if self.map[loc2tuple(proposed_player_loc)] == CellType.ACORN.value:
            timestep_reward += self.rewards['acorn']
            self.map[loc2tuple(proposed_player_loc)] = CellType.BLANK.value
            self.has_acorn = True

        # Collision with squirrel
        if self.map[loc2tuple(proposed_player_loc)] == CellType.SQUIRREL.value:
            if self.has_acorn:
                timestep_reward += self.rewards['delivered']
                self.map[loc2tuple(proposed_player_loc)] = CellType.BLANK.value
                done = True
                endRound = True

        # Update
        # self.map[loc2tuple(self.player_loc)] = CellType.BLANK.value  # Clear previous location

        self.player_loc = proposed_player_loc
        self.player_orientation = proposed_orientation
        print("XXXXXXXXXXXXXXX")
        print("Step function")
        print(f"new: {self.player_loc}")
        print("XXXXXXXXXXXXXXX")

        # Don't overwrite map since taxi can overlap squirrel (writing to map would delete squirrel)
        # self.map[loc2tuple(self.player_loc)] = CellType.TAXI.value  # Set new location

        if self.ts >= self.max_steps:
            timestep_reward += self.rewards['max_steps_exceeded']
            done = True
            endRound = True

        self.ts += 1
        self.cumulative_reward += timestep_reward

        # obs, rew, done, info
        return (self.map.copy(), self.player_loc, self.has_acorn), timestep_reward, done, dict(
            map=self.map.copy(), player_location=self.player_loc,
            player_orientation=self.player_orientation.value,
            timestep_reward=timestep_reward, ts=self.ts, cumulative_reward=self.cumulative_reward,
            has_acorn=self.has_acorn, endRound=endRound)

    def reset(self):
        """
        Randomize the map state
        :return: First observation
        """
        # Reset states
        self.has_acorn = False
        self.player_orientation = None
        self.player_loc = None
        self.ts = 0
        self.cumulative_reward = 0

        if self.randomize_map:
            meets_criteria = False

            while not meets_criteria:  # Note this is a quick fix to make sure game elements are at least one move away from each other
                # Create the walls
                self.map = np.ones(self.map_size, dtype=np.intc) * CellType.WALLS.value

                # Empty the inside
                self.map[1:-1, 1:-1] = np.ones((self.map_size[0] - 2, self.map_size[1] - 2)) * CellType.BLANK.value

                # Place robotaxi
                player_loc = self.np_random.integers(low=(1, 1), high=(self.map_size[1] - 1, self.map_size[0] - 1))
                self.player_loc = (
                int(player_loc[0]), int(player_loc[1]))  # Ensure dtype is int not numpy to be able to JSONify

                # Pick starting direction
                possible_Orientations = []
                if not (self.player_loc[0] < self.initial_avoidance_dist):
                    possible_Orientations.append(Direction.LEFT)
                if not ((self.map_size[1] - 1) - self.player_loc[0] < self.initial_avoidance_dist):
                    possible_Orientations.append(Direction.RIGHT)
                if not (self.player_loc[0] < self.initial_avoidance_dist):
                    possible_Orientations.append(Direction.UP)
                if not ((self.map_size[0] - 1) - self.player_loc[1] < self.initial_avoidance_dist):
                    possible_Orientations.append(Direction.DOWN)

                self.player_orientation = self.random.choice(possible_Orientations)

                # Find all open spaces
                open_locs = set()
                for r in range(self.map.shape[0]):
                    for c in range(self.map.shape[1]):
                        if self.map[r, c] == CellType.BLANK.value and not (
                                self.player_loc[0] == c and self.player_loc[1] == r):
                            open_locs.add((r, c))

                # Mask out spaces within collision distance of player
                for step in range(1, self.initial_avoidance_dist + 1):
                    open_locs.discard((self.player_loc[1] + (self.player_orientation.value[1] * step),
                                       self.player_loc[0] + (self.player_orientation.value[0] * step)))

                # Place squirrel and acorn
                squirrel_loc = self.random.choice(list(open_locs))
                open_locs.remove(squirrel_loc)
                self.map[tuple(squirrel_loc)] = CellType.SQUIRREL.value

                acorn_loc = self.random.choice(list(open_locs))
                open_locs.remove(acorn_loc)
                self.map[tuple(acorn_loc)] = CellType.ACORN.value

                # Place bombs in remaining locations
                for i in range(self.num_bombs):
                    bomb_loc = self.random.choice(list(open_locs))
                    open_locs.remove(bomb_loc)
                    self.map[tuple(bomb_loc)] = CellType.BOMB.value

                # Check criteria
                element_rcs = []
                for r in range(1, self.map.shape[0]-1):  # Avoid borders
                    for c in range(1, self.map.shape[1]-1):  # Avoid borders
                        if not (self.map[r, c] == CellType.BLANK.value):
                            element_rcs.append((r, c))

                found_issue = False
                for i in range(len(element_rcs)):
                    for j in range(len(element_rcs)):
                        if i == j:
                            continue
                        if abs(element_rcs[i][0] - element_rcs[j][0]) +  abs(element_rcs[i][1] - element_rcs[j][1]) < 4:
                            found_issue = True
                            break
                    if found_issue:
                        break

                if not found_issue:
                    meets_criteria = True

                # found_issue = False
                # for el_rc in element_rcs:
                #
                #     if (el_rc[0] - 1, el_rc[1]) in element_rcs or (el_rc[0] + 1, el_rc[1]) in element_rcs or (el_rc[0], el_rc[1] - 1) in element_rcs or (el_rc[0], el_rc[1] + 1) in element_rcs:
                #         found_issue = True
                #         break
                # if not found_issue:
                #     meets_criteria = True


            # Rerandomize player start
            if self.rerandomize_player_start:
                rerandomizer_seed = time.time()
                rereandomizer_random = Random(rerandomizer_seed)

                # First, list all open spaces, find bombs
                open_locs = set()
                bombs_rc = []
                for r in range(self.map.shape[0]):
                    for c in range(self.map.shape[1]):
                        if self.map[r, c] == CellType.BLANK.value:
                            open_locs.add((r, c))
                        elif self.map[r, c] == CellType.BOMB.value:
                            bombs_rc.append((r, c))

                # Choose player direction
                self.player_orientation = rereandomizer_random.choice([orient for orient in Direction])

                # Mask out areas from bomb, wall
                for bomb in bombs_rc:
                    for step in range(1, self.initial_avoidance_dist + 1):
                        # Looking back from bomb to player
                        open_locs.discard((bomb[0] - (self.player_orientation.value[1] * step),
                                           bomb[1] - (self.player_orientation.value[0] * step)))

                # Choose player location
                self.player_loc = rereandomizer_random.choice(list(open_locs))[::-1]

        else:  # Load preset map
            self.map = np.asarray(self.preset_map)
            self.player_orientation = Direction(tuple(self.preset_player_orientation))
            self.player_loc = tuple(self.preset_player_location)

        # obs, info
        return (self.map.copy(), self.player_loc, self.has_acorn), dict(map=self.map.copy(),
                                                                        player_location=self.player_loc,
                                                                        player_orientation=self.player_orientation.value,
                                                                        timestep_reward=None,
                                                                        ts=self.ts,
                                                                        cumulative_reward=self.cumulative_reward,
                                                                        has_acorn=self.has_acorn,
                                                                        endRound=False)

    def render(self, mode="human"):
        if mode == "human":
            str_map = [["."] * self.map.shape[1] for i in range(self.map.shape[0])]

            for r in range(self.map.shape[0]):
                for c in range(self.map.shape[1]):
                    if self.map[(r, c)] == CellType.BLANK.value:
                        str_map[r][c] = '.'
                    elif self.map[(r, c)] == CellType.WALLS.value:
                        str_map[r][c] = '#'
                    elif self.map[(r, c)] == CellType.BOMB.value:
                        str_map[r][c] = 'B'
                    elif self.map[(r, c)] == CellType.ACORN.value:
                        str_map[r][c] = 'A'
                    elif self.map[(r, c)] == CellType.SQUIRREL.value:
                        str_map[r][c] = 'S'

            str_map[self.player_loc[1]][self.player_loc[0]] = 'R'

            # Display the info
            clear()

            print("Map:")
            for row in str_map:
                print(row)

            print(f"Player Location: {self.player_loc}")
            print(f"Player Orientation: {self.player_orientation}")

    def seed(self, seed=None):
        if seed:
            self.random = Random(seed)
            self.np_random = np.random.default_rng(seed)
        else:
            self.random = Random()
            self.np_random = np.random.default_rng()

    def close(self):
        pass


def loc2tuple(loc):
    """
    Converts from (x, y) coordinates to (row, col)
    :param loc: (x, y) coordinate
    :return: (row, col) coordinate
    """
    return tuple(loc)[::-1]


def move_in_direction(loc, direction):
    print("########################")
    print("move in direction function")
    print(f"loc: {loc}")
    print(f"direction: {direction.value}")
    print(loc[0] + direction.value[0], loc[1] + direction.value[1])
    print("########################")
    return loc[0] + direction.value[0], loc[1] + direction.value[1]


def clear():
    subprocess.call('cls||clear', shell=True)


class CellType(Enum):
    BLANK = 0
    WALLS = 1
    BOMB = 2
    ACORN = 3
    SQUIRREL = 4


class Direction(Enum):
    # In (x, y) format NOT (row, col)
    #STILL = (0, 0)
    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
    LEFT = (-1, 0)


Int2Direction = {
    0: Direction.UP,
    1: Direction.RIGHT,
    2: Direction.DOWN,
    3: Direction.LEFT
}
Direction2Int = {
    Direction.UP: 0,
    Direction.RIGHT: 1,
    Direction.DOWN: 2,
    Direction.LEFT: 3
}


class Action(Enum):
    NOP = 0
    UP = 1
    RIGHT = 2
    DOWN = 3
    LEFT = 4


if __name__ == '__main__':
    config = {'rng_seed': 42}
    env = RoboTaxiEnv(config=config)
    env.reset()
    print(env.map)
    print(env.player_orientation)
