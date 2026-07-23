# ComfyUI DOM Widget Patterns & Best Practices

## Critical Knowledge: Pointer Events Blocking Issue

### The Problem
When ComfyUI's `addDOMWidget()` creates a widget, it generates a **wrapper element hierarchy**:
```
.widget-wrapper (parent container - created by ComfyUI)
  └── widget.element (your DOM element wrapper)
      └── your actual content (e.g., div, video, canvas)
```

**BOTH the wrapper AND its parent can intercept pointer events**, even when:
- Height is 0
- Display is none
- Visibility is hidden
- Position is absolute

This creates an "invisible wall" that blocks clicks and mouse wheel events on nodes below.

## Native Node Image Preview Pattern

When a node needs to show an image preview on the node canvas, use ComfyUI's native preview mechanism by assigning loaded `Image` objects to `node.imgs`. This matches native Preview Image / Load Image behavior and avoids layout problems from custom canvas widgets. Native-style preview updates should redraw the canvas without forcing node size changes.

### Correct Pattern
```javascript
function setNodePreview(node, imageUrl) {
    const img = new Image();
    img.onload = () => {
        node.imgs = [img];
        node.imageIndex = 0;
        refreshNodePreview(node);
    };
    img.onerror = () => clearNodePreview(node);
    img.src = imageUrl;
}

function clearNodePreview(node) {
    node.imgs = [];
    refreshNodePreview(node);
}

function refreshNodePreview(node) {
    if (node.setDirtyCanvas) node.setDirtyCanvas(true, true);
    else node.graph?.setDirtyCanvas(true, true);
}
```

### Mistake to Avoid
Do **not** create a custom `addCustomWidget()` just to draw a preview image with `ctx.drawImage()`. Manual draw coordinates are easy to get wrong because widget width, node padding, zoom, and frontend layout can differ across ComfyUI versions. This caused the Apex LoRA Loader selected preview to look stretched/shifted/clipped until it was changed to `node.imgs`.

### Real-World Example
`web/apex_lora_loader.js` now loads the selected LoRA preview image, sets `node.imgs = [img]`, sets `node.imageIndex = 0`, and clears with `node.imgs = []` when no preview exists. It only dirties/redraws the canvas and intentionally does not call `node.setSize(node.computeSize())` during image changes, preserving the user's node size like native Load Image.

## Native-First UI Rule

Always use ComfyUI's native UI/rendering mechanisms when they exist. Do not invent custom canvas drawing, sizing, DOM overlays, or interaction models unless native ComfyUI/LiteGraph APIs cannot provide the needed behavior. Native behavior should be the default reference for custom nodes.

### The Solution Pattern

#### 1. Initial State Management
```javascript
// Always start with collapsed/hidden state for widgets that can be toggled
node._state = {
    widgetExpanded: false,  // Start collapsed!
    // ... other state
};
```

#### 2. Deferred Initialization
```javascript
// After addDOMWidget(), defer visibility updates to ensure elements exist
requestAnimationFrame(() => {
    requestAnimationFrame(() => {
        updateWidgetVisibility(node);
    });
});
```

**Why double requestAnimationFrame?**
- First frame: DOM widget wrappers are attached to DOM
- Second frame: wrapper.element and parentElement are available
- This prevents race conditions where elements don't exist yet

#### 3. Complete Pointer Events Disabling
```javascript
function hideWidget(widget) {
    if (!widget?.element) return;
    
    const wrapper = widget.element;
    const wrapperParent = wrapper.parentElement;
    
    // Disable on wrapper
    wrapper.style.pointerEvents = "none";
    wrapper.style.display = "none";
    wrapper.style.height = "0";
    wrapper.style.overflow = "hidden";
    wrapper.style.position = "absolute";
    wrapper.style.visibility = "hidden";
    wrapper.style.zIndex = "-9999";
    
    // CRITICAL: Also disable on parent!
    if (wrapperParent) {
        wrapperParent.style.pointerEvents = "none";
        wrapperParent.style.display = "none";
    }
}
```

#### 4. Proper Re-enabling
```javascript
function showWidget(widget) {
    if (!widget?.element) return;
    
    const wrapper = widget.element;
    const wrapperParent = wrapper.parentElement;
    
    // Remove properties to restore defaults
    wrapper.style.removeProperty('pointer-events');
    wrapper.style.removeProperty('display');
    wrapper.style.removeProperty('height');
    wrapper.style.removeProperty('overflow');
    wrapper.style.removeProperty('position');
    wrapper.style.removeProperty('visibility');
    wrapper.style.removeProperty('z-index');
    
    // Also restore parent
    if (wrapperParent) {
        wrapperParent.style.removeProperty('pointer-events');
        wrapperParent.style.removeProperty('display');
    }
}
```

#### 5. Post-Update Verification
```javascript
// After any visibility change, verify in next frames
requestAnimationFrame(() => {
    if (node.setDirtyCanvas) {
        node.setDirtyCanvas(true, true);
    }
    
    // Double-check pointer events persisted
    requestAnimationFrame(() => {
        if (!state.widgetExpanded && widget?.element) {
            const wrapper = widget.element;
            const wrapperParent = wrapper.parentElement;
            wrapper.style.pointerEvents = "none";
            if (wrapperParent) wrapperParent.style.pointerEvents = "none";
        }
    });
});
```

## Common Mistakes to Avoid

### ❌ WRONG: Only disabling inner content
```javascript
// This DOES NOT work - wrapper still blocks
dom.container.style.pointerEvents = "none";
dom.container.style.display = "none";
```

### ❌ WRONG: Only disabling widget.element
```javascript
// This is INCOMPLETE - parent still blocks
if (widget?.element) {
    widget.element.style.pointerEvents = "none";
}
```

### ❌ WRONG: Starting expanded
```javascript
// This causes blocking on first launch
browserExpanded: true  // Bad!
```

### ❌ WRONG: Immediate visibility update
```javascript
// Elements may not exist yet
addDOMWidget(...);
updateVisibility(node);  // Too soon!
```

### ✅ CORRECT: Complete pattern
```javascript
// 1. Start collapsed
browserExpanded: false

// 2. Create widgets
const widget = node.addDOMWidget(...);

// 3. Defer initialization
requestAnimationFrame(() => {
    requestAnimationFrame(() => {
        updateVisibility(node);
    });
});

// 4. In updateVisibility, handle BOTH levels
if (widget?.element) {
    const wrapper = widget.element;
    const wrapperParent = wrapper.parentElement;
    
    wrapper.style.pointerEvents = "none";
    if (wrapperParent) {
        wrapperParent.style.pointerEvents = "none";
    }
}
```

## GitHub Issue Reference
- **Issue #11006**: DOM widget overlays intercept pointer events on collapsed nodes
- **Fix merged**: April 2026
- **Core issue**: Parent element wrapping behavior not documented

## Testing Checklist
When implementing DOM widgets that can be hidden:

- [ ] Widget starts in collapsed/hidden state
- [ ] Initial visibility update is deferred (double RAF)
- [ ] Both wrapper AND parent get pointer-events disabled
- [ ] On first node launch, can click/scroll on nodes below
- [ ] After first toggle, behavior still works
- [ ] After workflow save/load, behavior still works
- [ ] Multiple instances of node don't interfere with each other

## Real-World Example
For DOM-widget visibility handling, follow the wrapper + parent pointer-events pattern above. For node image previews, follow the `node.imgs` native preview pattern documented near the top of this file; `web/apex_lora_loader.js` is the current example.

## Summary
**The golden rule**: When hiding DOM widgets in ComfyUI, you MUST disable pointer-events on BOTH `widget.element` (the wrapper) AND `widget.element.parentElement` (the ComfyUI-created parent container). One level is never enough.
