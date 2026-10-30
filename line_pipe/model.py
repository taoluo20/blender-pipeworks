# SPDX-License-Identifier: GPL-3.0-or-later
"""Routing state, independent of Blender context and modal event delivery."""
import math
from itertools import permutations, product
from mathutils import Vector

EPS = 1e-7
WORLD_AXES = {name: Vector(value) for name, value in (
    ('+X', (1, 0, 0)), ('-X', (-1, 0, 0)), ('+Y', (0, 1, 0)),
    ('-Y', (0, -1, 0)), ('+Z', (0, 0, 1)), ('-Z', (0, 0, -1)))}


def initial_directions(project):
    """Follow projected world axes, spreading ambiguous views into six distinct rays."""
    projected = {key: Vector(project(axis)) for key, axis in WORLD_AXES.items()}
    normalized = {key: value.normalized() for key, value in projected.items()}
    if all(value.length > .15 for value in projected.values()) and all(
            a.dot(b) < math.cos(math.radians(20)) for a, b in
            ((normalized[a], normalized[b]) for a, b in permutations(normalized, 2))):
        return normalized
    # An axis viewed end-on has no screen direction. Fit an antipodal hexagon
    # to the visible axes so all six choices remain available and labeled.
    positive = ('+X', '+Y', '+Z')
    best_score, best = -1.0, None
    for order in permutations(positive):
        for signs in product((-1, 1), repeat=3):
            basis = {key: Vector((math.cos(i * math.pi / 3), math.sin(i * math.pi / 3))) * signs[i]
                     for i, key in enumerate(order)}
            cosine = sum(projected[key].dot(value) for key, value in basis.items())
            sine = sum(projected[key].dot(Vector((-value.y, value.x))) for key, value in basis.items())
            score = math.hypot(cosine, sine)
            if score > best_score + EPS:
                best_score, best = score, (basis, math.atan2(sine, cosine))
    basis, angle = best
    result = {}
    for key, value in basis.items():
        ray = Vector((value.x * math.cos(angle) - value.y * math.sin(angle),
                      value.x * math.sin(angle) + value.y * math.cos(angle)))
        result[key], result['-' + key[1]] = ray, -ray
    return result


def choose_initial_direction(delta, directions, current=None, deadzone=6):
    delta = Vector(delta)
    if delta.length < deadzone:
        return None
    mouse = delta.normalized()
    winner = max(directions, key=lambda key: mouse.dot(directions[key]))
    if current in directions and mouse.dot(directions[current]) >= mouse.dot(directions[winner]) - .04:
        return current
    return winner


def frame(direction):
    heading = Vector(direction).normalized()
    if heading.length < .5:
        raise ValueError('bad_direction')
    reference = min((Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
                    key=lambda axis: abs(axis.dot(heading)))
    u = heading.cross(reference).normalized()
    return u, heading.cross(u).normalized()


def rounded_path(points, radius, steps):
    """Sample tangent circular fillets without silently reducing the requested radius."""
    points = [Vector(p) for p in points]
    if len(points) < 2:
        return points
    result = [points[0]]
    for index in range(1, len(points) - 1):
        previous, corner, following = points[index - 1:index + 2]
        incoming, outgoing = corner - previous, following - corner
        ilen, olen = incoming.length, outgoing.length
        incoming.normalize()
        outgoing.normalize()
        angle = math.acos(max(-1.0, min(1.0, incoming.dot(outgoing))))
        if angle < EPS:
            continue
        if abs(angle - math.pi / 2) > 1e-4:
            raise ValueError('Route corners must be perpendicular')
        needed_before = radius * (2 if index > 1 else 1)
        needed_after = radius * (2 if index < len(points) - 2 else 1)
        if ilen + EPS < needed_before or olen + EPS < needed_after:
            raise ValueError('Segment is too short for the bend radius')
        start = corner - incoming * radius
        center = start + outgoing * radius
        radial = -outgoing
        if (result[-1] - start).length > EPS:
            result.append(start)
        for step in range(1, steps + 1):
            theta = math.pi / 2 * step / steps
            result.append(center + radius * (radial * math.cos(theta) + incoming * math.sin(theta)))
    if (result[-1] - points[-1]).length > EPS:
        result.append(points[-1])
    return result


class Route:
    def __init__(self, origin, direction, diameter, radius, axis_initial=False):
        if not all(math.isfinite(v) and v > 0 for v in (diameter, radius)) or radius <= diameter / 2:
            raise ValueError('bad_radius')
        self.points = [Vector(origin)]
        self.heading = Vector(direction).normalized()
        self.u, self.v = frame(self.heading)
        self.diameter, self.radius = diameter, radius
        self.length = 0.0
        self.turning = False
        self.candidate = None
        self.history = []
        self.axis_initial = axis_initial

    @property
    def choosing_initial(self):
        return self.axis_initial and len(self.points) == 1 and not self.turning

    def aim_initial(self, axis, length):
        if not self.choosing_initial:
            return
        self.heading = WORLD_AXES[axis].copy()
        self.u, self.v = frame(self.heading)
        self.extend(length)

    @property
    def clearance(self):
        return max(self.diameter * .02, EPS * 10)

    @property
    def minimum(self):
        return self.radius + self.clearance if len(self.points) > 1 else 0.0

    @property
    def turn_minimum(self):
        return self.radius * (2 if len(self.points) > 1 else 1) + self.clearance

    @property
    def tip(self):
        return self.points[-1] + self.heading * self.length

    def extend(self, length):
        self.length = max(self.minimum, float(length))

    def begin_turn(self):
        if self.length + EPS < self.turn_minimum:
            return False
        self.turning, self.candidate = True, None
        return True

    def choose(self, direction):
        if not self.turning:
            return
        direction = Vector(direction).normalized()
        if abs(direction.dot(self.heading)) > 1e-5:
            raise ValueError('Turn must be perpendicular')
        self.candidate = direction

    def release_turn(self):
        if self.turning and self.candidate is not None:
            self.history.append((self.heading.copy(), self.u.copy(), self.v.copy(), self.length))
            self.points.append(self.tip)
            rotation = self.heading.rotation_difference(self.candidate)
            self.u, self.v = rotation @ self.u, rotation @ self.v
            self.heading = self.candidate.copy()
            self.length = self.minimum
        self.turning, self.candidate = False, None

    def undo(self):
        if self.turning:
            self.turning, self.candidate = False, None
        elif self.history:
            self.points.pop()
            self.heading, self.u, self.v, self.length = self.history.pop()

    def route_points(self, preview=True):
        result = self.points + [self.tip]
        if preview and self.turning and self.candidate is not None:
            result.append(self.tip + self.candidate * (self.radius + self.clearance))
        return result


def turn_directions(u, v, project):
    """Assign all four bends to a stable screen cross, including edge-on views."""
    pu, pv = Vector(project(u)), Vector(project(v))
    if pu.length > EPS:
        pu.normalize()
    if pv.length > EPS:
        pv.normalize()
    horizontal_u = abs(pu.x) + abs(pv.y) >= abs(pv.x) + abs(pu.y)
    horizontal, vertical = (Vector(u), Vector(v)) if horizontal_u else (Vector(v), Vector(u))
    hp, vp = (pu, pv) if horizontal_u else (pv, pu)
    if hp.x < 0:
        horizontal.negate()
    if vp.y < 0:
        vertical.negate()
    return {'RIGHT': horizontal, 'LEFT': -horizontal, 'UP': vertical, 'DOWN': -vertical}


def choose_sector(delta, deadzone=14):
    x, y = delta
    if math.hypot(x, y) < deadzone:
        return None
    return ('RIGHT' if x > 0 else 'LEFT') if abs(x) >= abs(y) else ('UP' if y > 0 else 'DOWN')
