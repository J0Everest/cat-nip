import { Component, Input } from '@angular/core';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-copy-button',
  imports: [MatButtonModule, MatIconModule],
  template: `
    <button mat-stroked-button class="action-btn" (click)="copy()">
      <mat-icon>content_copy</mat-icon> {{ label }}
    </button>
    @if (showDownload) {
      <button mat-stroked-button class="action-btn" (click)="downloadCsv()">
        <mat-icon>download</mat-icon> Download CSV
      </button>
    }
    @if (feedback) {
      <span class="feedback-msg">{{ feedback }}</span>
    }
  `,
  styles: [`
    :host { display: inline-flex; align-items: center; gap: 8px; margin: 4px 0 8px; }
    .action-btn { font-size: 0.78rem; }
    .feedback-msg { font-size: 0.78rem; color: #198038; }
  `],
})
export class CopyButtonComponent {
  @Input() label = 'Copy';
  @Input() data = '';
  @Input() showDownload = true;
  @Input() downloadFilename = 'export.csv';
  feedback = '';

  constructor(private clipboard: Clipboard) {}

  copy(): void {
    this.clipboard.copy(this.data);
    this.showFeedback('Copied!');
  }

  downloadCsv(): void {
    const csv = this.tsvToCsv(this.data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = this.downloadFilename;
    a.click();
    URL.revokeObjectURL(url);
    this.showFeedback('Downloaded!');
  }

  private tsvToCsv(tsv: string): string {
    return tsv.split('\n').map(line =>
      line.split('\t').map(cell => {
        if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
          return '"' + cell.replace(/"/g, '""') + '"';
        }
        return cell;
      }).join(',')
    ).join('\n');
  }

  private showFeedback(msg: string): void {
    this.feedback = msg;
    setTimeout(() => this.feedback = '', 1500);
  }
}
