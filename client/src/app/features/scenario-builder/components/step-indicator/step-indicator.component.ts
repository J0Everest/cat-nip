import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-step-indicator',
  template: `
    <div class="step-bar">
      @for (step of steps; track step; let i = $index) {
        <div class="step-item" [class.active]="i === currentIndex" [class.done]="i < currentIndex">
          {{ step }}
        </div>
      }
    </div>
  `,
  styles: [`
    .step-bar { display: flex; gap: 0; margin-bottom: 20px; }
    .step-item {
      flex: 1; text-align: center; padding: 10px 8px;
      font-size: 0.78rem; font-weight: 600;
      border-bottom: 3px solid #E2E8F0; color: #A4ABC8;
      transition: all 0.2s;
    }
    .step-item.active { border-bottom-color: #235CF4; color: #235CF4; }
    .step-item.done { border-bottom-color: #198038; color: #198038; }
  `],
})
export class StepIndicatorComponent {
  @Input() steps: string[] = [];
  @Input() currentIndex = 0;
}
