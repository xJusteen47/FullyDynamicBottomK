"""
This pre-process the dataset to create the dataset for the experiments.
The parameters are:
    - DATASET_NAME: the name of the dataset file
    - d: the radius of the ball to be created

The output is a file with the same name of the dataset file, but with the prefix "dataset_".
The new dataset selects the top 5000 nodes with the highest out-degree, and for each node, it creates a ball of radius d.
"""

import networkx as nx


# Parametri del dataset da generare.
# DATASET_NAME = "soc-LiveJournal1.txt"
DATASET_NAME = "com-youtube.ungraph.txt"
d = 1

# Lettura degli archi dal file di input.
print(f"Reading file {DATASET_NAME}...", end=" ", flush=True)
f = open(DATASET_NAME, "r")

lines = [l.strip().split() for l in f.readlines()]
lines = [(int(x), int(y)) for x, y in lines]
f.close()
print("Done!\n\n")


# Costruzione del grafo diretto usato per ricavare i vicinati.
print("Loading graph...", end=" ", flush=True)
G = nx.DiGraph()
G.add_edges_from(lines[1:])
print("Done!")

# Generazione del dataset: d=1 scrive i vicini dei nodi più connessi;
# d=2 scrive le palle di raggio 2 e ne calcola le statistiche dimensionali.
if d == 1:
    rank = sorted(G.out_degree(), key=lambda x: x[1], reverse=True)[:5000]

    with open(f"dataset_{DATASET_NAME}", "w") as file:
        for node, _ in rank:
            file.write(str(node) + " " + " ".join([str(x) for x in G[node]]) + "\n")

elif d == 2:
    max_size, min_size, avg_size, n = 0, float("inf"), 0, 0
    file = open(f"dataset_d=2_top5000degrees_{DATASET_NAME}", "w")

    rank = sorted(G.out_degree(), key=lambda x: x[1], reverse=True)[:5000]

    for v, _ in rank:
        print(f"\r{100*n/5_000:.4f}%", end="", flush=True)

        if n == 5_000:
            break

        ball = set(nx.ego_graph(G, v, radius=2).nodes())

        max_size = max(max_size, len(ball))
        min_size = min(min_size, len(ball))
        avg_size += len(ball)

        file.write(str(v) + " " + " ".join([str(x) for x in ball]) + "\n")
        n += 1

    avg_size /= n
    print(f"N. sets:\t{n}")
    print(f"Max Size:\t{max_size}")
    print(f"Min Size:\t{min_size}")
    print(f"Avg Size:\t{avg_size}")

    file.close()
