import numpy as np
import scipy as sp
from scipy.integrate import odeint

# sexual mixing matrix
def SMM(i, j, N, epsilon, pi):
    return epsilon * (i == j) + (1 - epsilon) * pi[j] * N[j] / np.sum(pi * N)

# change in susceptible hosts in group i
def dSidt(S, Ires, Isen, N, pi, i, alpha, beta, gamma, epsilon, phi, mu, D):
    nu = (1 - phi) / D
    tau = phi / D

    dSi = -S[i] * pi[i] * sum([
        SMM(i, j, N, epsilon, pi) * beta[i, j] * (Isen[j] + Ires[j]) / N[j]
        for j in [0, 1]
    ]) + nu * (Isen[i] + Ires[i]) + tau * (1 - mu) * Isen[i] + alpha * (
        -S[i] + N[i]) - gamma * S[i] + gamma * N[i] * sum(S)

    return dSi

# change in infecteds of sensitive strain in group i
def dIsenidt(S, Ires, Isen, N, pi, i, alpha, beta, gamma, epsilon, phi, mu, D):
    nu = (1 - phi) / D
    tau = phi / D

    dIseni = S[i] * pi[i] * sum([
        SMM(i, j, N, epsilon, pi) * beta[i, j] * Isen[j] / N[j]
        for j in [0, 1]
    ]) - (nu + tau + alpha + gamma) * Isen[i] + gamma * N[i] * np.sum(Isen)
    
    return dIseni

# change in infecteds of resistant strain in group i
def dIresidt(S, Ires, Isen, N, pi, i, alpha, beta, gamma, epsilon, phi, mu, D):
    nu = (1 - phi) / D
    tau = phi / D

    dIresi = S[i] * pi[i] * sum([
        SMM(i, j, N, epsilon, pi) * beta[i, j] * Ires[j] / N[j]
        for j in [0, 1]
    ]) - (nu + alpha + gamma) * Ires[i] + tau * mu * Isen[i] + gamma * N[i] * np.sum(Ires)
    return dIresi

# full model
def math_model(y, t, N, pi, alpha, beta, gamma, epsilon, phi, mu, D):
    dydt = []
    S = y[:2]
    Ires = y[2:4]
    Isen = y[4:]

    funcs = [dSidt, dIresidt, dIsenidt]

    for func in funcs:
        for i in range(2):
            dydt.append(
                func(S, Ires, Isen, N, pi, i, alpha, beta, gamma, epsilon, phi,
                     mu, D))
    return dydt
