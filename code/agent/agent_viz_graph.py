import networkx as nx
import pickle
import matplotlib.pyplot as plt

gg = None
with open('./agent/agent_acl_graph.gpickle', 'rb') as f:
    gg = pickle.load(f)

nx.draw_networkx(gg)

plt.show()