import gym
import sys
import itertools
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from queue import Queue
from agent import Agent

def is_int(string):
    try: return int(string) > 0
    except: return False

def process(state):
    batch = []
    for frame in state:
        image = Image.fromarray(frame).convert('L')
        matrix = np.array(image)
        for x in range(85, 96):
            for y in range(96):
                matrix[x][y] = 0
        batch += [matrix / 255]
    return np.array(batch).transpose(1, 2, 0)

args = sys.argv[1:]
if len(args) in [2, 3] and args[0] in ['train', 'continue'] and is_int(args[1]):
    mode = args[0]
    episodes = int(args[1])
    show = 'human' if len(args) == 3 and args[2] == 'show' else 'rgb_array'
elif len(args) == 1 and args[0] == 'test':
    mode = args[0]
    show = 'human'
else:
    print('wrong format')
    exit(1)

steering = [-1, 0, 1]
gas = [0, 1]
breaking = [0, .2]
agent = Agent(
    list(itertools.product(steering, gas, breaking)), 500, 50,
    alpha=.01, gamma=.95, epsilon=1, epsilon_lower=.1, epsilon_decay=.99
)

env = gym.make('CarRacing-v2', render_mode=show)
if mode in ['continue', 'test']:
    agent.load()

if mode == 'test':
    should_break = False

    def take_action(action):
        global frames, should_break
        step_reward = 0
        step_game_over = False
        for _ in range(3):
            observation, reward, game_over, _, _ = env.step(action)
            step_reward += reward
            step_game_over |= game_over
        should_break |= step_game_over
        frames.get()
        frames.put(observation)
        return process(frames.queue), step_reward, step_game_over

    frames = Queue(3)
    observation, _ = env.reset()
    frames.put(observation)
    frames.put(observation)
    frames.put(observation)
    for _ in range(20):
        take_action((0, .5, 0))
    while not should_break:
        agent.step(process(frames.queue), take_action)
    exit(0)

rewards = []
for episode in range(1, episodes + 1):
    episode_reward = 0
    negative_rewards = 0
    should_break = False

    def take_action(action):
        global frames, episode_reward, negative_rewards, should_break
        step_reward = 0
        step_game_over = False
        for _ in range(3):
            observation, reward, game_over, _, _ = env.step(action)
            step_reward += reward
            step_game_over |= game_over
        episode_reward += step_reward
        negative_rewards = negative_rewards + 1 if step_reward < 0 else 0
        should_break |= step_game_over
        frames.get()
        frames.put(observation)
        return process(frames.queue), step_reward, step_game_over

    frames = Queue(3)
    observation, _ = env.reset()
    frames.put(observation)
    frames.put(observation)
    frames.put(observation)
    for _ in range(20):
        take_action((0, .5, 0))
    step = 0
    while not should_break:
        agent.step(process(frames.queue), take_action)
        step += 1
        negative_rewards = 0 if step < 50 + episode else negative_rewards
        should_break |= negative_rewards == 20
    agent.replay()
    if episode % 5 == 0:
        agent.calibrate()
    agent.save()
    rewards += [episode_reward]
    print(f'episode {episode}/{episodes}: reward {episode_reward}')

plt.plot(range(len(rewards)), rewards)
plt.show()
