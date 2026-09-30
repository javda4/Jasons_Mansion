/**
 * Typed event bus — the boundary between runtime/application systems and game systems (§2.4).
 * Systems publish facts; nobody reaches into another system's objects.
 */
export interface EventMap {
  'app:ready': void;
  'app:paused': { paused: boolean };
  'quality:changed': { tier: QualityTier };
  'zone:entered': { zoneId: string };
  'zone:state': { zoneId: string; state: string };
  'ui:toast': { text: string };
  'door:moved': { id: string; opening: boolean; position: { x: number; y: number; z: number } };
  'interaction:focus': { id: string; prompt: string } | null;
  'interaction:activated': { id: string; interactionType: string; [key: string]: unknown };
}

export type QualityTier = 'high' | 'medium' | 'low';

type Handler<T> = (payload: T) => void;

export class EventBus {
  private handlers = new Map<keyof EventMap, Set<Handler<never>>>();

  on<K extends keyof EventMap>(type: K, handler: Handler<EventMap[K]>): () => void {
    let set = this.handlers.get(type);
    if (!set) this.handlers.set(type, (set = new Set()));
    set.add(handler as Handler<never>);
    return () => set.delete(handler as Handler<never>);
  }

  emit<K extends keyof EventMap>(type: K, ...[payload]: EventMap[K] extends void ? [] : [EventMap[K]]): void {
    this.handlers.get(type)?.forEach((h) => (h as Handler<EventMap[K]>)(payload as EventMap[K]));
  }
}
