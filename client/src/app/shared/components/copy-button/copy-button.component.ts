import { Component, Input } from '@angular/core';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-copy-button',
  imports: [MatButtonModule, MatIconModule],
  template: `
    <button mat-stroked-button class="copy-btn" (click)="copy()">
      <mat-icon>content_copy</mat-icon> {{ label }}
    </button>
    @if (copied) {
      <span class="copied-msg">Copied!</span>
    }
  `,
  styles: [`
    :host { display: inline-flex; align-items: center; gap: 8px; margin: 4px 0 8px; }
    .copy-btn { font-size: 0.78rem; }
    .copied-msg { font-size: 0.78rem; color: #198038; }
  `],
})
export class CopyButtonComponent {
  @Input() label = 'Copy';
  @Input() data = '';
  copied = false;

  constructor(private clipboard: Clipboard) {}

  copy(): void {
    this.clipboard.copy(this.data);
    this.copied = true;
    setTimeout(() => this.copied = false, 1500);
  }
}
