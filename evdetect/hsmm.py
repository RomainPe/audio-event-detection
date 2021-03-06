"""
Hidden semi-Markov event models (implementation not completed yet)
"""

import numpy as np
from scipy.special import factorial

from evdetect.hmm import HiddenMarkovModel


class HiddenSemiMarkovModel(HiddenMarkovModel):
    """Hidden semi-Markov model class

    Parameters
    ----------
    a : ndarray, shape (n_states, n_states)
        Transition probabilities
    pi : ndarray, shape (n_states,)
        Initial probabilities
    mu : ndarray, shape (n_states, n_freq_bins)
        Emission distributions parameters (Dirichlet)
    nu : ndarray, shape (n_states,)
        Duration distributions parameters (Poisson)
    scaling : float
        Scaling factor used in emission density functions
    end_state : string
        Possible hidden end states, must be either 'all' or 'last'
    min_float : float
        Minimum float value used to avoid 0 values in log computations

    """

    def __init__(self, a, pi, mu, nu, scaling=1.0, end_state='all', min_float=1e-50):
        assert(np.all(nu > 0))
        self.nu = nu

        super(HiddenSemiMarkovModel, self).__init__(a, pi, mu, scaling, end_state, min_float)

    def log_p(self, i, d):
        """Duration log probability functions

        Parameters
        ----------
        i : int
            Index of the considered hidden state
        d : int
            Duration

        Returns
        -------
        float
            Value of the duration log probability function associated with hidden state i evaluated at d
        """
        return d * np.log(self.nu[i]) - self.nu[i] - np.sum(np.log(np.arange(1, d + 1)))

    def p(self, i, d):
        """Duration log probability functions

        Parameters
        ----------
        i : int
            Index of the considered hidden state
        d : int
            Duration

        Returns
        -------
        float
            Value of the duration probability function associated with hidden state i evaluated at d
        """
        return self.nu[i] ** d * np.exp(- self.nu[i]) / factorial(d)

    # TODO: deal with overlapping matches
    def detect_event(self, x, epsilon, delta, display=False, max_segment_length=50):
        """Event detection interface

        Parameters
        ----------
        x : ndarray, shape (n_steps, n_freq_bins)
            Input audio stream
        epsilon : float
            Likelihood threshold
        delta : float
            Minimum subsequence length
        display : bool
            Whether to display detection results or not
        max_segment_length : int
            Maximum segment length

        Returns
        -------
        list
            List of reported subsequences

        """
        n_steps = x.shape[0]
        log_e = np.log(epsilon)

        log_v = np.zeros((n_steps, self.n_states))
        s = [[(-1, -1) for _ in range(self.n_states)] for _ in range(n_steps)]

        candidates = set([])
        reported_subsequences = []

        for t in range(n_steps):
            for i in range(self.n_states):
                log_v1 = - np.inf
                log_v2 = - np.inf

                best_d1 = 0
                best_d2 = 0
                best_j2 = 0

                log_emissions = 0

                for d in range(1, min(t + 2, max_segment_length)):
                    log_emissions += self.log_b(i, x[t])

                    temp_log_v1 = self.log_pi[i] + self.log_p(i, d) + log_emissions

                    if temp_log_v1 > log_v1:
                        best_d1 = d
                        log_v1 = temp_log_v1

                    if d <= t:
                        best_j2 = np.argmax(self.log_a[:, i] + log_v[t - d])
                        temp_log_v2 = self.log_a[best_j2, i] + log_v[t - d, best_j2] + self.log_p(i, d) + log_emissions

                        if temp_log_v2 > log_v2:
                            best_d2 = d
                            log_v2 = temp_log_v2

                if log_v1 > log_v2:
                    log_v[t, i] = log_v1 - best_d1 * log_e
                    s[t][i] = (t - best_d1 + 1, i)
                else:
                    log_v[t, i] = log_v2 - best_d2 * log_e
                    s[t][i] = s[t - best_d2][best_j2]

                if self.end_state == 'all' or i == self.n_states - 1:
                    if log_v[t, i] >= - delta * log_e:  # log likelihood threshold
                        # if the starting position is not shared with another candidate, i.e. Viterbi paths do not cross
                        if s[t][i] not in set([c[1] for c in candidates]):
                            candidates.add((log_v[t, i], s[t][i], (t, i)))
                        else:
                            for c in set(candidates):
                                # otherwise, keep the one with highest log likelihood
                                if s[t][i] == c[1] and log_v[t, i] >= c[0]:
                                    candidates.remove(c)
                                    candidates.add((log_v[t, i], s[t][i], (t, i)))

            for c in set(candidates):
                if c[1] not in set([s[t][i] for i in range(self.n_states)]) or t == n_steps - 1:
                    length = c[2][0] - c[1][0] + 1
                    log_likelihood = c[0] + length * log_e

                    if display:
                        print('\n' + "Log likelihood: {}".format(log_likelihood))
                        print("Starting position: {} (in state {})".format(c[1][0], c[1][1]))
                        print("End position: {} (in state {})".format(c[2][0], c[2][1]))

                    reported_subsequences.append((c[0], c[1][0], c[2][0]))
                    candidates.remove(c)

        return reported_subsequences

    # TODO: implement parameters learning
    def learn_parameters(self, x_train, n_iter):
        """Parameters learning (EM algorithm) interface

        Parameters
        ----------
        x_train : list
            List of training sequences
        n_iter : int
            Number of EM iterations to perform

        """
        # num_train_seq = len(x_train)
        #
        # for _ in range(n_iter):
        #
        #     likelihoods = []
        #     gamma = []
        #     xi = []
        #     tau = []
        #
        #     # E step
        #     for k in range(num_train_seq):
        #         seq_likelihood, seq_gamma, seq_xi, seq_tau = self._forward_backward(x_train[k])
        #
        #         likelihoods.append(seq_likelihood)
        #         gamma.append(seq_gamma)
        #         xi.append(seq_xi)
        #         tau.append(seq_tau)
        #
        #     # M step
        #     new_a = np.zeros_like(self.a)
        #     new_mu = np.zeros_like(self.mu)
        #     new_nu = np.zeros_like(self.nu)
        #     new_pi = np.zeros_like(self.pi)
        #
        #     new_mu_norm = np.zeros(self.n_states)
        #
        #     for k in range(num_train_seq):
        #         new_a += np.sum(xi[k] / likelihoods[k], axis=0)
        #         new_pi += gamma[k][0] / likelihoods[k]
        #
        #         for i in range(self.n_states):
        #             for t in range(x_train[k].shape[0]):
        #                 normalized_frame = x_train[k][t] / np.sum(x_train[k][t])
        #                 new_mu[i] += gamma[k][t, i] / likelihoods[k] * normalized_frame
        #
        #             new_mu_norm[i] += np.sum(gamma[k][:, i]) / likelihoods[k]
        #
        #     new_pi *= 1 / np.sum(new_pi)
        #
        #     for i in range(self.n_states):
        #         new_a[i] *= 1 / np.sum(new_a[i])
        #         new_mu[i] *= 1 / new_mu_norm[i]
        #
        #     self.a = new_a
        #     self.mu = new_mu
        #     self.nu = new_nu
        #     self.pi = new_pi

    def _forward_backward(self, x):
        """Forward backward recursion

        Parameters
        ----------
        x : ndarray, shape (n_steps, n_freq_bins)

        Returns
        -------
        tuple
            (seq_likelihood, gamma, xi) with seq_likelihood the marginal likelihood of x under the model

        """
        pass
