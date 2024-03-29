import random
import numpy as np
from queue import Queue
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from keras.optimizers import Adam

class Agent:
    def __init__(self, action_space, memory_size, batch_size, **hyper):
        self.alpha = hyper['alpha']
        self.gamma = hyper['gamma']
        self.epsilon = hyper['epsilon']
        self.epsilon_lower = hyper['epsilon_lower']
        self.epsilon_decay = hyper['epsilon_decay']
        self.action_space = action_space
        self.memory = Queue(memory_size)
        self.batch_size = batch_size
        self.model = self.create_model()
        self.target_model = self.create_model()
        self.calibrate()

    def create_model(self):
        model = Sequential()
        model.add(Conv2D(filters=6, kernel_size=7, strides=3, activation='relu', input_shape=(96, 96, 3)))
        model.add(MaxPooling2D(pool_size=2))
        model.add(Conv2D(filters=12, kernel_size=4, activation='relu'))
        model.add(MaxPooling2D(pool_size=2))
        model.add(Flatten())
        model.add(Dense(216, activation='relu'))
        model.add(Dense(len(self.action_space)))
        model.compile(loss='mean_squared_error', optimizer=Adam(learning_rate=self.alpha))
        return model

    def step(self, state, take_action):
        if random.random() < self.epsilon:
            action_index = random.randrange(len(self.action_space))
        else:
            q_values = self.model.predict(np.array([state]), verbose=0)[0]
            action_index = np.argmax(q_values)
        next_state, reward, game_over = take_action(self.action_space[action_index])
        if len(self.memory.queue) == self.memory.maxsize:
            self.memory.get()
        self.memory.put((state, action_index, next_state, reward, game_over))

    def replay(self):
        memory = list(self.memory.queue)
        if self.batch_size > len(memory): return
        batch = random.sample(memory, self.batch_size)
        training_inputs = []
        training_outputs = []
        for state, action_index, next_state, reward, game_over in batch:
            target = self.model.predict(np.array([state]), verbose=0)[0]
            if game_over:
                target[action_index] = reward
            else:
                q_values = self.target_model.predict(np.array([next_state]), verbose=0)[0]
                target[action_index] = reward + self.gamma * np.max(q_values)
            training_inputs += [state]
            training_outputs += [target]
        self.model.fit(np.array(training_inputs), np.array(training_outputs), use_multiprocessing=True, verbose=0)
        if self.epsilon > self.epsilon_lower:
            self.epsilon *= self.epsilon_decay

    def calibrate(self):
        self.target_model.set_weights(self.model.get_weights())

    def load(self):
        self.model.load_weights('model')
        self.calibrate()
        with open('epsilon', 'r') as fd:
            self.epsilon = float(fd.read())

    def save(self):
        self.target_model.save_weights('model')
        with open('epsilon', 'w') as fd:
            fd.write(str(self.epsilon))
