/**
 * WeatherLink Dashboard - Chart.js Premium Styling System (chart-theme.js)
 * Configure defaults and helpers for highly polished visual representation.
 * Includes Excel-style 2-level Hierarchical Categorical Axis for ISO Weeks.
 */

// ==============================================================================
// FUNCIONES GLOBALES DE SEMANA ISO Y ETIQUETAS DE EJES (NIVEL GLOBAL / WINDOW)
// ==============================================================================

function getWeekCode(dateInput) {
    if (!dateInput && dateInput !== 0) return '';
    const d = new Date(typeof dateInput === 'number' ? (dateInput < 1e11 ? dateInput * 1000 : dateInput) : dateInput);
    if (isNaN(d.getTime())) return '';
    const target = new Date(d.valueOf());
    const dayNr = (d.getDay() + 6) % 7;
    target.setDate(target.getDate() - dayNr + 3);
    const firstThursday = target.valueOf();
    target.setMonth(0, 1);
    if (target.getDay() !== 4) {
        target.setMonth(0, 1 + ((4 - target.getDay()) + 7) % 7);
    }
    const weekDiff = 1 + Math.round((firstThursday - target) / (7 * 24 * 3600 * 1000));
    const year = new Date(firstThursday).getFullYear();
    const yy = String(year).slice(-2);
    const ww = String(weekDiff).padStart(2, '0');
    return `${yy}${ww}`;
}

function formatLevel1Label(dateInput, isDaily = false) {
    const d = new Date(typeof dateInput === 'number' ? (dateInput < 1e11 ? dateInput * 1000 : dateInput) : dateInput);
    if (isNaN(d.getTime())) return String(dateInput);
    if (isDaily) {
        return d.toLocaleDateString('es-ES', { weekday: 'short', day: '2-digit', month: 'short' });
    }
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' }) + ' ' +
           d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

function formatLabelSeries(datesArray, isDaily = false) {
    if (!Array.isArray(datesArray)) return [];
    return datesArray.map(d => formatLevel1Label(d, isDaily));
}

function formatLabelWithWeek(dateInput, isDaily = false) {
    return formatLevel1Label(dateInput, isDaily);
}

function resetChartZoom(chart) {
    if (chart && typeof chart.resetZoom === 'function') {
        chart.resetZoom();
    }
}

// Bind explicitly to window
if (typeof window !== 'undefined') {
    window.getWeekCode = getWeekCode;
    window.formatLevel1Label = formatLevel1Label;
    window.formatLabelSeries = formatLabelSeries;
    window.formatLabelWithWeek = formatLabelWithWeek;
    window.resetChartZoom = resetChartZoom;
}

// Configure Chart.js global defaults if Chart is loaded
if (typeof Chart !== 'undefined') {
    // Fonts and global colors
    Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#94a3b8'; // Tick colors, etc.
    
    // Layout bottom padding to reserve room for Level 2 Excel week bracket
    Chart.defaults.layout = Chart.defaults.layout || {};
    Chart.defaults.layout.padding = Chart.defaults.layout.padding || {};
    Chart.defaults.layout.padding.bottom = 34;

    // Legends
    Chart.defaults.plugins.legend.labels.color = '#cbd5e1';
    Chart.defaults.plugins.legend.labels.font = {
        family: "'Outfit', sans-serif",
        size: 13,
        weight: '600'
    };
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.legend.labels.boxHeight = 8;
    Chart.defaults.plugins.legend.labels.padding = 15;

    // Tooltips (Glassmorphism look)
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(9, 13, 22, 0.92)';
    Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
    Chart.defaults.plugins.tooltip.titleFont = {
        family: "'Outfit', sans-serif",
        size: 13,
        weight: '700'
    };
    Chart.defaults.plugins.tooltip.bodyColor = '#e2e8f0';
    Chart.defaults.plugins.tooltip.bodyFont = {
        family: "'Inter', sans-serif",
        size: 12
    };
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.12)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.usePointStyle = true;
    Chart.defaults.plugins.tooltip.boxWidth = 6;
    Chart.defaults.plugins.tooltip.boxHeight = 6;
    Chart.defaults.plugins.tooltip.boxPadding = 6;
    Chart.defaults.plugins.tooltip.mode = 'index';
    Chart.defaults.plugins.tooltip.intersect = false;
    Chart.defaults.plugins.tooltip.callbacks = Chart.defaults.plugins.tooltip.callbacks || {};
    Chart.defaults.plugins.tooltip.callbacks.title = function(context) {
        if (!context || !context.length) return '';
        const item = context[0];
        const chart = item.chart;
        const idx = item.dataIndex;
        const rawLabel = item.label;
        const dates = chart?.data?._dates;
        const ts = (dates && dates[idx] !== undefined) ? dates[idx] : null;

        if (ts) {
            const d = new Date(typeof ts === 'number' ? (ts < 1e11 ? ts * 1000 : ts) : ts);
            if (!isNaN(d.getTime())) {
                const fullDate = d.toLocaleString('es-ES', {
                    weekday: 'short',
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                const week = getWeekCode(d);
                return `${fullDate} • Sem ${week}`;
            }
        }
        return Array.isArray(rawLabel) ? rawLabel.join(' • ') : String(rawLabel);
    };
}

// ==============================================================================
// PLUGIN: EXCEL MULTI-LEVEL CATEGORICAL AXIS (Gráfico Dinámico de Excel)
// ==============================================================================
const excelMultiLevelAxisPlugin = {
    id: 'excelMultiLevelAxis',
    afterDraw(chart) {
        const dates = chart?.data?._dates;
        if (!dates || !dates.length) return;

        const xScale = chart.scales.x;
        const chartArea = chart.chartArea;
        const ctx = chart.ctx;
        if (!xScale || !chartArea) return;

        // 1. Agrupar índices continuos por semana ISO
        const groups = [];
        let currentGroup = null;

        dates.forEach((ts, idx) => {
            const d = new Date(typeof ts === 'number' ? (ts < 1e11 ? ts * 1000 : ts) : ts);
            const week = getWeekCode(d);
            if (!currentGroup || currentGroup.week !== week) {
                if (currentGroup) currentGroup.endIndex = idx - 1;
                currentGroup = { week: week, startIndex: idx, endIndex: idx };
                groups.push(currentGroup);
            } else {
                currentGroup.endIndex = idx;
            }
        });

        // Coordenadas verticales de los niveles
        const yTop = chartArea.top;
        const yChartBottom = chartArea.bottom;
        const yLevel1Bottom = xScale.bottom;
        const yLevel2Top = yLevel1Bottom + 2;
        const yLevel2Bottom = yLevel2Top + 24;

        const minVal = xScale.min !== undefined ? xScale.min : 0;
        const maxVal = xScale.max !== undefined ? xScale.max : dates.length - 1;

        ctx.save();

        groups.forEach((g) => {
            // Descartar si el grupo está completamente fuera de la vista de zoom
            if (g.endIndex < minVal || g.startIndex > maxVal) return;

            // Calcular coordenadas horizontales del grupo
            let xStart;
            if (g.startIndex <= minVal) {
                xStart = xScale.left;
            } else {
                const prevPixel = xScale.getPixelForValue(g.startIndex - 1);
                const curPixel = xScale.getPixelForValue(g.startIndex);
                xStart = (prevPixel + curPixel) / 2;
            }

            let xEnd;
            if (g.endIndex >= maxVal) {
                xEnd = xScale.right;
            } else {
                const curPixel = xScale.getPixelForValue(g.endIndex);
                const nextPixel = xScale.getPixelForValue(g.endIndex + 1);
                xEnd = (curPixel + nextPixel) / 2;
            }

            // Acotar a los límites visibles del eje
            xStart = Math.max(xScale.left, Math.min(xScale.right, xStart));
            xEnd = Math.max(xScale.left, Math.min(xScale.right, xEnd));

            if (xStart >= xEnd) return;

            // 1. Línea divisoria vertical de transición entre semanas
            if (g.startIndex > minVal) {
                // Segmento superior dentro del gráfico (punteada sutil cian)
                ctx.beginPath();
                ctx.strokeStyle = 'rgba(56, 189, 248, 0.40)';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([4, 4]);
                ctx.moveTo(xStart, yTop);
                ctx.lineTo(xStart, yChartBottom);
                ctx.stroke();

                // Segmento inferior que atraviesa el eje y encierra la etiqueta padre
                ctx.beginPath();
                ctx.setLineDash([]);
                ctx.strokeStyle = 'rgba(56, 189, 248, 0.85)';
                ctx.lineWidth = 1.5;
                ctx.moveTo(xStart, yChartBottom);
                ctx.lineTo(xStart, yLevel2Bottom);
                ctx.stroke();
            }

            // Línea de cierre vertical en el extremo derecho final
            if (g.endIndex >= maxVal) {
                ctx.beginPath();
                ctx.setLineDash([]);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.20)';
                ctx.lineWidth = 1;
                ctx.moveTo(xEnd, yLevel2Top);
                ctx.lineTo(xEnd, yLevel2Bottom);
                ctx.stroke();
            }

            // Línea de cierre vertical en el extremo izquierdo inicial
            if (g.startIndex <= minVal) {
                ctx.beginPath();
                ctx.setLineDash([]);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.20)';
                ctx.lineWidth = 1;
                ctx.moveTo(xStart, yLevel2Top);
                ctx.lineTo(xStart, yLevel2Bottom);
                ctx.stroke();
            }

            // 2. Línea horizontal divisoria entre Nivel 1 (mediciones) y Nivel 2 (semanas)
            ctx.beginPath();
            ctx.setLineDash([]);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
            ctx.lineWidth = 1;
            ctx.moveTo(xStart, yLevel2Top);
            ctx.lineTo(xEnd, yLevel2Top);
            ctx.stroke();

            // 3. Línea horizontal de fondo (cierre de la caja jerárquica estilo Excel)
            ctx.beginPath();
            ctx.moveTo(xStart, yLevel2Bottom);
            ctx.lineTo(xEnd, yLevel2Bottom);
            ctx.stroke();

            // 4. Etiqueta centrada de la Semana Padre (Nivel Inferior)
            const cellWidth = xEnd - xStart;
            if (cellWidth >= 32) {
                const xCenter = (xStart + xEnd) / 2;
                const yCenter = (yLevel2Top + yLevel2Bottom) / 2;

                ctx.font = '600 11px Outfit, Inter, sans-serif';
                ctx.fillStyle = '#38bdf8'; // Cyan radiante estilo profesional
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('Sem ' + g.week, xCenter, yCenter);
            }
        });

        ctx.restore();
    }
};

if (typeof Chart !== 'undefined') {
    Chart.register(excelMultiLevelAxisPlugin);
}

const ChartTheme = {
    // Generate linear gradient fading to transparent for line charts fill
    getGradient(ctx, colorHex, height = 300) {
        const drawingContext = ctx.getContext ? ctx.getContext('2d') : ctx;
        const gradient = drawingContext.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, colorHex + '35'); // 20% opacity at top
        gradient.addColorStop(0.5, colorHex + '0e'); // 5% opacity in middle
        gradient.addColorStop(1, colorHex + '00');  // 0% opacity at bottom
        return gradient;
    },

    // Standard Grid and Tick configuration for axes
    getAxisConfig(titleText, beginAtZero = false) {
        const isXAxis = /fecha|hora|días|semana/i.test(titleText || '');

        if (isXAxis) {
            return {
                grid: {
                    color: 'rgba(255, 255, 255, 0.04)',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    drawBorder: true,
                    tickColor: 'rgba(255, 255, 255, 0.08)'
                },
                ticks: {
                    color: '#94a3b8',
                    font: {
                        family: "'Inter', sans-serif",
                        size: 10
                    },
                    minRotation: 90,
                    maxRotation: 90,
                    autoSkip: true,
                    autoSkipPadding: 8,
                    padding: 4
                },
                title: {
                    display: false // El Nivel 2 jerárquico ya contextualiza las semanas
                }
            };
        }

        return {
            grid: {
                color: 'rgba(255, 255, 255, 0.04)',
                borderColor: 'rgba(255, 255, 255, 0.08)',
                drawBorder: false,
                tickColor: 'rgba(255, 255, 255, 0.06)'
            },
            ticks: {
                color: '#94a3b8',
                font: {
                    family: "'Inter', sans-serif",
                    size: 11
                },
                padding: 8
            },
            title: {
                display: !!titleText,
                text: titleText || '',
                color: '#94a3b8',
                font: {
                    family: "'Outfit', sans-serif",
                    size: 12,
                    weight: '500'
                },
                padding: 10
            },
            beginAtZero: beginAtZero
        };
    },

    // Palette mapping for consistent metrics visualization
    getMetricStyle(metricType) {
        const styles = {
            temperature: { color: '#f97316', label: 'Temperatura (°C)' },
            humidity: { color: '#06b6d4', label: 'Humedad (%)' },
            wind_speed: { color: '#3b82f6', label: 'Velocidad (km/h)' },
            rain: { color: '#8b5cf6', label: 'Precipitación (mm)' },
            solar_radiation: { color: '#f59e0b', label: 'Radiación (W/m²)' },
            vpd: { color: '#10b981', label: 'DPV (kPa)' }
        };
        return styles[metricType] || { color: '#4facfe', label: '' };
    },

    // Configuración universal de Zoom tipo selección/arrastre
    getZoomConfig() {
        return {
            pan: {
                enabled: true,
                mode: 'x',
                modifierKey: 'ctrl'
            },
            zoom: {
                drag: {
                    enabled: true,
                    backgroundColor: 'rgba(79, 172, 254, 0.22)',
                    borderColor: 'rgba(79, 172, 254, 0.85)',
                    borderWidth: 1.5
                },
                mode: 'x'
            }
        };
    },

    // Habilita restablecer zoom con doble clic en el lienzo
    enableCanvasReset(canvas, chartGetter) {
        if (!canvas) return;
        canvas.title = 'Arrastra para hacer zoom • Doble clic para restablecer';
        canvas.addEventListener('dblclick', () => {
            const chart = typeof chartGetter === 'function' ? chartGetter() : chartGetter;
            if (chart && typeof chart.resetZoom === 'function') {
                chart.resetZoom();
            }
        });
    }
};

if (typeof window !== 'undefined') {
    window.ChartTheme = ChartTheme;
}
