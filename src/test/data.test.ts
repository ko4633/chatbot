import { describe, expect, it } from 'vitest';
import { factionsData, regionsData } from '../core/data';

describe('data loading', () => {
  it('loads 551년 봄 as the start date', () => {
    expect(regionsData.startYear).toBe(551);
    expect(regionsData.startSeason).toBe('spring');
  });

  it('loads every region with historical ownership', () => {
    const byId = Object.fromEntries(regionsData.regions.map((r) => [r.id, r]));
    expect(byId.pyeongyang.owner).toBe('goguryeo');
    expect(byId.pyeongyang.capital).toBe(true);
    expect(byId.hanseong.owner).toBe('baekje');
    expect(byId.sabi.owner).toBe('baekje');
    expect(byId.sabi.capital).toBe(true);
    expect(byId.seorabeol.owner).toBe('silla');
    expect(byId.seorabeol.capital).toBe(true);
    expect(byId.daegaya.owner).toBe('gaya');
    expect(byId.daegaya.capital).toBe(true);
    expect(byId.yoseo.owner).toBe('jungwon');
    expect(byId.wa.owner).toBe('wa');
  });

  it('keeps adjacency symmetric for land and sea routes', () => {
    const byId = Object.fromEntries(regionsData.regions.map((r) => [r.id, r]));
    for (const region of regionsData.regions) {
      for (const adj of region.adjacent) {
        const target = byId[adj.to];
        expect(target, `${adj.to} referenced from ${region.id} must exist`).toBeDefined();
        const back = target.adjacent.find((a) => a.to === region.id);
        expect(back, `${target.id} should list ${region.id} back`).toBeDefined();
        expect(back?.type).toBe(adj.type);
      }
    }
  });

  it('loads faction initial values and relations', () => {
    const byId = Object.fromEntries(factionsData.factions.map((f) => [f.id, f]));
    expect(byId.goguryeo.color).toBe('#9E2B25');
    expect(byId.baekje.color).toBe('#2C4F7C');
    expect(byId.silla.color).toBe('#B8912A');
    expect(byId.gaya.color).toBe('#4F6B45');
    const gRelation = factionsData.initialRelations.find(
      (r) => (r.a === 'goguryeo' && r.b === 'baekje') || (r.a === 'baekje' && r.b === 'goguryeo')
    );
    expect(gRelation?.value).toBe(-50);
  });
});
