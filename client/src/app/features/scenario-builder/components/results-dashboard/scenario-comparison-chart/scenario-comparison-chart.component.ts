import { Component, Input, ViewChild, ElementRef, AfterViewInit, OnChanges } from '@angular/core';
import { Chart, registerables } from 'chart.js';
import { ScenarioSummary } from '../../../../../core/models/event.models';
import { DESIGN_TOKENS } from '../../../../../shared/theme/design-tokens';

Chart.register(...registerables);

@Component({
  selector: 'app-scenario-comparison-chart',
  template: `<div class="chart-container"><canvas #chartCanvas></canvas></div>`,
  styles: [`.chart-container { height: 350px; position: relative; margin: 16px 0; }`],
})
export class ScenarioComparisonChartComponent implements AfterViewInit, OnChanges {
  @Input() summaries: ScenarioSummary[] = [];
  @ViewChild('chartCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  private chart?: Chart;

  ngAfterViewInit(): void {
    this.renderChart();
  }

  ngOnChanges(): void {
    if (this.canvasRef) {
      this.renderChart();
    }
  }

  private renderChart(): void {
    if (this.chart) this.chart.destroy();

    const labels = this.summaries.map(s => s.scenario);
    const data = this.summaries.map(s => s.gross_loss_m);
    const colors = this.summaries.map(s => DESIGN_TOKENS.scenarioColors[s.scenario] ?? DESIGN_TOKENS.everestBlue);

    this.chart = new Chart(this.canvasRef.nativeElement, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const s = this.summaries[ctx.dataIndex];
                return [
                  `Gross Loss: $${s.gross_loss_m.toFixed(1)}M`,
                  `Contracts: ${s.contracts}`,
                  `Market Share: ${s.market_share_pct.toFixed(2)}%`,
                ];
              },
            },
          },
        },
        scales: {
          y: {
            title: { display: true, text: 'Gross Loss ($M)', color: '#061C49' },
            grid: { color: '#E2E8F0' },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });
  }
}
