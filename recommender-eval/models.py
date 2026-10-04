"""Three recommenders, each fitted on a training set and nothing else.

Each exposes `fit(train)` and `recommend(user, k, exclude)`. `exclude` is the
user's training history: recommending something the user has already
interacted with is free marks, and a protocol that permits it flatters every
model equally while ranking them wrongly.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from simulate import Interaction


class Popularity:
    """Global interaction counts. The baseline that is embarrassingly hard to
    beat and routinely left out of papers."""

    name = "popularity (global)"

    def fit(self, train: list[Interaction]) -> "Popularity":
        self.ranked = [item for item, _ in Counter(i.item for i in train).most_common()]
        return self

    def recommend(self, user: int, k: int, exclude: set[int]) -> list[int]:
        out = []
        for item in self.ranked:
            if item not in exclude:
                out.append(item)
                if len(out) == k:
                    break
        return out


class RecentPopularity:
    """Counts from the last `window` days of training only.

    Included because it is the honest comparison for a drifting catalogue: if
    collaborative filtering only beats *global* popularity, it may just be
    rediscovering what is popular now.
    """

    name = "popularity (recent 14d)"

    def __init__(self, window: int = 14):
        self.window = window

    def fit(self, train: list[Interaction]) -> "RecentPopularity":
        last_day = max(i.day for i in train)
        cutoff = last_day - self.window
        counts = Counter(i.item for i in train if i.day > cutoff)
        if not counts:
            counts = Counter(i.item for i in train)
        self.ranked = [item for item, _ in counts.most_common()]
        return self

    def recommend(self, user: int, k: int, exclude: set[int]) -> list[int]:
        out = []
        for item in self.ranked:
            if item not in exclude:
                out.append(item)
                if len(out) == k:
                    break
        return out


class ItemKNN:
    """Item-item collaborative filtering on cosine similarity of co-occurrence.

    sim(a, b) = |users(a) & users(b)| / sqrt(|users(a)| * |users(b)|)

    A user is scored on an item by summing its similarity to each item in
    their history. No timestamps are used -- which is the point: the model
    cannot tell whether a co-occurrence came from before or after the
    evaluation point, so the split is the only thing protecting it.
    """

    name = "item-item CF"

    def __init__(self, neighbours: int = 50):
        self.neighbours = neighbours

    def fit(self, train: list[Interaction]) -> "ItemKNN":
        users_of: dict[int, set[int]] = defaultdict(set)
        self.items_of: dict[int, set[int]] = defaultdict(set)
        for i in train:
            users_of[i.item].add(i.user)
            self.items_of[i.user].add(i.item)

        norms = {item: math.sqrt(len(u)) for item, u in users_of.items()}
        # co-occurrence counts, built by walking each user's basket
        co: dict[int, Counter] = defaultdict(Counter)
        for items in self.items_of.values():
            basket = list(items)
            for a_index, a in enumerate(basket):
                for b in basket[a_index + 1:]:
                    co[a][b] += 1
                    co[b][a] += 1

        self.similar: dict[int, list[tuple[int, float]]] = {}
        for a, counter in co.items():
            scored = [(b, n / (norms[a] * norms[b])) for b, n in counter.items()]
            scored.sort(key=lambda pair: -pair[1])
            self.similar[a] = scored[:self.neighbours]

        self.fallback = [item for item, _ in
                         Counter(i.item for i in train).most_common()]
        return self

    def recommend(self, user: int, k: int, exclude: set[int]) -> list[int]:
        scores: Counter = Counter()
        for item in self.items_of.get(user, ()):
            for other, sim in self.similar.get(item, ()):
                if other not in exclude:
                    scores[other] += sim
        out = [item for item, _ in scores.most_common(k)]
        if len(out) < k:   # a cold user gets the popular list, as in production
            for item in self.fallback:
                if item not in exclude and item not in out:
                    out.append(item)
                    if len(out) == k:
                        break
        return out


MODELS = [Popularity, RecentPopularity, ItemKNN]
