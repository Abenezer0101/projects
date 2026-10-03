"""A 3-d tree over unit vectors, and the brute-force scan it has to beat.

Both searches count the distance computations they perform. Wall-clock time
answers "which is faster on this machine today"; the operation count answers
"which does less work", which is the part that transfers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from geo import squared_chord

Vector = tuple[float, float, float]


@dataclass
class Node:
    point: Vector
    payload: object
    axis: int
    left: "Node | None" = None
    right: "Node | None" = None


@dataclass
class SearchStats:
    distance_calls: int = 0
    nodes_visited: int = 0
    subtrees_pruned: int = 0


def build(items: list[tuple[Vector, object]], depth: int = 0) -> Node | None:
    """Median split, cycling through the three axes.

    Splitting on the median rather than the midpoint keeps the tree balanced
    whatever the distribution, which matters here: real geography is clumped,
    and a midpoint split on clustered data degenerates into a linked list.
    """
    if not items:
        return None
    axis = depth % 3
    items = sorted(items, key=lambda pair: pair[0][axis])
    mid = len(items) // 2
    point, payload = items[mid]
    return Node(
        point=point,
        payload=payload,
        axis=axis,
        left=build(items[:mid], depth + 1),
        right=build(items[mid + 1:], depth + 1),
    )


def nearest(root: Node | None, target: Vector,
            stats: SearchStats | None = None) -> tuple[object, float]:
    """Nearest neighbour by squared chord distance.

    The pruning test is the one place this is easy to get wrong: a subtree can
    only be skipped when the *perpendicular distance to the splitting plane*
    already exceeds the best distance found so far. Comparing against the
    distance to the splitting point instead looks similar and silently returns
    wrong answers, which is why `difftest` exists.
    """
    stats = stats or SearchStats()
    best: list = [None, float("inf")]

    def visit(node: Node | None) -> None:
        if node is None:
            return
        stats.nodes_visited += 1
        stats.distance_calls += 1
        d = squared_chord(node.point, target)
        if d < best[1]:
            best[0], best[1] = node.payload, d

        delta = target[node.axis] - node.point[node.axis]
        near, far = (node.left, node.right) if delta < 0 else (node.right, node.left)
        visit(near)
        # the plane is `delta` away; anything beyond it is at least delta^2 off
        if delta * delta < best[1]:
            visit(far)
        elif far is not None:
            stats.subtrees_pruned += 1

    visit(root)
    return best[0], best[1]


def brute_force(items: list[tuple[Vector, object]], target: Vector,
                stats: SearchStats | None = None) -> tuple[object, float]:
    stats = stats or SearchStats()
    best_payload, best_d = None, float("inf")
    for point, payload in items:
        stats.distance_calls += 1
        d = squared_chord(point, target)
        if d < best_d:
            best_payload, best_d = payload, d
    return best_payload, best_d


def naive_lonlat_tree_nearest(items: list[tuple[tuple[float, float], object]],
                              target: tuple[float, float]) -> object:
    """The tempting mistake: a 2-d tree indexing (lat, lon) directly.

    Kept as a first-class function so its failure is a measured result rather
    than a warning in a comment.
    """
    import math

    @dataclass
    class N:
        point: tuple[float, float]
        payload: object
        axis: int
        left: "N | None" = None
        right: "N | None" = None

    def build2(pairs, depth=0):
        if not pairs:
            return None
        axis = depth % 2
        pairs = sorted(pairs, key=lambda p: p[0][axis])
        mid = len(pairs) // 2
        return N(pairs[mid][0], pairs[mid][1], axis,
                 build2(pairs[:mid], depth + 1), build2(pairs[mid + 1:], depth + 1))

    root = build2(items)
    best: list = [None, float("inf")]

    def visit(node):
        if node is None:
            return
        d = math.hypot(node.point[0] - target[0], node.point[1] - target[1])
        if d < best[1]:
            best[0], best[1] = node.payload, d
        delta = target[node.axis] - node.point[node.axis]
        near, far = (node.left, node.right) if delta < 0 else (node.right, node.left)
        visit(near)
        if abs(delta) < best[1]:
            visit(far)

    visit(root)
    return best[0]
