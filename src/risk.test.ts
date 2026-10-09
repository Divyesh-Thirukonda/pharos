import { describe, expect, it } from 'vitest';
import { predictConflict, SCENARIOS, type Actor } from './risk';

const actor = (id: string, values: Partial<Actor> = {}): Actor => ({
  id, kind: 'vehicle', x: 0, y: 0, vx: 0, vy: 0, width: 2, length: 2, ...values,
});

describe('illustrative constant-velocity forecast', () => {
  it('finds converging paths and gives the first footprint contact', () => {
    const forecast = predictConflict([
      actor('car', { x: -6, vx: 2 }),
      actor('walker', { y: -6, vy: 2 }),
    ]);
    expect(forecast.conflict).toEqual({ time: 2, x: -1, y: -1, actorIds: ['car', 'walker'] });
    expect(forecast.closestApproach).toBe(0);
  });

  it('detects a fast conflict occurring between rendering samples', () => {
    const forecast = predictConflict([
      actor('car', { x: -5, vx: 100 }), actor('stopped'),
    ], 1, 1);
    expect(forecast.conflict?.time).toBeCloseTo(0.03);
    expect(forecast.samples).toHaveLength(2);
  });

  it('keeps separated parallel paths clear and reports edge clearance', () => {
    const forecast = predictConflict([
      actor('one', { vx: 2 }), actor('two', { y: 5, vx: 2 }),
    ]);
    expect(forecast.conflict).toBeNull();
    expect(forecast.closestApproach).toBeCloseTo(3);
  });

  it('does not flag a vehicle stopped before the crossing', () => {
    const scenario = SCENARIOS.find(({ id }) => id === 'safe-yield')!;
    const forecast = predictConflict(scenario.actors);
    expect(forecast.conflict).toBeNull();
    expect(forecast.closestApproach).toBeCloseTo(1.85);
  });

  it('does not report a conflict beyond the requested horizon', () => {
    const actors = [actor('moving', { x: -10, vx: 2 }), actor('still')];
    expect(predictConflict(actors, 3).conflict).toBeNull();
    expect(predictConflict(actors, 3).closestApproach).toBeCloseTo(2);
    expect(predictConflict(actors, 4).conflict?.time).toBe(4);
  });

  it('reports existing overlap at time zero even when stationary', () => {
    const forecast = predictConflict([actor('one'), actor('two', { x: 1 })], 0);
    expect(forecast.conflict?.time).toBe(0);
    expect(forecast.samples).toHaveLength(1);
  });

  it('computes closest diagonal approach between sample times', () => {
    const forecast = predictConflict([
      actor('origin'), actor('passing', { x: 5, y: 3, vx: -1, vy: 1 }),
    ], 3, 3);
    expect(forecast.conflict).toBeNull();
    expect(forecast.closestApproach).toBeCloseTo(Math.sqrt(8));
  });

  it('selects the earliest conflict among multiple pairs', () => {
    const forecast = predictConflict([
      actor('moving', { x: -6, vx: 2 }),
      actor('late', { x: 1 }),
      actor('early', { x: -2, y: 0 }),
    ]);
    expect(forecast.conflict?.actorIds).toEqual(['moving', 'early']);
    expect(forecast.conflict?.time).toBe(1);
  });

  it('includes the horizon once when the step does not divide it', () => {
    const forecast = predictConflict([actor('moving', { vx: 2 })], 1, 0.3);
    expect(forecast.samples.map(({ time }) => time)).toEqual([0, 0.3, 0.6, 0.8999999999999999, 1]);
    expect(forecast.samples.at(-1)?.actors[0].x).toBe(2);
    expect(forecast.closestApproach).toBe(Infinity);
  });

  it('does not mutate inputs or retain references to actor objects', () => {
    const input = Object.freeze([Object.freeze(actor('moving', { vx: 2 })), Object.freeze(actor('other', { y: 5 }))]);
    const before = JSON.stringify(input);
    const forecast = predictConflict(input as unknown as Actor[]);
    forecast.samples[0].actors[0].x = 999;
    expect(JSON.stringify(input)).toBe(before);
  });

  it('handles an empty scene without fabricating a conflict', () => {
    const forecast = predictConflict([]);
    expect(forecast.conflict).toBeNull();
    expect(forecast.closestApproach).toBe(Infinity);
    expect(forecast.samples.every(({ actors }) => actors.length === 0)).toBe(true);
  });

  it.each([NaN, Infinity, -Infinity])('rejects nonfinite geometry %s', (value) => {
    expect(() => predictConflict([actor('bad', { x: value })])).toThrow(RangeError);
    expect(() => predictConflict([actor('bad', { vx: value })])).toThrow(RangeError);
    expect(() => predictConflict([actor('bad', { width: value })])).toThrow(RangeError);
  });

  it('rejects invalid time, dimensions, ids, and numerical overflow', () => {
    for (const horizon of [-1, Infinity, NaN]) expect(() => predictConflict([], horizon)).toThrow(RangeError);
    for (const step of [0, -1, Infinity, NaN]) expect(() => predictConflict([], 3, step)).toThrow(RangeError);
    expect(() => predictConflict([], 3, 0.00001)).toThrow(RangeError);
    expect(() => predictConflict([actor('bad', { length: 0 })])).toThrow(RangeError);
    expect(() => predictConflict([actor('duplicate'), actor('duplicate')])).toThrow(TypeError);
    expect(() => predictConflict([actor('')])).toThrow(TypeError);
    expect(() => predictConflict([actor('huge', { vx: Number.MAX_VALUE })])).toThrow(RangeError);
    expect(() => predictConflict([
      actor('left', { x: -Number.MAX_VALUE }), actor('right', { x: Number.MAX_VALUE }),
    ])).toThrow(RangeError);
  });

  it('provides two clearly illustrative conflicts and one safe scenario', () => {
    expect(SCENARIOS.map(({ actors }) => predictConflict(actors).conflict !== null)).toEqual([true, true, false]);
  });
});
