"""Scoped output-cache keys for explicitly uncached music-loop expansions.

Native LoopIteration already uses a NaN fingerprint when iteration caching is
off. Its expanded descendants cannot reuse results between prompts. Preserve
that policy without copying their entire growing ancestry into every key.
Ordinary nodes and explicitly cached loops keep native input signatures.
"""
import uuid
import weakref

from comfy_execution.caching import BasicCache, CacheKeySetInputSignature, NullCache, to_hashable
from comfy_execution.graph_utils import is_link

_scopes = weakref.WeakKeyDictionary()


def _marked_owner(graph, node_id, owners):
    seen = set()
    parent = graph.get_parent_node_id(node_id)
    while parent is not None and parent not in seen:
        seen.add(parent)
        definition = graph.get_node(parent)
        if definition["class_type"] == "StartLoop":
            return parent if parent in owners and definition["inputs"].get("cache_iterations", False) is False else None
        parent = graph.get_parent_node_id(parent)
    return None


class _UncachedMusicLoopKeys(CacheKeySetInputSignature):
    async def get_node_signature(self, dynprompt, node_id):
        scope = _scopes.get(dynprompt)
        if scope is not None and _marked_owner(dynprompt, node_id, scope[1]) is not None:
            # NaN keeps external cache persistence disabled, as with native
            # uncached LoopIteration fingerprints. This key object is stable
            # within its key set, but never matches a different prompt.
            # Match the native signature container so RAM-pressure eviction can
            # compare tied priorities/timestamps alongside ordinary node keys.
            return to_hashable(("Apex uncached music loop", scope[0], node_id,
                                dynprompt.get_node(node_id)["class_type"], float("nan")))
        return await super().get_node_signature(dynprompt, node_id)


def enable_uncached_music_loop_keys(graph, execution_list, plan_node_id, require_uncached=False):
    if graph is None or execution_list is None:
        return {"status": "no_execution_context"}
    matching = {
        key for key in graph.all_node_ids()
        if graph.get_node(key)["class_type"] == "StartLoop"
        and is_link(graph.get_node(key)["inputs"].get("mode.num_iterations"))
        and graph.get_node(key)["inputs"]["mode.num_iterations"][0] == plan_node_id
    }
    if require_uncached and any(graph.get_node(key)["inputs"].get("cache_iterations", False) is not False for key in matching):
        raise ValueError("Apex music timing: keep Cache Iterations off on the scheduled render loop. This fresh-generation workflow releases completed clips between iterations.")
    owners = {key for key in matching if graph.get_node(key)["inputs"].get("cache_iterations", False) is False}
    if not owners:
        return {"status": "no_matching_uncached_music_loop"}
    cache = execution_list.output_cache
    if isinstance(cache, NullCache):
        return {"status": "native_cache_disabled"}
    supported = (CacheKeySetInputSignature, _UncachedMusicLoopKeys)
    caches = []
    todo = [cache]
    seen = set()
    while todo:
        current = todo.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if not isinstance(current, BasicCache) or current.key_class not in supported:
            raise ValueError("Apex music timing: the current output-cache implementation is unsupported by the scoped loop optimization.")
        if current.initialized and type(current.cache_key_set) not in supported:
            raise ValueError("Apex music timing: the current cache key set is unsupported by the scoped loop optimization.")
        if current.initialized and set(vars(current.cache_key_set)) != {"keys", "subcache_keys", "dynprompt", "is_changed_cache"}:
            raise ValueError("Apex music timing: the native cache key layout has changed; update Apex before using its loop optimization.")
        caches.append(current)
        todo.extend(current.subcaches.values())

    scope = _scopes.setdefault(graph, (uuid.uuid4().hex, set()))
    scope[1].update(owners)
    # Upgrade only this executor's output-cache instances. Root keys and all
    # existing entries are preserved; no core methods or global flags change.
    for current in caches:
        current.key_class = _UncachedMusicLoopKeys
        if current.initialized and type(current.cache_key_set) is CacheKeySetInputSignature:
            old = current.cache_key_set
            replacement = _UncachedMusicLoopKeys(old.dynprompt, [], old.is_changed_cache)
            replacement.keys = old.keys
            replacement.subcache_keys = old.subcache_keys
            current.cache_key_set = replacement
    return {"status": "scoped_uncached_iteration_keys", "loops": sorted(owners)}
