/**/**

 * Apex RGB Curve - Core Interface Controller * Apex RGB Curve - Core Interface

 * Professional Photoshop-style RGB curve editor * Professional RGB curve editor with separate channel controls

 */ */



export class ApexRGBCurveInterface {export class ApexRGBCurveInterface {

    constructor(canvas, widget) {    constructor(canvas, widget) {

        this.canvas = canvas;        this.canvas = canvas;

        this.ctx = canvas.getContext('2d');        this.ctx = canvas.getContext('2d');

        this.widget = widget;        this.widget = widget;

                

        // Interface state        // Current active channel

        this.activeChannel = 'rgb'; // 'rgb', 'red', 'green', 'blue'        this.activeChannel = 'master';

        this.selectedPoint = -1;        

        this.isDragging = false;        // Curve data for each channel

        this.showGrid = true;        this.curves = {

        this.gridOpacity = 0.3;            master: [[0, 0], [1, 1]],

                    red: [[0, 0], [1, 1]],

        // Curve data for each channel            green: [[0, 0], [1, 1]],

        this.curves = {            blue: [[0, 0], [1, 1]]

            rgb: [[0, 0], [1, 1]],      // Master RGB curve        };

            red: [[0, 0], [1, 1]],      // Red channel curve        

            green: [[0, 0], [1, 1]],    // Green channel curve        // UI state

            blue: [[0, 0], [1, 1]]      // Blue channel curve        this.selectedPoint = -1;

        };        this.isDragging = false;

                this.gridSize = 20;

        // Visual settings        

        this.pointRadius = 5;        // Channel colors

        this.lineWidth = 2;        this.channelColors = {

        this.colors = {            master: '#ffffff',

            background: '#2a2a2a',            red: '#ff4444',

            grid: '#444444',            green: '#44ff44',

            diagonal: '#666666',            blue: '#4444ff'

            rgb: '#ffffff',        };

            red: '#ff4444',        

            green: '#44ff44',        // Initialize

            blue: '#4488ff',        this.setupCanvas();

            point: '#ffffff',        this.bindEvents();

            pointSelected: '#ffff00',    }

            text: '#cccccc'    

        };    setupCanvas() {

                // Set up canvas styling

        // Channel visibility        this.canvas.style.cursor = 'crosshair';

        this.channelVisible = {        

            rgb: true,        // Parse initial widget value if exists

            red: false,        if (this.widget.value && this.widget.value.trim() !== '') {

            green: false,            this.parseCurveData(this.widget.value);

            blue: false        }

        };    }

            

        // Sub-components will be set by main interface    bindEvents() {

        this.visualization = null;        // Mouse events will be handled by the events module

        this.events = null;        // This is just setup for the core interface

        this.ui = null;    }

    }    

        parseCurveData(data) {

    // Channel management        try {

    setActiveChannel(channel) {            const parsed = JSON.parse(data);

        if (['rgb', 'red', 'green', 'blue'].includes(channel)) {            if (parsed && typeof parsed === 'object') {

            this.activeChannel = channel;                // Update curves with parsed data

            this.selectedPoint = -1;                for (const channel of ['master', 'red', 'green', 'blue']) {

            this.updateChannelVisibility();                    if (parsed[channel] && Array.isArray(parsed[channel])) {

            this.updateNodeWidget();                        this.curves[channel] = parsed[channel];

            this.redraw();                    }

        }                }

    }            }

            } catch (error) {

    updateChannelVisibility() {            console.warn('Failed to parse RGB curve data:', error);

        // Show only active channel and RGB if it's not RGB        }

        this.channelVisible = {    }

            rgb: this.activeChannel === 'rgb' || this.activeChannel !== 'rgb',    

            red: this.activeChannel === 'red',    updateNodeWidget() {

            green: this.activeChannel === 'green',         // Convert curves to JSON string for the node

            blue: this.activeChannel === 'blue'        const curveData = JSON.stringify(this.curves);

        };        this.widget.value = curveData;

                

        // Always show RGB as baseline unless we're editing it        // Trigger widget callback

        if (this.activeChannel !== 'rgb') {        if (this.widget.callback) {

            this.channelVisible.rgb = true;            this.widget.callback(curveData);

        }        }

    }    }

        

    // Point management    setActiveChannel(channel) {

    addPoint(x, y) {        if (this.channelColors[channel]) {

        const curve = this.curves[this.activeChannel];            this.activeChannel = channel;

                    this.selectedPoint = -1;

        // Convert canvas coordinates to curve coordinates            this.redraw();

        const curveX = this.canvasToCurveX(x);        }

        const curveY = this.canvasToCurveY(y);    }

            

        // Don't add points at the exact endpoints    getActiveCurve() {

        if (curveX <= 0.01 || curveX >= 0.99) return false;        return this.curves[this.activeChannel];

            }

        // Find insertion position    

        let insertIndex = curve.length;    setActiveCurve(points) {

        for (let i = 1; i < curve.length; i++) {        this.curves[this.activeChannel] = points;

            if (curve[i][0] > curveX) {        this.updateNodeWidget();

                insertIndex = i;    }

                break;    

            }    addPoint(x, y) {

        }        const curve = this.getActiveCurve();

                

        // Insert new point        // Convert canvas coordinates to curve coordinates

        curve.splice(insertIndex, 0, [curveX, curveY]);        const curveX = x / this.canvas.width;

        this.selectedPoint = insertIndex;        const curveY = 1 - (y / this.canvas.height);

                

        this.updateNodeWidget();        // Clamp values

        return true;        const clampedX = Math.max(0, Math.min(1, curveX));

    }        const clampedY = Math.max(0, Math.min(1, curveY));

            

    removePoint(index) {        // Don't add if too close to existing points

        const curve = this.curves[this.activeChannel];        for (let i = 0; i < curve.length; i++) {

                    const dx = Math.abs(curve[i][0] - clampedX);

        // Don't remove endpoint points (first and last)            const dy = Math.abs(curve[i][1] - clampedY);

        if (index <= 0 || index >= curve.length - 1) return false;            if (dx < 0.03 && dy < 0.03) {

                        return i; // Return existing point index

        curve.splice(index, 1);            }

        this.selectedPoint = -1;        }

                

        this.updateNodeWidget();        // Find insertion position to maintain sort order

        return true;        let insertIndex = curve.length;

    }        for (let i = 0; i < curve.length; i++) {

                if (curve[i][0] > clampedX) {

    movePoint(index, x, y) {                insertIndex = i;

        const curve = this.curves[this.activeChannel];                break;

        if (index < 0 || index >= curve.length) return false;            }

                }

        const curveX = this.canvasToCurveX(x);        

        const curveY = this.canvasToCurveY(y);        // Insert new point

                curve.splice(insertIndex, 0, [clampedX, clampedY]);

        // Constrain endpoints to their X positions        this.updateNodeWidget();

        if (index === 0) {        

            curve[0][1] = Math.max(0, Math.min(1, curveY));        return insertIndex;

            return true;    }

        } else if (index === curve.length - 1) {    

            curve[index][1] = Math.max(0, Math.min(1, curveY));    removePoint(index) {

            return true;        const curve = this.getActiveCurve();

        }        

                // Don't allow removal of first or last point

        // Constrain X between neighboring points        if (index <= 0 || index >= curve.length - 1) {

        const minX = curve[index - 1][0] + 0.01;            return false;

        const maxX = curve[index + 1][0] - 0.01;        }

        const constrainedX = Math.max(minX, Math.min(maxX, curveX));        

        const constrainedY = Math.max(0, Math.min(1, curveY));        curve.splice(index, 1);

                this.updateNodeWidget();

        curve[index][0] = constrainedX;        this.selectedPoint = -1;

        curve[index][1] = constrainedY;        

                return true;

        this.updateNodeWidget();    }

        return true;    

    }    updatePoint(index, x, y) {

            const curve = this.getActiveCurve();

    // Coordinate conversion        

    canvasToCurveX(canvasX) {        if (index < 0 || index >= curve.length) return;

        const margin = 30;        

        return Math.max(0, Math.min(1, (canvasX - margin) / (this.canvas.width - 2 * margin)));        // Convert canvas coordinates to curve coordinates

    }        const curveX = x / this.canvas.width;

            const curveY = 1 - (y / this.canvas.height);

    canvasToCurveY(canvasY) {        

        const margin = 30;        // Clamp values

        return Math.max(0, Math.min(1, 1 - (canvasY - margin) / (this.canvas.height - 2 * margin)));        const clampedX = Math.max(0, Math.min(1, curveX));

    }        const clampedY = Math.max(0, Math.min(1, curveY));

            

    curveToCanvasX(curveX) {        // For first and last points, only allow Y changes

        const margin = 30;        if (index === 0) {

        return margin + curveX * (this.canvas.width - 2 * margin);            curve[index] = [0, clampedY];

    }        } else if (index === curve.length - 1) {

                curve[index] = [1, clampedY];

    curveToCanvasY(curveY) {        } else {

        const margin = 30;            // For middle points, constrain X between neighbors

        return margin + (1 - curveY) * (this.canvas.height - 2 * margin);            const prevX = curve[index - 1][0];

    }            const nextX = curve[index + 1][0];

                const constrainedX = Math.max(prevX + 0.01, Math.min(nextX - 0.01, clampedX));

    // Point detection            

    findPointAt(x, y, tolerance = 10) {            curve[index] = [constrainedX, clampedY];

        const curve = this.curves[this.activeChannel];        }

                

        for (let i = 0; i < curve.length; i++) {        this.updateNodeWidget();

            const pointX = this.curveToCanvasX(curve[i][0]);    }

            const pointY = this.curveToCanvasY(curve[i][1]);    

                findNearestPoint(x, y, threshold = 15) {

            const distance = Math.sqrt((x - pointX) ** 2 + (y - pointY) ** 2);        const curve = this.getActiveCurve();

            if (distance <= tolerance) {        

                return i;        for (let i = 0; i < curve.length; i++) {

            }            const pointX = curve[i][0] * this.canvas.width;

        }            const pointY = (1 - curve[i][1]) * this.canvas.height;

                    

        return -1;            const dx = x - pointX;

    }            const dy = y - pointY;

                const distance = Math.sqrt(dx * dx + dy * dy);

    // Preset curves            

    resetCurve(channel = null) {            if (distance <= threshold) {

        const targetChannel = channel || this.activeChannel;                return i;

        this.curves[targetChannel] = [[0, 0], [1, 1]];            }

        this.selectedPoint = -1;        }

        this.updateNodeWidget();        

    }        return -1;

        }

    applySCurve(channel = null) {    

        const targetChannel = channel || this.activeChannel;    resetChannel(channel = null) {

        this.curves[targetChannel] = [        const targetChannel = channel || this.activeChannel;

            [0, 0],        this.curves[targetChannel] = [[0, 0], [1, 1]];

            [0.25, 0.15],        this.updateNodeWidget();

            [0.75, 0.85],        this.selectedPoint = -1;

            // Apex RGB Curve - Core Interface Controller
            // Professional Photoshop-style RGB curve editor with separate channel controls

            export class ApexRGBCurveInterface {
                constructor(canvas, widget) {
                    this.canvas = canvas;
                    this.widget = widget;
                    this.gridOpacity = 0.3;
                    this.curves = {
                        master: [[0, 0], [1, 1]],
                        red: [[0, 0], [1, 1]],
                        green: [[0, 0], [1, 1]],
                        blue: [[0, 0], [1, 1]],
                        rgb: [[0, 0], [1, 1]] // Master RGB curve
                    };
                    this.isDragging = false;
                    this.gridSize = 20;
                    this.pointRadius = 5;
                    this.lineWidth = 2;
                    this.channelColors = {
                        master: '#ffffff',
                        red: '#ff4444',
                        green: '#44ff44',
                        blue: '#4488ff',
                        rgb: '#ffffff',
                        point: '#ffffff',
                        text: '#cccccc'
                    };
                    this.activeChannel = 'rgb';
                    this.setupCanvas();
                    this.bindEvents();
                }

                setupCanvas() {
                    // Canvas setup logic here
                }

                bindEvents() {
                    // Event binding logic here
                }

                parseCurveData(data) {
                    try {
                        const parsed = JSON.parse(data);
                        // Validate and assign curve data
                        this.curves = parsed;
                    } catch (error) {
                        console.warn('Failed to parse RGB curve data:', error);
                    }
                }

                setActiveChannel(channel) {
                    this.activeChannel = channel;
                    this.updateChannelVisibility();
                }

                updateChannelVisibility() {
                    // Update channel visibility logic here
                }

                updateNodeWidget() {
                    // Update node widget logic here
                }
            }

            this.curves[targetChannel] = [        ];

                [0, 0.1],        this.updateNodeWidget();

                [0.25, 0.35],        this.selectedPoint = -1;

                [0.5, 0.5],    }

                [0.75, 0.65],    

                [1, 0.9]    redraw() {

            ];        if (this.visualization) {

        }            this.visualization.draw();

                }

        this.selectedPoint = -1;    }

        this.updateNodeWidget();}
    }
    
    // Widget communication
    updateNodeWidget() {
        if (this.widget && this.widget.callback) {
            const curvesData = JSON.stringify(this.curves);
            this.widget.value = curvesData;
            this.widget.callback(curvesData);
        }
    }
    
    // Redraw trigger
    redraw() {
        if (this.visualization) {
            this.visualization.draw();
        }
    }
}