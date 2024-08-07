from env import RoboTaxiEnv

ACTION_DICT = {'W': 1, 'D': 2, 'S': 3, 'A': 4, '': 0}

if __name__ == '__main__':

    env = RoboTaxiEnv({'rng_seed': int('00000')})

    obs, info = env.reset()
    for _ in range(1000):
        print('-')
        env.render()

        print(env.map)

        action_char = input("Action: ").strip()
        if action_char:
            action_char = action_char[0]

        action = ACTION_DICT[action_char]

        obs, rew, done, info = env.step(action)  # take a random action
        print(f"Reward: {rew}")
        print(f"Score: {info['cumulative_reward']}")

        if done:
            break

    env.close()
