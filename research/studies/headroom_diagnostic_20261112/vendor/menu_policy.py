"""Documentation-only tool retrieval. No ROS endpoint or answer knowledge."""
import math
import re
import time
from collections import Counter


def words(text):
    return re.findall(r'[a-z]+|[0-9]+', str(text).lower())


class MenuPolicy:
    """Rank actual names, descriptions and argument schemas; never fill arguments."""

    def __init__(self, schemas, arm, limit=5):
        started = time.perf_counter()
        self.schemas = schemas
        self.arm = arm
        self.limit = limit
        self.fields = []
        if arm in ('original', 'prompted'):
            self.preprocessing_seconds = 0.0
            return
        for schema in schemas:
            f = schema['function']
            self.fields.append([
                Counter(words(f['name'])),
                Counter(words(f.get('description', ''))),
                Counter(words(f.get('parameters', {}))),
            ])
        self.idf = {}
        vocabulary = set().union(*(set().union(*row) for row in self.fields))
        for token in vocabulary:
            count = sum(any(token in field for field in row) for row in self.fields)
            self.idf[token] = math.log(1 + (len(schemas) - count + .5) / (count + .5))
        self.preprocessing_seconds = time.perf_counter() - started

    def select(self, request, observation='', expanded=False):
        started = time.perf_counter()
        if self.arm in ('original', 'prompted') or expanded:
            return self.schemas, {'reason': 'full_menu' if self.arm in ('original', 'prompted') else 'explicit_expansion', 'seconds': time.perf_counter()-started}
        # The simple control retains the initial request. The candidate conditions
        # retrieval on the most recent observation, without interpreting its meaning.
        query = Counter(words(request + (' ' + observation[:1024] if self.arm == 'candidate' else '')))
        scores = []
        for row in self.fields:
            if self.arm == 'simple':
                merged = row[0] + row[1] + row[2]
                score = sum(self.idf.get(w, 0) * min(merged[w], 2) for w in query)
                score /= math.sqrt(max(1, sum(merged.values())))
            else:
                score = 0.0
                for weight, field in zip((.5, .3, .2), row):
                    score += weight * sum(self.idf.get(w, 0) * min(field[w], 2) for w in query) / math.sqrt(max(1, sum(field.values())))
            scores.append(score)
        ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], self.schemas[i]['function']['name']))
        reason = 'top_k'
        chosen = ranked[:self.limit]
        if not scores[ranked[0]]:
            chosen, reason = ranked, 'no_lexical_support'
        elif self.arm == 'candidate' and len(ranked) > self.limit:
            boundary = scores[ranked[self.limit-1]]
            next_score = scores[ranked[self.limit]]
            # A narrow cutoff gap is only a heuristic, not calibrated confidence.
            if boundary > 0 and (boundary-next_score)/boundary < .10:
                chosen, reason = ranked, 'ambiguous_cutoff'
        selected = [self.schemas[i] for i in chosen]
        return selected, {'reason': reason, 'scores': [{'name': self.schemas[i]['function']['name'], 'score': scores[i]} for i in ranked], 'seconds': time.perf_counter()-started}
