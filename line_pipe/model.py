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


def bend_floor(diameter):
    # mathutils coordinates are float32. Reserve only a rounding guard, not a gap.
    return diameter / 2 + diameter * 2 ** -16


def fillet_radii(points, radius, pipe_radius=0.0):
    """Fit local radii under the maximum, sharing short segments between fillets."""
    points = [Vector(p) for p in points]
    if not math.isfinite(radius) or radius <= pipe_radius:
        raise ValueError('bad_radius')
    lengths = [(b - a).length for a, b in zip(points, points[1:])]
    radii = [min(radius, before, after) for before, after in zip(lengths, lengths[1:])]
    lower = bend_floor(pipe_radius * 2)
    tolerance = max(pipe_radius * 2, min(radii, default=radius)) * 2 ** -22
    if any(value < lower - tolerance or value <= pipe_radius for value in radii):
        raise ValueError('fit')
    for index, length in enumerate(lengths[1:-1]):
        before, after = radii[index:index + 2]
        if before + after > length:
            # Share the available inner radii proportionally, preserving positivity.
            available = length - 2 * lower
            if available < -tolerance:
                raise ValueError('fit')
            inner_total = max(0.0, before - lower) + max(0.0, after - lower)
            scale = max(0.0, available) / inner_total if inner_total else 0.0
            radii[index] = lower + max(0.0, before - lower) * scale
            radii[index + 1] = lower + max(0.0, after - lower) * scale
    return radii


def rounded_samples(points, radius, steps, pipe_radius=0.0):
    """Return sampled positions and exact tangents, including zero-length straights."""
    points = [Vector(p) for p in points]
    if len(points) < 2:
        return []
    radii = fillet_radii(points, radius, pipe_radius)
    result = [(points[0], (points[1] - points[0]).normalized())]
    for index in range(1, len(points) - 1):
        previous, corner, following = points[index - 1:index + 2]
        incoming, outgoing = corner - previous, following - corner
        incoming.normalize()
        outgoing.normalize()
        angle = math.acos(max(-1.0, min(1.0, incoming.dot(outgoing))))
        if angle < EPS:
            continue
        if abs(angle - math.pi / 2) > 1e-4:
            raise ValueError('Route corners must be perpendicular')
        local_radius = radii[index - 1]
        start = corner - incoming * local_radius
        center = start + outgoing * local_radius
        radial = -outgoing
        tolerance = max(local_radius, pipe_radius * 2) * 2 ** -20
        if (result[-1][0] - start).length > tolerance:
            result.append((start, incoming))
        for step in range(1, steps + 1):
            theta = math.pi / 2 * step / steps
            position = center + local_radius * (radial * math.cos(theta) + incoming * math.sin(theta))
            tangent = outgoing * math.sin(theta) + incoming * math.cos(theta)
            result.append((position, tangent))
    tolerance = max(radii[-1] if radii else (points[-1] - points[0]).length, pipe_radius * 2) * 2 ** -20
    if (result[-1][0] - points[-1]).length > tolerance:
        result.append((points[-1], (points[-1] - points[-2]).normalized()))
    return result


def rounded_path(points, radius, steps, pipe_radius=0.0):
    return [position for position, _ in rounded_samples(points, radius, steps, pipe_radius)]


class Route:
    def __init__(self, origin, direction, diameter, radius, axis_initial=False):
        if not all(math.isfinite(v) and v > 0 for v in (diameter, radius)) or radius < bend_floor(diameter):
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
    def minimum(self):
        return bend_floor(self.diameter) if len(self.points) > 1 else 0.0

    @property
    def turn_minimum(self):
        return bend_floor(self.diameter) * (2 if len(self.points) > 1 else 1)

    @property
    def preview_length(self):
        return min(self.radius, self.length / (2 if len(self.points) > 1 else 1))

    @property
    def tip(self):
        return self.points[-1] + self.heading * self.length

    def extend(self, length):
        self.length = max(self.minimum, float(length))

    def begin_turn(self):
        if self.length < self.turn_minimum:
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
            outgoing_length = self.preview_length
            self.history.append((self.heading.copy(), self.u.copy(), self.v.copy(), self.length))
            self.points.append(self.tip)
            rotation = self.heading.rotation_difference(self.candidate)
            self.u, self.v = rotation @ self.u, rotation @ self.v
            self.heading = self.candidate.copy()
            self.length = outgoing_length
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
            result.append(self.tip + self.candidate * self.preview_length)
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
