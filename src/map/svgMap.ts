import { regionsData } from '../core/data';
import type { FactionId, GameState, RegionId } from '../core/types';

const SVG_NS = 'http://www.w3.org/2000/svg';

const VIEW_W = 760;
const VIEW_H = 980;
const MIN_SCALE = 0.5;
const MAX_SCALE = 4;

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

function radiusFor(terrain: string): number {
  switch (terrain) {
    case 'capital':
      return 22;
    case 'external':
      return 12;
    default:
      return 16;
  }
}

export interface MapView {
  update(state: GameState, selected: RegionId | null): void;
}

export function createMapView(
  container: HTMLElement,
  factionColors: Record<FactionId, string>,
  onRegionTap: (regionId: RegionId) => void
): MapView {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${VIEW_W} ${VIEW_H}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

  const world = document.createElementNS(SVG_NS, 'g');
  svg.appendChild(world);

  const edgeLayer = document.createElementNS(SVG_NS, 'g');
  edgeLayer.setAttribute('class', 'edge-layer');
  world.appendChild(edgeLayer);

  const nodeLayer = document.createElementNS(SVG_NS, 'g');
  nodeLayer.setAttribute('class', 'node-layer');
  world.appendChild(nodeLayer);

  container.innerHTML = '';
  container.appendChild(svg);

  const byId = Object.fromEntries(regionsData.regions.map((r) => [r.id, r]));

  // 연결선: 각 쌍은 한 번만 그린다.
  const drawnPairs = new Set<string>();
  for (const region of regionsData.regions) {
    for (const adj of region.adjacent) {
      const key = [region.id, adj.to].sort().join('|');
      if (drawnPairs.has(key)) continue;
      drawnPairs.add(key);
      const target = byId[adj.to];
      if (!target) continue;
      const line = document.createElementNS(SVG_NS, 'line');
      line.setAttribute('x1', String(region.x));
      line.setAttribute('y1', String(region.y));
      line.setAttribute('x2', String(target.x));
      line.setAttribute('y2', String(target.y));
      line.setAttribute('class', adj.type === 'sea' ? 'edge-sea' : 'edge-land');
      edgeLayer.appendChild(line);
    }
  }

  const nodeCircles: Record<RegionId, SVGCircleElement> = {};
  const nodeGroups: Record<RegionId, SVGGElement> = {};

  for (const region of regionsData.regions) {
    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', 'region-node');
    g.setAttribute('data-region', region.id);
    g.setAttribute('transform', `translate(${region.x}, ${region.y})`);

    const circle = document.createElementNS(SVG_NS, 'circle');
    circle.setAttribute('class', 'body');
    circle.setAttribute('r', String(radiusFor(region.terrain)));
    g.appendChild(circle);

    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('y', String(radiusFor(region.terrain) + 14));
    label.setAttribute('font-size', region.terrain === 'external' ? '11' : '13');
    label.textContent = region.name;
    g.appendChild(label);

    g.addEventListener('click', () => onRegionTap(region.id));

    nodeLayer.appendChild(g);
    nodeCircles[region.id] = circle;
    nodeGroups[region.id] = g;
  }

  // --- 팬/줌 ---
  let view: ViewBox = { x: 0, y: 0, w: VIEW_W, h: VIEW_H };
  const pointers = new Map<number, { x: number; y: number }>();
  let lastPinchDist = 0;
  let dragStart: { x: number; y: number; view: ViewBox } | null = null;

  function applyView() {
    svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.h}`);
  }

  function clampView(v: ViewBox): ViewBox {
    const w = Math.min(VIEW_W / MIN_SCALE, Math.max(VIEW_W / MAX_SCALE, v.w));
    const h = w * (VIEW_H / VIEW_W);
    let x = v.x;
    let y = v.y;
    x = Math.min(VIEW_W - w, Math.max(-w * 0.5, x));
    y = Math.min(VIEW_H - h, Math.max(-h * 0.5, y));
    return { x, y, w, h };
  }

  function clientToSvgPoint(clientX: number, clientY: number) {
    const rect = container.getBoundingClientRect();
    const relX = (clientX - rect.left) / rect.width;
    const relY = (clientY - rect.top) / rect.height;
    return { x: view.x + relX * view.w, y: view.y + relY * view.h };
  }

  function zoomAt(clientX: number, clientY: number, factor: number) {
    const focus = clientToSvgPoint(clientX, clientY);
    const newW = view.w / factor;
    const newH = view.h / factor;
    const x = focus.x - (focus.x - view.x) * (newW / view.w);
    const y = focus.y - (focus.y - view.y) * (newH / view.h);
    view = clampView({ x, y, w: newW, h: newH });
    applyView();
  }

  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    zoomAt(e.clientX, e.clientY, factor);
  }, { passive: false });

  svg.addEventListener('pointerdown', (e) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      dragStart = { x: e.clientX, y: e.clientY, view: { ...view } };
    } else if (pointers.size === 2) {
      const pts = Array.from(pointers.values());
      lastPinchDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
    }
  });

  svg.addEventListener('pointermove', (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.size === 1 && dragStart) {
      const rect = container.getBoundingClientRect();
      const dx = ((e.clientX - dragStart.x) / rect.width) * dragStart.view.w;
      const dy = ((e.clientY - dragStart.y) / rect.height) * dragStart.view.h;
      view = clampView({ x: dragStart.view.x - dx, y: dragStart.view.y - dy, w: dragStart.view.w, h: dragStart.view.h });
      applyView();
    } else if (pointers.size === 2) {
      const pts = Array.from(pointers.values());
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      if (lastPinchDist > 0) {
        const factor = dist / lastPinchDist;
        const midX = (pts[0].x + pts[1].x) / 2;
        const midY = (pts[0].y + pts[1].y) / 2;
        zoomAt(midX, midY, factor);
      }
      lastPinchDist = dist;
    }
  });

  function endPointer(e: PointerEvent) {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) lastPinchDist = 0;
    if (pointers.size === 0) dragStart = null;
  }
  svg.addEventListener('pointerup', endPointer);
  svg.addEventListener('pointercancel', endPointer);
  svg.addEventListener('pointerleave', endPointer);

  applyView();

  function update(state: GameState, selected: RegionId | null) {
    for (const region of regionsData.regions) {
      const owner = state.regions[region.id]?.owner ?? region.owner;
      const color = factionColors[owner] ?? '#888888';
      nodeCircles[region.id].setAttribute('fill', color);
      nodeGroups[region.id].classList.toggle('selected', region.id === selected);
    }
  }

  return { update };
}
