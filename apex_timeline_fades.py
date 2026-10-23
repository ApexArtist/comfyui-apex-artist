"""Clip fade envelopes and short transition renders for the timeline."""

import hashlib
import json
import os
import uuid


def clamp_fades(clip):
    duration = float(clip['duration'])
    for side in ('in', 'out'):
        clip['fade_' + side] = min(duration, max(0, float(clip.get('fade_' + side, 0))))


def available_start(track, start, duration):
    candidates = {0, start, *(clip['start'] + clip['duration'] for clip in track['clips']),
                  *(max(0, clip['start'] - duration) for clip in track['clips'])}
    available = [time for time in candidates if all(time + duration <= clip['start'] + 1e-6
                 or time >= clip['start'] + clip['duration'] - 1e-6 for clip in track['clips'])]
    return min(available, key=lambda time: (abs(time - start), time))


def clear_auto_fades(track, clip):
    for item in track['clips']:
        for side in ('in', 'out'):
            key = 'auto_fade_' + side
            if key in item and (item is clip or item[key] == clip['id']):
                item.pop(key)
                item['fade_' + side] = 0


def join_fades(track, clip, fps):
    ordered = sorted(track['clips'], key=lambda item: item['start'])
    for left, right in zip(ordered, ordered[1:]):
        if clip not in (left, right):
            continue
        overlap = left['start'] + left['duration'] - right['start']
        # A contained clip is an overlay, not an end-to-start transition.
        if overlap < -0.5 / fps or right['start'] + right['duration'] < left['start'] + left['duration'] - .5 / fps:
            continue
        duration = min(overlap if overlap > .5 / fps else .25, left['duration'], right['duration'])
        left.update(fade_out=duration, auto_fade_out=right['id'])
        right.update(fade_in=duration, auto_fade_in=left['id'])


def fade_value(clip, time, skip_out=False):
    local = time - clip['start']
    incoming = clip.get('fade_in', 0)
    outgoing = 0 if skip_out else clip.get('fade_out', 0)
    return max(0, min(1, local / incoming if incoming else 1)) * max(0, min(1, (clip['duration'] - local) / outgoing if outgoing else 1))


def active_layers(project, time, base_index=0):
    layers = [clip for track in sorted(project['tracks'], key=lambda item: item['index']) if track['index'] >= base_index
              for clip in track['clips'] if clip['start'] <= time < clip['start'] + clip['duration']]
    incoming = {clip.get('auto_fade_in'): clip for clip in layers if clip.get('auto_fade_in')}
    return [(clip, clip['id'] in incoming and incoming[clip['id']]['start'] < clip['start'] + clip['duration']) for clip in layers]


def fade_spans(project, fps, duration, base_index=0):
    total = round(duration * fps)
    boundaries = {0, total}
    for track in project['tracks']:
        if track['index'] < base_index:
            continue
        for clip in track['clips']:
            for time in (clip['start'], clip['start'] + clip.get('fade_in', 0),
                         clip['start'] + clip['duration'] - clip.get('fade_out', 0), clip['start'] + clip['duration']):
                boundaries.add(max(0, min(total, round(time * fps))))
    times = sorted(boundaries)
    return [(start / fps, (end - start) / fps, active_layers(project, (start + end) / (2 * fps), base_index))
            for start, end in zip(times, times[1:]) if end > start]


def render_fade_span(project, store, layers, start, duration, reference, ffmpeg):
    # Opaque upper clips hide lower layers, including their missing sources.
    for index in range(len(layers) - 1, -1, -1):
        clip, skip_out = layers[index]
        if min(fade_value(clip, start, skip_out), fade_value(clip, start + duration, skip_out)) >= 1:
            layers = layers[index:]
            break
    paths = [store.render_asset_path(project, clip['asset_id'], reference) for clip, _ in layers]
    identity = [(str(path), path.stat().st_size, path.stat().st_mtime_ns) for path in paths]
    key = hashlib.sha256(json.dumps([layers, start, duration, reference, identity], sort_keys=True).encode()).hexdigest()
    directory = store.project_dir(project['project_id']) / 'render_cache'
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / ('fade-' + key + '.mp4')
    if destination.is_file():
        return destination
    width, height, fps = reference['width'], reference['height'], reference['frame_rate']
    args = ['-filter_complex_threads', '1', '-f', 'lavfi', '-i', f'color=c=black:s={width}x{height}:r={fps}:d={duration}']
    filters = ['[0:v]format=gbrp[base0]']
    for index, ((clip, skip_out), path) in enumerate(zip(layers, paths), 1):
        source = clip.get('source_in', 0) + start - clip['start']
        args += ['-ss', str(max(0, source)), '-t', str(duration), '-i', str(path)]
        filters.append(f'[{index}:v]fps={fps},setpts=PTS-STARTPTS,format=gbrp[clip{index}]')
        local = f'(T+{start - clip["start"]:.12f})'
        incoming = clip.get('fade_in', 0)
        outgoing = 0 if skip_out else clip.get('fade_out', 0)
        alpha_in = f'min(1,max(0,{local}/{incoming:.12f}))' if incoming else '1'
        alpha_out = f'min(1,max(0,({clip["duration"]:.12f}-{local})/{outgoing:.12f}))' if outgoing else '1'
        alpha = f'({alpha_in}*{alpha_out})'
        filters.append(f"[base{index-1}][clip{index}]blend=all_expr='A*(1-{alpha})+B*{alpha}':shortest=1[base{index}]")
    filters.append(f'[base{len(layers)}]format=yuv420p[out]')
    temporary = directory / (key + '.' + uuid.uuid4().hex + '.mp4')
    try:
        ffmpeg(args + ['-filter_complex', ';'.join(filters), '-map', '[out]', '-an', '-frames:v', str(round(duration * fps)),
                       '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', str(temporary)])
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
