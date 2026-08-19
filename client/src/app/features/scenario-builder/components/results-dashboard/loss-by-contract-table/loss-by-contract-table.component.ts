import { Component, Input } from '@angular/core';
import { DecimalPipe, PercentPipe } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { ContractLoss } from '../../../../../core/models/event.models';
import { CopyButtonComponent } from '../../../../../shared/components/copy-button/copy-button.component';

@Component({
  selector: 'app-loss-by-contract-table',
  imports: [DecimalPipe, PercentPipe, MatTableModule, MatSortModule, CopyButtonComponent],
  template: `
    <app-copy-button label="Copy Loss by Contract" [data]="tsvData" downloadFilename="loss-by-contract.csv" />

    <table mat-table [dataSource]="contracts" matSort class="contract-table">
      <ng-container matColumnDef="layerkey">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Layerkey</th>
        <td mat-cell *matCellDef="let c">{{ c.layerkey }}</td>
      </ng-container>
      <ng-container matColumnDef="department">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Department</th>
        <td mat-cell *matCellDef="let c">{{ c.department }}</td>
      </ng-container>
      <ng-container matColumnDef="company">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Company</th>
        <td mat-cell *matCellDef="let c">{{ c.company }}</td>
      </ng-container>
      <ng-container matColumnDef="subtype">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Subtype</th>
        <td mat-cell *matCellDef="let c">{{ c.subtype }}</td>
      </ng-container>
      <ng-container matColumnDef="contract">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Contract</th>
        <td mat-cell *matCellDef="let c">{{ c.contract }}</td>
      </ng-container>
      <ng-container matColumnDef="terms">
        <th mat-header-cell *matHeaderCellDef>Terms</th>
        <td mat-cell *matCellDef="let c">{{ c.terms }}</td>
      </ng-container>
      <ng-container matColumnDef="everest_limit">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Everest Limit</th>
        <td mat-cell *matCellDef="let c">{{ c.everest_limit | number:'1.0-0' }}</td>
      </ng-container>
      <ng-container matColumnDef="rol">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>ROL</th>
        <td mat-cell *matCellDef="let c">{{ c.rol | number:'1.2-2' }}</td>
      </ng-container>
      <ng-container matColumnDef="share">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Share</th>
        <td mat-cell *matCellDef="let c">{{ c.share | percent:'1.1-1' }}</td>
      </ng-container>
      <ng-container matColumnDef="low_gross_m">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Low $M</th>
        <td mat-cell *matCellDef="let c">{{ c.low_gross_m | number:'1.4-4' }}</td>
      </ng-container>
      <ng-container matColumnDef="med_gross_m">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Med $M</th>
        <td mat-cell *matCellDef="let c">{{ c.med_gross_m | number:'1.4-4' }}</td>
      </ng-container>
      <ng-container matColumnDef="high_gross_m">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>High $M</th>
        <td mat-cell *matCellDef="let c">{{ c.high_gross_m | number:'1.4-4' }}</td>
      </ng-container>

      <tr mat-header-row *matHeaderRowDef="columns"></tr>
      <tr mat-row *matRowDef="let row; columns: columns;"></tr>
    </table>
  `,
  styles: [`
    .contract-table { width: 100%; margin-bottom: 16px; }
  `],
})
export class LossByContractTableComponent {
  @Input() contracts: ContractLoss[] = [];

  readonly columns = [
    'layerkey', 'department', 'company', 'subtype', 'contract', 'terms',
    'everest_limit', 'rol', 'share', 'low_gross_m', 'med_gross_m', 'high_gross_m',
  ];

  get tsvData(): string {
    const header = this.columns.join('\t');
    const rows = this.contracts.map(c =>
      this.columns.map(col => (c as unknown as Record<string, unknown>)[col] ?? '').join('\t')
    );
    return [header, ...rows].join('\n');
  }
}
