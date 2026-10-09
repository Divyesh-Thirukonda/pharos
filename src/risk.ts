/**
 * Illustrative scenario · not live detection.
 *
 * Constant-velocity geometry for an interactive demonstration only. This is not
 * a validated collision predictor or a real-world safety decision system.
 * Positions are rectangle centers in meters; length is the fixed x dimension
 * and width is the fixed y dimension. There is no inferred intent, probability,
 * perception, camera calibration, or road-user identification in this module.
 */
export interface Actor {
  id: string;
  kind: 'vehicle' | 'pedestrian' | 'cyclist';
  x: number;
  y: number;
  vx: number;
  vy: number;
  width: number;
  length: number;
}

export interface Forecast {
  samples: { time: number; actors: { id: string; x: number; y: number }[] }[];
  conflict: { time: number; x: number; y: number; actorIds: [string, string] } | null;
  /** Minimum distance between rectangle edges; Infinity when there is no pair. */
  closestApproach: number;
}

export interface Scenario {
  id: string;
  title: string;
  description: string;
  actors: Actor[];
  signal: string;
  intervention: string;
}

const EPSILON = 1e-9;
const MAX_SAMPLE_COUNT = 10_001;
// Preserve room for relative-coordinate subtraction and squared distances.
const MAX_SAFE_MAGNITUDE = Math.sqrt(Number.MAX_VALUE) / 16;

function validate(actors: Actor[], horizon: number, step: number): void {
  if (!Number.isFinite(horizon) || horizon < 0 || horizon > MAX_SAFE_MAGNITUDE) {
    throw new RangeError('horizonSeconds must be finite, nonnegative, and within numeric limits');
  }
  if (!Number.isFinite(step) || step <= 0) {
    throw new RangeError('stepSeconds must be finite and positive');
  }
  if (Math.ceil(horizon / step) + 1 > MAX_SAMPLE_COUNT) {
    throw new RangeError(`Forecast cannot exceed ${MAX_SAMPLE_COUNT} samples`);
  }
  const ids = new Set<string>();
  for (const actor of actors) {
    if (!actor.id || ids.has(actor.id)) throw new TypeError('Actor ids must be nonempty and unique');
    ids.add(actor.id);
    if (![actor.x, actor.y, actor.vx, actor.vy, actor.width, actor.length]
      .every(value => Number.isFinite(value) && Math.abs(value) <= MAX_SAFE_MAGNITUDE)) {
      throw new RangeError(`Actor ${actor.id} must have finite geometry and velocity within numeric limits`);
    }
    if (actor.width <= 0 || actor.length <= 0) {
      throw new RangeError(`Actor ${actor.id} dimensions must be positive`);
    }
    if (![actor.x + actor.vx * horizon, actor.y + actor.vy * horizon]
      .every(value => Number.isFinite(value) && Math.abs(value) <= MAX_SAFE_MAGNITUDE)) {
      throw new RangeError(`Actor ${actor.id} projected coordinates exceed numeric limits`);
    }
  }
}

/** Closed slab intervals: touching footprints conservatively count as conflict. */
function slab(position: number, velocity: number, extent: number): [number, number] | null {
  if (velocity === 0) return Math.abs(position) <= extent ? [-Infinity, Infinity] : null;
  const first = (-extent - position) / velocity;
  const last = (extent - position) / velocity;
  return [Math.min(first, last), Math.max(first, last)];
}

function pairGeometry(a: Actor, b: Actor) {
  return {
    px: b.x - a.x,
    py: b.y - a.y,
    vx: b.vx - a.vx,
    vy: b.vy - a.vy,
    ex: a.length / 2 + b.length / 2,
    ey: a.width / 2 + b.width / 2,
  };
}

function collisionTime(a: Actor, b: Actor, horizon: number): number | null {
  const { px, py, vx, vy, ex, ey } = pairGeometry(a, b);
  const x = slab(px, vx, ex);
  const y = slab(py, vy, ey);
  if (!x || !y) return null;
  const entry = Math.max(0, x[0], y[0]);
  const exit = Math.min(horizon, x[1], y[1]);
  return entry <= exit + EPSILON && entry <= horizon + EPSILON
    ? Math.min(horizon, entry)
    : null;
}

/** Exact minimum AABB clearance for two linearly moving rectangles. */
function clearance(a: Actor, b: Actor, horizon: number): number {
  const { px, py, vx, vy, ex, ey } = pairGeometry(a, b);
  const distanceAt = (time: number) => Math.hypot(
    Math.max(0, Math.abs(px + vx * time) - ex),
    Math.max(0, Math.abs(py + vy * time) - ey),
  );
  // Each breakpoint changes which rectangle edge defines the distance.
  const times = [0, horizon];
  for (const [position, velocity, extent] of [[px, vx, ex], [py, vy, ey]]) {
    if (velocity === 0) continue;
    for (const edge of [-extent, extent]) {
      const time = (edge - position) / velocity;
      if (time > 0 && time < horizon) times.push(time);
    }
  }
  times.sort((aTime, bTime) => aTime - bTime);
  let closest = Math.min(...times.map(distanceAt));
  for (let index = 0; index < times.length - 1; index += 1) {
    const start = times[index];
    const end = times[index + 1];
    const midpoint = (start + end) / 2;
    let numerator = 0;
    let denominator = 0;
    for (const [position, velocity, extent] of [[px, vx, ex], [py, vy, ey]]) {
      const middlePosition = position + velocity * midpoint;
      if (Math.abs(middlePosition) <= extent) continue;
      const offset = position - Math.sign(middlePosition) * extent;
      numerator += offset * velocity;
      denominator += velocity * velocity;
    }
    if (denominator > 0) {
      const minimumTime = Math.max(start, Math.min(end, -numerator / denominator));
      closest = Math.min(closest, distanceAt(minimumTime));
    }
  }
  return closest;
}

function overlapCenter(a: Actor, b: Actor, time: number): { x: number; y: number } {
  const ax = a.x + a.vx * time;
  const ay = a.y + a.vy * time;
  const bx = b.x + b.vx * time;
  const by = b.y + b.vy * time;
  return {
    x: (Math.max(ax - a.length / 2, bx - b.length / 2) + Math.min(ax + a.length / 2, bx + b.length / 2)) / 2,
    y: (Math.max(ay - a.width / 2, by - b.width / 2) + Math.min(ay + a.width / 2, by + b.width / 2)) / 2,
  };
}

export function predictConflict(actors: Actor[], horizonSeconds = 3, stepSeconds = 0.1): Forecast {
  validate(actors, horizonSeconds, stepSeconds);
  const samples: Forecast['samples'] = [];
  const sample = (time: number) => ({
    time,
    actors: actors.map(({ id, x, y, vx, vy }) => ({ id, x: x + vx * time, y: y + vy * time })),
  });
  const intervals = Math.ceil(horizonSeconds / stepSeconds);
  for (let index = 0; index < intervals; index += 1) samples.push(sample(index * stepSeconds));
  samples.push(sample(horizonSeconds));

  let conflict: Forecast['conflict'] = null;
  let closestApproach = Infinity;
  for (let first = 0; first < actors.length; first += 1) {
    for (let second = first + 1; second < actors.length; second += 1) {
      const a = actors[first];
      const b = actors[second];
      const time = collisionTime(a, b, horizonSeconds);
      closestApproach = Math.min(closestApproach, clearance(a, b, horizonSeconds));
      if (time !== null && (conflict === null || time < conflict.time)) {
        conflict = { time, ...overlapCenter(a, b, time), actorIds: [a.id, b.id] };
      }
    }
  }
  // Avoid a floating-point residual on footprints that touch exactly.
  if (conflict) closestApproach = 0;
  return { samples, conflict, closestApproach };
}

export const SCENARIOS: Scenario[] = [
  {
    id: 'turning-conflict',
    title: 'Turning into a crossing',
    description: 'The final, straight portion of a vehicle turn intersects a pedestrian’s path if both continue at their present speeds.',
    actors: [
      { id: 'vehicle-1', kind: 'vehicle', x: -9, y: 0, vx: 4, vy: 0, width: 1.9, length: 4.6 },
      { id: 'pedestrian-1', kind: 'pedestrian', x: 0, y: 5, vx: 0, vy: -1.5, width: 0.7, length: 0.7 },
    ],
    signal: 'Converging paths · pedestrian in turning path',
    intervention: 'Review turn calming and a leading pedestrian interval to separate the movements.',
  },
  {
    id: 'occluded-crossing',
    title: 'Emerging from an obstruction',
    description: 'An illustrative pedestrian emerges into an approaching vehicle’s path. The obstruction is scenario context, not a detected object.',
    actors: [
      { id: 'vehicle-1', kind: 'vehicle', x: -10, y: 0, vx: 5, vy: 0, width: 2, length: 4.6 },
      { id: 'pedestrian-1', kind: 'pedestrian', x: 0, y: -4, vx: 0, vy: 1.9, width: 0.7, length: 0.7 },
    ],
    signal: 'Converging paths · limited sightline scenario',
    intervention: 'Review daylighting and loading placement to improve visibility near the crossing.',
  },
  {
    id: 'safe-yield',
    title: 'Yielding before the crossing',
    description: 'The vehicle remains stopped before the crossing while the pedestrian passes. Their projected footprints remain separated.',
    actors: [
      { id: 'vehicle-1', kind: 'vehicle', x: -4.5, y: 0, vx: 0, vy: 0, width: 1.9, length: 4.6 },
      { id: 'pedestrian-1', kind: 'pedestrian', x: 0, y: 3, vx: 0, vy: -1.5, width: 0.7, length: 0.7 },
    ],
    signal: 'Separated paths · vehicle yielding',
    intervention: 'No conflict is projected within this illustrative horizon; maintain a clear crossing and sightlines.',
  },
];
