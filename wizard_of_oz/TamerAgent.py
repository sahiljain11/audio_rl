# Implementation inspired by https://github.com/benibienz/TAMER/tree/master

import datetime
import pickle
import time
from itertools import count
from pathlib import Path
from sys import stdout
from csv import DictWriter
from scipy.stats import gamma
from scipy.stats import uniform
from scipy.integrate import quad
from loguru import logger
import os
import json
from torch import nn
import torch.nn.functional as F
from torch import optim
from ProsodyHandler import *
import itertools
import librosa

import numpy as np
from sklearn import pipeline, preprocessing
from sklearn.kernel_approximation import RBFSampler
from sklearn.linear_model import SGDRegressor
from collections import deque
import torch
import random



LAKE_ACTION_MAP = {0: 'left', 1: 'down', 2: 'right', 3: 'up'}
MODELS_DIR = Path(__file__).parents[1].joinpath('saved_models')
LOGS_DIR = Path(__file__).parents[1].joinpath('logs')
sleep_time = 2.2

class InteractiveAgent():
    """
    Agent for getting the interactive human reward.
     Human reward is based on binary feedback.
    """

    def __init__(self, audio_dict, baseline_audio_file, delay=0.4, baseline_agent=True):
        self.human_reward_time = time.time()
        self.audio_dict = audio_dict
        self.baseline_audio, self.baseline_sr = librosa.load(baseline_audio_file, sr=None)
        self.baseline_dict = self._fill_baseline_dict(self.baseline_audio)
        self.feedback_overview = {"yes": 0, "no": 0, "total": 0}
        self.delay = delay
        self.baseline_agent = baseline_agent

    def get_no_ratio(self):
        return self.feedback_overview["no"] / self.feedback_overview["total"]

    def _fill_baseline_dict(self, audio) -> dict:
        """
        Fills the baseline dictionary with the prosody measures.
        :param audio: audio array.
        :return: Dictionary with prosody rules.
        """
        return {
            "loudness": {"mean": np.mean(ProsodyHandler.loudness_raw(audio)).item(),
                         "std": np.std(ProsodyHandler.loudness_raw(audio)).item()},
            "pitch": {"mean": np.mean(ProsodyHandler.pitch_raw(audio)).item(),
                      "std": np.std(ProsodyHandler.pitch_raw(audio)).item()},
            "energy": {"mean": np.mean(ProsodyHandler.energy_raw(audio)).item(),
                       "std": np.std(ProsodyHandler.energy_raw(audio)).item()}
        }

    def get_human_reward(self, info) -> tuple:
        """
        Checks whether new human input was generated and
        gives corresponding human reward.
        """
        human_reward = [0]
        reward_obtained = []
        # robot log ts
        robot_start_ts = info[0]
        robot_end_ts = info[1]

        potential_feedback = []
        # human audio ts
        audio_ts = list(self.audio_dict.keys())
        # audio_ts tuple: (word, audio chunk)
        for word in audio_ts:
            word_start = word[0]
            word_end = word[1]
            feedback_word, audio_chunk = self.audio_dict[word]

            if (robot_start_ts >= word_start and robot_start_ts <= word_end) or (robot_end_ts <= word_end and robot_end_ts >= word_start) or (word_start >= robot_start_ts and word_start <= robot_end_ts) or (word_end >= robot_start_ts and word_end <= robot_end_ts):
                # the word
                potential_feedback.append((feedback_word, audio_chunk))
                reward_obtained.append((word_start, word_end))

        if potential_feedback:
            if self.baseline_agent:
                human_reward = self.determine_human_reward_baseline(potential_feedback)
            
            else:
                human_reward = self.determine_human_reward_prosody(potential_feedback)

        return human_reward, reward_obtained

    def determine_human_reward_prosody(self, feedback_list) -> list:
        """
        Determines human reward based on human input.
        :param feedback_list: list containing info about text
        and prosody.
        :returns a human reward integer.
        """
        reward = []

        for feedback in feedback_list:
            word = feedback[0]
            audio_vector = feedback[1]
            z_loudness, z_pitch, z_energy = self.get_features(audio_vector)

            if word == "yes":
                loudness_value = 1 if np.isnan(z_loudness) else 1 + z_loudness
                pitch_value = 1 if np.isnan(z_pitch) else 1 + z_pitch
                energy_value = 1 if np.isnan(z_energy) else 1 + z_energy
                value = (loudness_value + pitch_value + energy_value)/3
                reward.append(value)

            elif word == "no":
                loudness_value = -1 if np.isnan(z_loudness) else -1 - z_loudness
                pitch_value = -1 if np.isnan(z_pitch) else -1 - z_pitch
                energy_value = -1 if np.isnan(z_energy) else -1 - z_energy
                value = (loudness_value + pitch_value + energy_value)/3
                reward.append(value)

        return reward

    def get_features(self, audio_vector):
        # loudness
        z_loudness = (ProsodyHandler.mean_loudness(audio_vector) - self.baseline_dict["loudness"]["mean"]) / \
                     self.baseline_dict["loudness"]["std"]
        # pitch
        z_pitch = (ProsodyHandler.mean_pitch(audio_vector) - self.baseline_dict["pitch"]["mean"]) / \
                  self.baseline_dict["pitch"]["std"]
        # energy
        z_energy = (ProsodyHandler.mean_energy(audio_vector) - self.baseline_dict["energy"]["mean"]) / \
                   self.baseline_dict["energy"]["std"]
        return z_loudness, z_pitch, z_energy
    
    def determine_human_reward_baseline(self, feedback_list) -> int:
        """
        Determines human reward based on human input.
        :param data: dictionary containing info about text
        and prosody.
        :returns a human reward integer.
        """
        reward = []

        for feedback in feedback_list:
            word = feedback[0]

            if word == "yes":
                reward.append(1)
            elif word == "no":
                reward.append(-1)

        return reward


class SGDFunctionApproximator:
    """ SGD function approximator with RBF preprocessing. """

    def __init__(self, env):

        # Feature preprocessing: Normalize to zero mean and unit variance
        observation_examples = np.array(
            [env.observation_space.sample() for _ in range(10000)], dtype='float64'
        )
        self.scaler = preprocessing.StandardScaler()
        self.scaler.fit(observation_examples)

        # Used to convert a state to a featurized represenation.
        # RBF kernels with different variances to cover different parts of the space
        self.featurizer = pipeline.FeatureUnion(
            [
                ('rbf1', RBFSampler(gamma=5.0, n_components=100)),
                ('rbf2', RBFSampler(gamma=2.0, n_components=100)),
                ('rbf3', RBFSampler(gamma=1.0, n_components=100)),
                ('rbf4', RBFSampler(gamma=0.5, n_components=100)),
            ]
        )
        self.featurizer.fit(self.scaler.transform(observation_examples))

        self.models = []
        for _ in range(env.action_space.n):
            model = SGDRegressor(learning_rate='constant', eta0=0.01)
            model.partial_fit([self.featurize_state(env.reset())], [0])
            self.models.append(model)

    def predict(self, state, has_acorn, action=None):
        has_acorn = 1 if has_acorn else 0
        features = self.featurize_state(state + [has_acorn])
        if not action:
            return [m.predict([features])[0] for m in self.models]
        else:
            return self.models[action].predict([features])[0]

    def update(self, state, has_acorn, action, td_target):
        has_acorn = 1 if has_acorn else 0
        features = self.featurize_state(state + [has_acorn])
        self.models[action].partial_fit([features], [td_target])

    def featurize_state(self, state):
        """ Returns the featurized representation for a state. """
        if len(state) > 3:
            state = state[:3]
        scaled = self.scaler.transform([state])
        featurized = self.featurizer.transform(scaled)
        return featurized[0]



class QNetwork(nn.Module):

    def __init__(self, input, output, num_hidden=64):
        nn.Module.__init__(self)
        self.l1 = nn.Linear(input, num_hidden)
        #self.l2 = nn.Linear(num_hidden, num_hidden)
        self.l3 = nn.Linear(num_hidden, output)
        self.loss = nn.MSELoss()

    def forward(self, x):
        x = F.relu(self.l1(x))
        #x = F.relu(self.l2(x))
        return self.l3(x)


class HumanRewardApproximator:
    """ NN approximator """
    def __init__(self, env):

        #self.models = []
        self.optimizers = []
        self.env = env
        self.losses = []
        self.loss_epochs = []

        self.model = QNetwork(3, 5)
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.005)

    def predict(self, state, has_acorn, action=None):
        has_acorn_bool = 1 if has_acorn else 0
        features = torch.Tensor([state[0]/self.env.width, state[1]/self.env.height, has_acorn_bool])
        if not action:
            return self.model(features)
        else:
            return self.model(features)[action]

    def update(self, state, has_acorn, action, td_target):
        has_acorn_bool = 1 if has_acorn else 0
        features = torch.Tensor([state[0]/self.env.width, state[1]/self.env.height, has_acorn_bool])
        self.optimizer.zero_grad()
        pred = self.model(features)
        target = pred.clone().detach()
        target[action] = td_target
        loss = self.model.loss(pred, target)
        self.losses.append(loss)
        loss.backward()
        self.optimizer.step()


    def featurize_state(self, state):
        """ Returns the featurized representation for a state. """
        scaled = self.scaler.transform([state])
        featurized = self.featurizer.transform(scaled)
        return featurized[0]

class TamerAgent:
    """
    QLearning Agent adapted to TAMER using steps from:
    http://www.cs.utexas.edu/users/bradknox/kcap09/Knox_and_Stone,_K-CAP_2009.html
    """
    def __init__(
        self,
        env,
        num_episodes,
        InteractiveAgent,
        reinforce_model,
        output_name,
        model_policy_path,
        credit_assignment = False,
        discount_factor=0,
        alpha=1,
        epsilon=0,
        min_eps=0,
        tame=True,
        output_dir=LOGS_DIR,
        model_file_to_load=None
    ):
        self.tame = tame
        self.reinforce_model = reinforce_model
        self.credit_assignment = credit_assignment
        self.ts_history = deque(maxlen=3)
        self.env = env
        self.output_dir = output_dir
        self.InteractiveAgent = InteractiveAgent
        self.cum_rewards = []
        self.model_policy = json.load(open(model_policy_path, 'r'))

        # init model
        if model_file_to_load is not None:
            print(f'Loaded pretrained model: {model_file_to_load}')
            self.load_model(filename=model_file_to_load)
        else:
            if tame:
                self.H = self.reinforce_model(env)  # init H function
            else:  # optionally run as standard Q Learning
                self.Q = self.reinforce_model(env)  # init Q function

        # hyperparameters
        self.discount_factor = discount_factor
        self.epsilon = epsilon if not tame else 0
        self.num_episodes = num_episodes
        self.min_eps = min_eps
        self.alpha = alpha
        self.state_log = []
        self.passive_reward = 0.5
        self.training_fatigue = 1
        self.training_fatigue_decay = 1.0001
        self.human_rewards = []
        p = self.get_policy()
        self.cum_rewards.append(self.evaluate_policy(p, self.model_policy))

        # calculate episodic reduction in epsilon
        self.epsilon_step = (epsilon - min_eps) / num_episodes

        # reward logging
        self.reward_log_columns = [
            'episode',
            'ep_start_ts',
            'state',
            'action',
            'next_state',
            'agent_got_reward_ts',
            'human_reward',
            'actual_human_reward',
            'environment_reward',
            'log_ts'
        ]
        self.reward_log_path = os.path.join(self.output_dir, f'{output_name}.csv')

    def act(self):
        """ 
        Epsilon-greedy Policy .
        """
        return self.env.get_action()

    def integrand(self, x):
        return gamma.pdf(x, 2, loc=0, scale=0.28)

    def credit_prob(self, lower_bound, upper_bound):
        return quad(self.integrand, lower_bound, upper_bound)[0]

    def _train_episode(self, episode_index):
        self.ts_history = deque(maxlen=3)
        tot_reward = 0
        # get initial state and attributes
        state = self.env.reset()
        has_acorn = False
        # start from first round to train tamer on the actual game, not the tutorial
        first_log = self.env.env_logs['log']['round-1']['episode-0']['1']
        info = (first_log['game_rendered_timestamp'], first_log['ts_end_timestamp'])

        ep_start_time = datetime.datetime.now()
        
        with open(self.reward_log_path, 'a+', newline='') as write_obj:
            dict_writer = DictWriter(write_obj, fieldnames=self.reward_log_columns)
            dict_writer.writeheader()
            # endless loop until done
            for ts in count():
                # MAKE H STEP
                now = info[0]
                action = self.act()
                self.ts_history.append((state, action, has_acorn, now))
                # Get next state and reward
                next_state, reward, done, has_acorn, new_info = self.env.step(action)
                human_reward, reward_obtained = self.InteractiveAgent.get_human_reward(info)
                #feedback_ts = dt.datetime.now().time()
                # getting the diference between the time the word was recorded and the time the feedback was given
                self.state_log.append((state, action, next_state, human_reward))

                if human_reward[0] != 0:
                    for i in range(len(human_reward)):
                        h_reward = human_reward[i]
                        # take ending ts to calculate the credit since person stopped giving feedback then
                        agent_got_reward_ts = reward_obtained[i][1]

                        # UPDATE H MODEL
                        credit_logger = []
                        if self.credit_assignment:
                            # based on integral under gamma funcion
                            # first lower bound => 0
                            lower_bound = 0
                            for state_hist in reversed(self.ts_history):
                                prev_state, prev_action, prev_has_acorn, prev_ts = state_hist

                                # upper bound is determined by the previous timestamp - the current timestamp
                                upper_bound = abs(agent_got_reward_ts - prev_ts)
                                credit = self.credit_prob(lower_bound, upper_bound) * h_reward
                                credit_logger.append(credit)
                                self.human_rewards.append(credit)
                                self.H.update(prev_state, prev_has_acorn, prev_action, credit)

                                lower_bound = upper_bound
                                agent_got_reward_ts = prev_ts

                        else:
                            self.H.update(state, has_acorn, action, h_reward)

                        dict_writer.writerow(
                            {
                                'episode': episode_index + 1,
                                'ep_start_ts': ep_start_time,
                                'state': state,
                                'action': action,
                                'next_state': next_state,
                                'agent_got_reward_ts': agent_got_reward_ts,
                                'human_reward': h_reward,
                                'actual_human_reward': credit_logger[0] if credit_logger else 0,
                                'environment_reward': 0,
                                'log_ts': time.time()
                            }
                        )
                    
                tot_reward += reward

                if done:
                    break

                stdout.write('\b' * (len(str(ts)) + 1))
                state = next_state
                info = new_info

        # Decay epsilon
        if self.epsilon > self.min_eps:
            self.epsilon -= self.epsilon_step

    def train(self, model_file_to_save=None):
        """
        TAMER (or Q learning) training loop
        Args:
            model_file_to_save: save Q or H model to this filename
        """
        # render first so that pygame display shows up on top
        for i in range(self.num_episodes):
            print(f'\nEpisode {i}/{self.num_episodes}')
            self._train_episode(i)
            start_states = self.get_start_states()
            p = self.get_policy()
            episode_cum_reward = self.evaluate_policy(p, self.model_policy)
            self.cum_rewards.append(np.mean(episode_cum_reward))

        f_name = np.random.randint(0, 100000)

        if model_file_to_save is not None:
            self.save_model(filename=model_file_to_save)

    def play(self, n_episodes=100, render=False):
        """
        Run episodes with trained agent
        Args:
            n_episodes: number of episodes
            render: optionally render episodes

        Returns: list of cumulative episode rewards
        """
        self.epsilon = 0
        ep_rewards = []
        for i in range(n_episodes):
            state = self.env.reset()
            done = False
            tot_reward = 0
            while not done:
                action = self.act()
                next_state, reward, done, has_acorn, new_info = self.env.step(action)
                tot_reward += reward
                state = next_state
            ep_rewards.append(tot_reward)
        return ep_rewards

    def evaluate(self, n_episodes=100):
        rewards = self.play(n_episodes=n_episodes)
        avg_reward = np.mean(rewards)
        return avg_reward

    def save_model(self, filename):
        """
        Save H or Q model to models dir
        Args:
            filename: name of pickled file
        """
        model = self.H if self.tame else self.Q
        filename = filename if filename.endswith('.p') else f'{filename}.p'
        with open(MODELS_DIR.joinpath(filename), 'wb') as f:
            pickle.dump(model, f)

    def load_model(self, filename):
        """
        Load H or Q model from models dir
        Args:
            filename: name of pickled file
        """
        filename = filename if filename.endswith('.p') else f'{filename}.p'
        with open(MODELS_DIR.joinpath(filename), 'rb') as f:
            model = pickle.load(f)
        if self.tame:
            self.H = model
        else:
            self.Q = model

    def _check_done_training(self):
        done_training = False
        try:
            if 'stop' in pickle.loads(self.r.get("policy_trained")):
                self.r.delete("policy_trained")
                done_training = True
        except:
            pass
        return done_training

    def get_policy(self, filename=None):
        state = self.env.reset()
        has_acorn = 0
        policy = {}
        l = [list(range(1,11)), range(1, 11), range(2)]
        combinations = [p for p in itertools.product(*l)]
        for comb in combinations:
            state = list(comb)
            has_acorn = 1 if state[2] == 1 else 0
            action = np.argmax([prediction.item() for prediction in self.H.predict(state, has_acorn)]).item()
            policy[str(state)] = action

        if filename is not None:
            with open(f"{MODELS_DIR.joinpath(filename)}_policy.json", "w") as f:
                json.dump(policy, f)
        return policy


    def get_start_states(self, num_eval=1000):
        start_states = []
        l = [list(range(1, 10)), range(1, 10), range(2)]
        all_states = [p for p in itertools.product(*l)]

        for _ in range(num_eval):
            start_states.append(list(random.choice(all_states)))
        return start_states
    
    def evaluate_policy(self, policy, model_policy):
        optimal_actions = 0
        for state, action in policy.items():
            if action in model_policy[state]:
                optimal_actions += 1
        return optimal_actions