import { Component, Input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { DetailRow } from '../../../../../core/models/event.models';
import { CopyButtonComponent } from '../../../../../shared/components/copy-button/copy-button.component';

@Component({
  selector: 'app-full-output-detail',
  imports: [DecimalPipe, MatTableModule, MatSortModule, CopyButtonComponent],
  template: `
    <app-copy-button label="Copy Full Output" [data]="tsvData" downloadFilename="full-output-detail.csv" />

    <table mat-table [dataSource]="detail" matSort class="detail-table">
      <ng-container matColumnDef="layerkey">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Layerkey</th>
        <td mat-cell *matCellDef="let d">{{ d.layerkey }}</td>
      </ng-container>
      <ng-container matColumnDef="scenario">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Scenario</th>
        <td mat-cell *matCellDef="let d">{{ d.scenario }}</td>
      </ng-container>
      <ng-container matColumnDef="department">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Department</th>
        <td mat-cell *matCellDef="let d">{{ d.department }}</td>
      </ng-container>
      <ng-container matColumnDef="company">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Company</th>
        <td mat-cell *matCellDef="let d">{{ d.company }}</td>
      </ng-container>
      <ng-container matColumnDef="contract">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Contract</th>
        <td mat-cell *matCellDef="let d">{{ d.contract }}</td>
      </ng-container>
      <ng-container matColumnDef="industry_loss_b">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Industry ($B)</th>
        <td mat-cell *matCellDef="let d">{{ d.industry_loss_b | number:'1.2-2' }}</td>
      </ng-container>
      <ng-container matColumnDef="gross_loss_m">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Gross $M</th>
        <td mat-cell *matCellDef="let d">{{ d.gross_loss_m | number:'1.4-4' }}</td>
      </ng-container>
      <ng-container matColumnDef="reins_recovery_m">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Reins Recovery $M</th>
        <td mat-cell *matCellDef="let d">{{ d.reins_recovery_m | number:'1.4-4' }}</td>
      </ng-container>
      <ng-container matColumnDef="net_loss_m">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Net $M</th>
        <td mat-cell *matCellDef="let d">{{ d.net_loss_m | number:'1.4-4' }}</td>
      </ng-container>

      <tr mat-header-row *matHeaderRowDef="columns"></tr>
      <tr mat-row *matRowDef="let row; columns: columns;"></tr>
    </table>
  `,
  styles: [`.detail-table { width: 100%; }`],
})
export class FullOutputDetailComponent {
  @Input() detail: DetailRow[] = [];

  readonly columns = [
    'layerkey', 'scenario', 'department', 'company', 'contract',
    'industry_loss_b', 'gross_loss_m', 'reins_recovery_m', 'net_loss_m',
  ];

  get tsvData(): string {
    const header = this.columns.join('\t');
    const rows = this.detail.map(d =>
      this.columns.map(col => (d as unknown as Record<string, unknown>)[col] ?? '').join('\t')
    );
    return [header, ...rows].join('\n');
  }
}
