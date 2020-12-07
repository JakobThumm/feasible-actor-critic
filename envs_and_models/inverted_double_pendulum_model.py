#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =====================================
# @Time    : 2020/12/2
# @Author  : Yang Guan (Tsinghua Univ.)
# @FileName: Inverted_double_pendulum.py
# =====================================
import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np


class Dynamics(object):
    def __init__(self, if_model=False):
        self.mass_cart = 9.42477796
        self.mass_rod1 = 4.1033127
        self.mass_rod2 = 4.1033127
        self.mass_rod2 = 4.1033127
        self.damping_cart = 0.
        self.damping_rod1 = 0.
        self.damping_rod2 = 0.
        self.l_rod1 = 0.6
        self.l_rod2 = 0.6
        self.g = 9.81

    def f_xu(self, states, actions, tau):
        m, m1, m2 = tf.constant(self.mass_cart, dtype=tf.float32),\
                    tf.constant(self.mass_rod1, dtype=tf.float32), \
                    tf.constant(self.mass_rod2, dtype=tf.float32),
        l1, l2 = tf.constant(self.l_rod1, dtype=tf.float32), tf.constant(self.l_rod2, dtype=tf.float32)
        d1, d2, d3 = tf.constant(self.damping_cart, dtype=tf.float32),\
                     tf.constant(self.damping_rod1, dtype=tf.float32), \
                     tf.constant(self.damping_rod2, dtype=tf.float32),
        g = tf.constant(self.g, dtype=tf.float32)
        p, theta1, theta2, pdot, theta1dot, theta2dot = states[:, 0], states[:, 1], states[:, 2], \
                                                        states[:, 3], states[:, 4], states[:, 5]
        u = actions[:, 0]
        ones = tf.ones_like(p, dtype=tf.float32)
        M = tf.reshape(tf.stack([(m+m1+m2)*ones, l1*(m1+m2)*tf.cos(theta1), m2*l2*tf.cos(theta2),
                                 l1*(m1+m2)*tf.cos(theta1), tf.square(l1)*(m1+m2)*ones, l1*l2*m2*tf.cos(theta1-theta2),
                                 l2*m2*tf.cos(theta2), l1*l2*m2*tf.cos(theta1-theta2), tf.square(l2)*m2*ones], axis=1),
                       shape=(-1, 3, 3))
        f = tf.reshape(tf.stack([l1*(m1+m2)*tf.square(theta1dot)*tf.sin(theta1)+m2*l2*tf.square(theta2dot)*tf.sin(theta2)-d1*pdot+u,
                                 -l1*l2*m2*tf.square(theta2dot)*tf.sin(theta1-theta2)+g*(m1+m2)*l1*tf.sin(theta1)-d2*theta1dot,
                                 l1*l2*m2*tf.square(theta1dot)*tf.sin(theta1-theta2)+g*l2*m2*tf.sin(theta2)], axis=1),
                       shape=(-1, 3, 1))
        M_inv = tf.linalg.inv(M)
        tmp = tf.squeeze(tf.matmul(M_inv, f), axis=-1)

        deriv = tf.concat([states[:, 3:], tmp], axis=-1)
        next_states = states + tau * deriv

        return next_states

    def compute_rewards(self, states):  # obses and actions are tensors
        with tf.name_scope('compute_reward') as scope:
            p, theta1, theta2, pdot, theta1dot, theta2dot = states[:, 0], states[:, 1], states[:, 2], \
                                                            states[:, 3], states[:, 4], states[:, 5]
            tip_x = p + self.l_rod1 * tf.sin(theta1) + self.l_rod2 * tf.sin(theta2)
            tip_y = self.l_rod1 * tf.cos(theta1) + self.l_rod2 * tf.cos(theta2)
            dist_penalty = 0.01 * tf.square(tip_x) + tf.square(tip_y - 2)
            v1, v2 = theta1dot, theta2dot
            alive_bonus = 10.
            vel_penalty = 1e-3 * v1 ** 2 + 5e-3 * v2 ** 2
            rewards = alive_bonus-dist_penalty-vel_penalty
            dones = tf.less_equal(tip_y, 1)

        return rewards, dones


class InvertedDoublePendulumModel(object):  # all tensors
    def __init__(self, **kwargs):
        # obs: p, sintheta1, sintheta2, costheta1, costheta2, pdot, theta1dot, theta2dot, frc1, frc2, frc3
        # state: p, theta1, theta2, pdot, theta1dot, theta2dot
        self.dynamics = Dynamics()
        self.obses = None
        self.states = None
        self.actions = None
        self.tau = 0.01
        plt.ion()

    def reset(self, obses):
        self.obses = obses
        self.states = self._get_state(self.obses)

    def _get_obs(self, states):
        p, theta1, theta2, pdot, theta1dot, theta2dot = states[:, 0], states[:, 1], states[:, 2], \
                                                        states[:, 3], states[:, 4], states[:, 5]
        zeros = tf.zeros_like(p, tf.float32)
        lists_to_stack = [p, tf.sin(theta1), tf.sin(theta2), tf.cos(theta1), tf.cos(theta2), pdot, theta1dot, theta2dot,
                          zeros, zeros, zeros]
        return tf.stack(lists_to_stack, axis=1)

    def _get_state(self, obses):
        p, sintheta1, sintheta2, costheta1, costheta2, pdot, theta1dot, theta2dot\
            = obses[:, 0], obses[:, 1], obses[:, 2], obses[:, 3], obses[:, 4], obses[:, 5], obses[:, 6], obses[:, 7]
        theta1 = tf.atan2(sintheta1, costheta1)
        theta2 = tf.atan2(sintheta2, costheta2)
        lists_to_stack = [p, theta1, theta2, pdot, theta1dot, theta2dot]
        return tf.stack(lists_to_stack, axis=1)

    def rollout_out(self, actions):  # obses and actions are tensors, think of actions are in range [-1, 1]
        with tf.name_scope('model_step') as scope:
            self.actions = self.action_trans(actions)
            self.states = self.dynamics.f_xu(self.states, self.actions, self.tau)
            self.obses = self._get_obs(self.states)
            rewards, dones = self.dynamics.compute_rewards(self.states)
        return self.obses, rewards, dones

    def action_trans(self, actions):
        return 500. * actions

    def render(self, mode='human'):
        plt.cla()
        states = self.states.numpy()
        p, theta1, theta2, pdot, theta1dot, theta2dot = states[0, 0], states[0, 1], states[0, 2], \
                                                        states[0, 3], states[0, 4], states[0, 5]
        point0x, point0y = p, 0
        point1x, point1y = point0x + self.dynamics.l_rod1 * np.sin(theta1), \
                           point0y + self.dynamics.l_rod1 * np.cos(theta1)
        point2x, point2y = point1x + self.dynamics.l_rod2 * np.sin(theta2),\
                           point1y + self.dynamics.l_rod2 * np.cos(theta2)

        plt.title("Demo_model")
        ax = plt.axes(xlim=(-2.5, 2.5),
                      ylim=(-2.5, 2.5))
        ax.add_patch(plt.Rectangle((-2.5, -2.5),
                                   5, 5, edgecolor='black',
                                   facecolor='none'))
        ax.axis('equal')
        plt.axis('off')
        ax.plot([-2.5, 2.5], [0, 0], 'k')
        ax.plot([-1, -1], [-2.5, 2.5], 'k')
        ax.plot([1, 1], [-2.5, 2.5], 'k')
        ax.plot(point0x, point0y, 'b.')
        ax.plot([point0x, point1x], [point0y, point1y], color='b')
        ax.plot(point1x, point1y, 'y.')
        ax.plot([point1x, point2x], [point1y, point2y], color='y')
        ax.plot(point2x, point2y, 'r.')
        text_x, text_y_start = -4, 2
        ge = iter(range(0, 1000, 1))
        scale = 0.3
        plt.text(text_x, text_y_start - scale*next(ge), 'position: {:.2f}'.format(p))
        plt.text(text_x, text_y_start - scale*next(ge), r'theta1: {:.2f}rad (${:.2f}\degree$)'.format(theta1, theta1*180/np.pi))
        plt.text(text_x, text_y_start - scale*next(ge), r'theta2: {:.2f}rad (${:.2f}\degree$)'.format(theta2, theta2*180/np.pi))
        plt.text(text_x, text_y_start - scale*next(ge), 'theta1dot: {:.2f}rad/s'.format(theta1dot))
        plt.text(text_x, text_y_start - scale*next(ge), 'theta2dot: {:.2f}rad/s'.format(theta2dot))
        if self.actions is not None:
            actions = self.actions.numpy()
            plt.text(text_x, text_y_start - scale*next(ge), 'action: {:.2f}N'.format(actions[0,0]))

        plt.pause(0.001)
        plt.show()


def testModel():
    model = InvertedDoublePendulumModel()
    # p, sintheta1, sintheta2, costheta1, costheta2, pdot, theta1dot, theta2dot, frc1, frc2, frc3
    init_obs = np.array([[0., 0., 0., 1., 1., 0., 0., 0., 0., 0.]])
    for _ in range(10):
        print('reset')
        model.reset(tf.constant(init_obs, dtype=tf.float32))
        for i in range(50):
            print('step {}'.format(i))
            actions = tf.random.normal((1,1), dtype=tf.float32)
            model.rollout_out(actions)
            model.render()


def testModel2():
    import gym
    env = gym.make('InvertedDoublePendulum-v2')
    obs = env.reset()
    model = InvertedDoublePendulumModel()
    model.reset(np.array([obs]))
    # p, sintheta1, sintheta2, costheta1, costheta2, pdot, theta1dot, theta2dot, frc1, frc2, frc3
    for _ in range(10):
        print('reset')
        obs = env.reset()
        model.reset(np.array([obs], dtype=np.float32))
        for i in range(50):
            print('step {}'.format(i))
            actions = np.random.random((1, 1))
            env.step(actions[0])
            env.render()
            model.rollout_out(actions)
            model.render()


if __name__ == '__main__':
    testModel2()
