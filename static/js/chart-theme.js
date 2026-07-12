/**
 * WeatherLink Dashboard - Chart.js Premium Styling System (chart-theme.js)
 * Configure defaults and helpers for highly polished visual representation.
 */

// Configure Chart.js global defaults if Chart is loaded
if (typeof Chart !== 'undefined') {
    // Fonts and global colors
    Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#94a3b8'; // Tick colors, etc.
    
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
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(9, 13, 22, 0.9)';
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
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.08)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 12;
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.usePointStyle = true;
    Chart.defaults.plugins.tooltip.boxWidth = 6;
    Chart.defaults.plugins.tooltip.boxHeight = 6;
    Chart.defaults.plugins.tooltip.boxPadding = 6;
    Chart.defaults.plugins.tooltip.mode = 'index';
    Chart.defaults.plugins.tooltip.intersect = false;
}

const ChartTheme = {
    // Generate linear gradient fading to transparent for line charts fill
    getGradient(ctx, colorHex, height = 300) {
        // Handle if ctx is Canvas element or CanvasRenderingContext2D
        const drawingContext = ctx.getContext ? ctx.getContext('2d') : ctx;
        const gradient = drawingContext.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, colorHex + '35'); // 20% opacity at top
        gradient.addColorStop(0.5, colorHex + '0e'); // 5% opacity in middle
        gradient.addColorStop(1, colorHex + '00');  // 0% opacity at bottom
        return gradient;
    },

    // Standard Grid and Tick configuration for axes
    getAxisConfig(titleText, beginAtZero = false) {
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
    }
};
