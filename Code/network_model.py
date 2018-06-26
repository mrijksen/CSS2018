import networkx as nx
from networkx.utils.random_sequence import (powerlaw_sequence)
import numpy as np
from tqdm import tqdm
import sys
import copy
from multiprocessing import Pool


def create_degree_sequence(n, sfunction=None, max_tries=50, **kwds):
    """ Attempt to create a valid degree sequence of length n using
    specified function sfunction(n,**kwds).

    Parameters
    ----------
    n : int
        Length of degree sequence = number of nodes
    sfunction: function
        Function which returns a list of n real or integer values.
        Called as "sfunction(n,**kwds)".
    max_tries: int
        Max number of attempts at creating valid degree sequence.

    Notes
    -----

    Repeatedly create a degree sequence by calling sfunction(n,**kwds)
    until achieving a valid degree sequence. If unsuccessful after
    max_tries attempts, raise an exception.
    
    For examples of sfunctions that return sequences of random numbers,
    see networkx.Utils.

    Examples
    --------
    >>> from networkx.utils import uniform_sequence, create_degree_sequence
    >>> seq=create_degree_sequence(10,uniform_sequence)
    """
    tries=0
    max_deg=n
    while tries < max_tries:
        trialseq=sfunction(n,**kwds)
        # round to integer values in the range [0,max_deg]
        seq=[min(max_deg, max( int(round(s)),0 )) for s in trialseq]
        # if graphical return, else throw away and try again
        if nx.is_graphical(seq):
            return seq
        tries+=1
    raise nx.NetworkXError("Exceeded max (%d) attempts at a valid sequence."%max_tries)


class Individual():
    """ 
    Contains data about status of infection for each person.
    
    time_since_infection equals -1 if person is not infected.
    
    The disease status is 0 for no disease, 1 for the sensitive
    strain and 2 for the resistant strain.
    """
    
    def __init__(self,i):
        self.identifier = i
        self.disease_status = 0
        self.time_since_infection = -1

def network_model(beta, tau, nu, mu, init, num_steps ,graph, doInit = False):
    num_infected  = np.zeros(num_steps)
    num_res = np.zeros(num_steps)

    infected = set()
    
    if doInit:
        for i in range(len(graph)):
            graph.node[i]["Data"].disease_status = 0

        
        for i in init:
            graph.node[i]["Data"].disease_status = 1
            infected.add(i)
    else:
        for i in range(len(graph)):
            if graph.node[i]["Data"].disease_status:
                infected.add(i)
      
    
    # iterate over time
    for t in tqdm(range(num_steps), position = 0):
        infected_copy = infected.copy()

        # iterate over infecteds 
        for i in infected_copy:

            # prob of recovering
            if np.random.rand() < nu:
                graph.node[i]["Data"].disease_status = 0
                infected.remove(i)

            # prob of treatment
            elif graph.node[i]["Data"].disease_status == 1 and np.random.rand() < tau*(1-mu):
                graph.node[i]["Data"].disease_status = 0
                infected.remove(i)

            # prob of getting the resistant strain
            elif graph.node[i]["Data"].disease_status == 1 and np.random.rand() < tau*mu:
                graph.node[i]["Data"].disease_status = 2

            # spreading of disease to neigbours
            if graph.node[i]["Data"].disease_status:
                for neighbor in graph.neighbors(i):
                    if graph.node[neighbor]["Data"].disease_status == 0 and np.random.rand() < beta:
                        highest_disease = max(
                            graph.node[i]["Data"].disease_status,
                            graph.node[neighbor]["Data"].disease_status)
                        graph.node[i]["Data"].disease_status = highest_disease
                        graph.node[neighbor]["Data"].disease_status = highest_disease
                        infected.add(i)
                        infected.add(neighbor)

        # keep track of total number of resistant infecteds
        tot = 0
        for i in infected:
            if graph.node[i]["Data"].disease_status == 2:
                tot += 1
        num_res[t] = tot 
        num_infected[t] = len(infected)
        
    return (num_res, num_infected)
