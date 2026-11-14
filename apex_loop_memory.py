"""Release captured clip intermediates in uncached native loops."""

import gc

import nodes

from comfy_execution.caching import BasicCache, HierarchicalCache, LRUCache, NullCache, RAMPressureCache
from comfy_execution.graph_utils import is_link


def _loop_owner(graph, node_id):
    parent = graph.get_parent_node_id(node_id)
    while parent is not None:
        if graph.get_node(parent)["class_type"] == "StartLoop":
            return parent
        parent = graph.get_parent_node_id(parent)
    return None


def _remove_output(cache, node_id, protected):
    if isinstance(cache, NullCache):
        return False
    if isinstance(cache, HierarchicalCache):
        cache = cache._get_cache_for(node_id)
    if cache is None or not cache.initialized:
        return False
    key = cache.cache_key_set.get_data_key(node_id)
    if key not in cache.cache or id(cache.cache[key]) in protected:
        return False
    del cache.cache[key]
    if isinstance(cache, LRUCache):
        cache.used_generation.pop(key, None)
        cache.children.pop(key, None)
    if isinstance(cache, RAMPressureCache):
        cache.timestamps.pop(key, None)
    return True


def release_captured_loop_outputs(graph, execution_list, node_id):
    """Drop completed ancestors after capture, preserving pending consumers."""
    if graph is None or execution_list is None:
        return 0
    owner = _loop_owner(graph, node_id)
    if owner is None or graph.get_node(owner)["inputs"].get("cache_iterations", False) is not False:
        return 0

    ancestors = set()
    sources = [node_id]
    while sources:
        current = sources.pop()
        for value in graph.get_node(current).get("inputs", {}).values():
            if not is_link(value):
                continue
            source = value[0]
            if source not in ancestors and _loop_owner(graph, source) == owner:
                ancestors.add(source)
                sources.append(source)

    pending = execution_list.pendingNodes
    still_needed = {
        value[0]
        for consumer in pending if consumer != node_id
        for value in graph.get_node(consumer).get("inputs", {}).values()
        if is_link(value)
    }
    protected = {
        id(entry) for source in still_needed
        if (entry := execution_list.output_cache.get_local(source)) is not None
    }
    released = sum(
        _remove_output(execution_list.output_cache, source, protected)
        for source in ancestors - set(pending) - still_needed
    )
    if released:
        gc.collect()
    return released


def release_completed_outputs(graph, execution_list, node_id):
    """Release finished current-loop outputs, or upstream intermediates outside a loop."""
    if graph is None or execution_list is None:
        return 0, "no_execution_context"
    if not isinstance(execution_list.output_cache, (BasicCache, NullCache)):
        return 0, "unsupported_cache"
    owner = _loop_owner(graph, node_id)
    if owner is not None:
        if graph.get_node(owner)["inputs"].get("cache_iterations", False) is not False:
            return 0, "cached_loop_preserved"
        candidates = {key for key in graph.all_node_ids() if _loop_owner(graph, key) == owner}
        scope = "current_loop"
    else:
        candidates = set()
        sources = [node_id]
        while sources:
            current = sources.pop()
            for value in graph.get_node(current).get("inputs", {}).values():
                if is_link(value) and value[0] not in candidates:
                    candidates.add(value[0])
                    sources.append(value[0])
        # Expansion outputs can be absent from their wrapper's original inputs.
        for key in graph.all_node_ids():
            parent = graph.get_parent_node_id(key)
            while parent is not None:
                if parent in candidates:
                    candidates.add(key)
                    break
                parent = graph.get_parent_node_id(parent)
        candidates = {key for key in candidates if _loop_owner(graph, key) is None}
        scope = "upstream"

    pending = execution_list.pendingNodes
    needed = {
        value[0]
        for consumer in pending if consumer != node_id
        for value in graph.get_node(consumer).get("inputs", {}).values()
        if is_link(value)
    }
    protected = {
        id(entry) for key in needed
        if (entry := execution_list.output_cache.get_local(key)) is not None
    }
    # Expanded and lazy readers also hold bindings in the execution list.
    for consumer, bindings in execution_list.execution_cache.items():
        if consumer in pending and consumer != node_id:
            needed.update(bindings)
            protected.update(id(entry) for entry in bindings.values() if entry is not None)

    model_types = {"MODEL", "CLIP", "VAE", "CONTROL_NET", "LATENT_UPSCALE_MODEL"}
    released = 0
    for key in candidates - set(pending) - needed - {node_id}:
        node_class = nodes.NODE_CLASS_MAPPINGS.get(graph.get_node(key)["class_type"])
        if owner is None and node_class is not None and model_types.intersection(node_class.RETURN_TYPES):
            continue
        released += _remove_output(execution_list.output_cache, key, protected)
    return released, scope
