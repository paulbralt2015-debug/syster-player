"""Moteur de reconstitution des lignes (brouillage par permutation de lignes)."""
import cv2
import numpy as np
from scipy.spatial.distance import cdist


def order_lines(gray, k=8, step=8):
    """Retrouve l'ordre des lignes par continuité de l'image.
    step : on ne compare qu'une colonne sur `step` (plus grand = plus rapide)."""
    H = gray.shape[0]
    g = gray[:, ::step].astype(np.float32)
    D = cdist(g, g, 'cityblock') / g.shape[1]
    np.fill_diagonal(D, np.inf)

    nn = np.argsort(D, axis=1)[:, :k]
    edges = {(min(i, j), max(i, j)) for i in range(H) for j in nn[i]}
    edges = sorted(edges, key=lambda e: D[e])

    parent = list(range(H))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    deg = np.zeros(H, int)
    adj = [[] for _ in range(H)]

    def link(a, b):
        adj[a].append(b)
        adj[b].append(a)
        deg[a] += 1
        deg[b] += 1
        parent[find(a)] = find(b)

    for a, b in edges:
        if deg[a] < 2 and deg[b] < 2 and find(a) != find(b):
            link(a, b)

    while True:
        ends = np.array([n for n in range(H) if deg[n] < 2])
        comp = np.array([find(n) for n in ends])
        if len(set(comp)) == 1:
            break
        sub = D[np.ix_(ends, ends)].copy()
        sub[comp[:, None] == comp[None, :]] = np.inf
        a, b = np.unravel_index(np.argmin(sub), sub.shape)
        link(int(ends[a]), int(ends[b]))

    start = next(n for n in range(H) if deg[n] < 2)
    order, prev, cur = [start], -1, start
    while len(order) < H:
        nxt = [n for n in adj[cur] if n != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        order.append(cur)
    return np.array(order)


class Descrambler:
    """Traite les images une à une en gardant le sens haut/bas cohérent."""

    def __init__(self, step=8):
        self.step = step
        self.prev = None

    def reset(self):
        self.prev = None

    def process(self, frame):
        """frame : image BGR (numpy). Retourne l'image réordonnée."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        order = order_lines(gray, step=self.step)
        small = gray[:, ::self.step].astype(np.int16)
        if self.prev is not None and self.prev.shape == small.shape:
            a = np.abs(small[order] - self.prev).mean()
            b = np.abs(small[order[::-1]] - self.prev).mean()
            if b < a:
                order = order[::-1]
        self.prev = small[order]
        return frame[order]
