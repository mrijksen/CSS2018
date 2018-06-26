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
        
    source: https://networkx.github.io/documentation/networkx-1.10
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

def power_law_graph(exp, num, seed=1234, plot=False):
    """
    Function which creates power law graph based on a number of nodes (num),
    an exponent (exp) and a seed. 
    
    source: http://nbviewer.jupyter.org/gist/Midnighter/248f1a5d8c21b39525ae
    """
    
    print("Power law exponent = -{0:.2f}".format(exp))
    
    # create graph
    sequence = create_degree_sequence(num, powerlaw_sequence, exponent=exp)
    graph = nx.configuration_model(sequence, seed=seed)

    # count parallel edges and avoid counting A-B as well as B-A
    num_par = sum(
        len(graph[node][neigh]) for node in graph
        for neigh in graph.neighbors(node)) // 2
    print("Power law graph has {0:d} parallel edges".format(num_par))
    loops = graph.selfloop_edges()

    # remove them
    graph = nx.Graph(graph)
    graph.remove_edges_from(loops)
    
    # get largest connected component
    # unfortunately, the iterator over the components is not guaranteed to be sorted by size
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    lcc = graph.subgraph(components[0])
    print("Size of largest connected component = {0:d}".format(len(lcc)))
    
    if plot == True:

        # new degree sequence
        simple_seq = [deg for (node, deg) in lcc.degree()]

        # create histograms
        counts = np.bincount(sequence)
        mask = (counts > 0)
        plt.figure()
        plt.plot(
            np.arange(len(counts))[mask],
            counts[mask] / counts.sum(),
            "o",
            label="MultiGraph")
        simple_counts = np.bincount(simple_seq)
        mask = (simple_counts > 0)

        # distribution is shifted for visibility
        plt.plot(
            np.arange(len(simple_counts))[mask],
            simple_counts[mask] / simple_counts.sum() / 10.0,
            "o",
            label="Simple LCC")

        # plot distribution
        x = np.arange(1, len(counts))
        plt.plot(x, np.power(x, -exp))
        plt.xlabel(r"Degree $k$")
        plt.xscale("log")
        plt.ylabel(r"Probability $P(k)$")
        plt.yscale("log")
        plt.title(r"$N = {0:d}, \\quad \\lambda = {1:.2f}$".format(num, exp))
        plt.legend(loc="best")
        plt.show()
        nx.powerlaw_cluster_graph

        # visualize network
        plt.figure()
        pos = nx.spring_layout(graph)
        nx.draw(graph, pos, node_color='b', node_size=10, with_labels=False)
        plt.show()
    return graph

def random_network(p, num, seed=1234, plot=False):
    """
    Function which creates random network based on edge probability (p),
    a given number of nodes (num) and a seed. 
    """
    
    # create graph
    graph = nx.fast_gnp_random_graph(num, p, seed=seed, directed=False)

    # plot
    if plot == True:
        plt.figure()
        pos = nx.spring_layout(graph)
        nx.draw(graph, pos, node_color='b', node_size=5, with_labels=False)
        plt.show()

        plt.figure()
        degree_sequence = sorted([d for n, d in graph.degree()], reverse=True)
        # print "Degree sequence", degree_sequence
        dmax = max(degree_sequence)

        plt.semilogy(degree_sequence, 'b-', marker='o')
        plt.title("Degree rank plot")
        plt.ylabel("degree")
        plt.xlabel("rank")
        plt.show()
    return graph

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


def network_model(beta, tau, nu, mu, init, num_steps, graph, doInit = False, disable_progress=False):
    """
    Function which runs disease spreading model on specified network.
    
    beta = transmission probability
    tau = probability of treatment
    nu = probability of recovering spontaneously
    init = initial number of infecteds (with sensitive strain)
    num_steps = number of iterations to run model
    graph = an initialized graph, e.g. random or scale-free
    doInit = boolean specifying to initialize or not
    """
    
    # arrays/set containing number of diseased
    num_infected  = np.zeros(num_steps)
    num_res = np.zeros(num_steps)
    infected = set()
    
    # initialization of infected individuals
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
    for t in tqdm(range(num_steps), position = 0, disable=disable_progress):
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
    return (num_res, num_infected, graph)
