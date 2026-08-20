import { Component, Input, Output, EventEmitter } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSortModule, Sort } from '@angular/material/sort';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { CandidateEvent } from '../../../../core/models/event.models';

@Component({
  selector: 'app-candidate-events-table',
  imports: [DecimalPipe, FormsModule, MatTableModule, MatCheckboxModule, MatSortModule, MatPaginatorModule],
  template: `
    <div class="section-title">Candidate Events</div>
    <p class="event-count">{{ events.length }} candidate event{{ events.length !== 1 ? 's' : '' }} found</p>

    <table mat-table [dataSource]="pagedEvents" matSort (matSortChange)="onSort($event)" class="events-table">
      <ng-container matColumnDef="select">
        <th mat-header-cell *matHeaderCellDef>
          <mat-checkbox (change)="toggleAll($event.checked)" [checked]="allSelected" [indeterminate]="someSelected" />
        </th>
        <td mat-cell *matCellDef="let event">
          <mat-checkbox [checked]="event.selected" (change)="toggleEvent(event, $event.checked)" />
        </td>
      </ng-container>

      <ng-container matColumnDef="event_id">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Event ID</th>
        <td mat-cell *matCellDef="let event">{{ event.event_id }}</td>
      </ng-container>

      <ng-container matColumnDef="description">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Description</th>
        <td mat-cell *matCellDef="let event">{{ event.description }}</td>
      </ng-container>

      <ng-container matColumnDef="peril">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Peril</th>
        <td mat-cell *matCellDef="let event">{{ event.peril }}</td>
      </ng-container>

      <ng-container matColumnDef="industry_loss_b">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>Industry Loss ($B)</th>
        <td mat-cell *matCellDef="let event">{{ event.industry_loss_b | number:'1.2-2' }}</td>
      </ng-container>

      <ng-container matColumnDef="air_description">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>AIR Description</th>
        <td mat-cell *matCellDef="let event">{{ event.air_description ?? '' }}</td>
      </ng-container>

      <ng-container matColumnDef="air_magnitude">
        <th mat-header-cell *matHeaderCellDef mat-sort-header>AIR Magnitude</th>
        <td mat-cell *matCellDef="let event">{{ event.air_magnitude != null ? (event.air_magnitude | number:'1.1-1') : '' }}</td>
      </ng-container>

      <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
      <tr mat-row *matRowDef="let row; columns: displayedColumns;" [class.selected-row]="row.selected"></tr>
    </table>

    <mat-paginator
      [length]="sortedEvents.length"
      [pageSize]="pageSize"
      [pageSizeOptions]="[25, 50, 100]"
      (page)="onPage($event)"
      showFirstLastButtons />
  `,
  styles: [`
    .section-title {
      font-size: 1.05rem; font-weight: 700; color: #061C49;
      border-bottom: 2px solid #235CF4; padding-bottom: 6px; margin: 24px 0 12px;
    }
    .event-count { font-size: 0.82rem; color: #A4ABC8; margin-bottom: 8px; }
    .events-table { width: 100%; border-radius: 8px; overflow: hidden; }
    .selected-row { background: #EBF0FE !important; }
    tr.mat-mdc-row:nth-child(even) { background: rgba(0,0,0,0.02); }
    tr.mat-mdc-row:hover { background: rgba(35,92,244,0.06); }
    tr.mat-mdc-row.selected-row:hover { background: #DDE5FD !important; }
    mat-paginator { margin-top: 8px; }
  `],
})
export class CandidateEventsTableComponent {
  @Input() events: CandidateEvent[] = [];
  @Input() loading = false;
  @Output() eventsSelected = new EventEmitter<CandidateEvent[]>();

  sortedEvents: CandidateEvent[] = [];
  pagedEvents: CandidateEvent[] = [];
  pageSize = 25;
  pageIndex = 0;

  get displayedColumns(): string[] {
    const cols = ['select', 'event_id', 'description', 'peril', 'industry_loss_b'];
    if (this.events.some(e => e.air_description != null)) cols.push('air_description');
    if (this.events.some(e => e.air_magnitude != null)) cols.push('air_magnitude');
    return cols;
  }

  get allSelected(): boolean {
    return this.events.length > 0 && this.events.every(e => e.selected);
  }

  get someSelected(): boolean {
    return this.events.some(e => e.selected) && !this.allSelected;
  }

  ngOnChanges(): void {
    this.sortedEvents = [...this.events];
    this.updatePage();
  }

  onSort(sort: Sort): void {
    if (!sort.active || sort.direction === '') {
      this.sortedEvents = [...this.events];
    } else {
      this.sortedEvents = [...this.events].sort((a, b) => {
        const aVal = (a as unknown as Record<string, unknown>)[sort.active];
        const bVal = (b as unknown as Record<string, unknown>)[sort.active];
        const cmp = (aVal ?? 0) < (bVal ?? 0) ? -1 : (aVal ?? 0) > (bVal ?? 0) ? 1 : 0;
        return sort.direction === 'asc' ? cmp : -cmp;
      });
    }
    this.pageIndex = 0;
    this.updatePage();
  }

  onPage(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.updatePage();
  }

  toggleEvent(event: CandidateEvent, checked: boolean): void {
    event.selected = checked;
    this.emitSelected();
  }

  toggleAll(checked: boolean): void {
    this.events.forEach(e => e.selected = checked);
    this.emitSelected();
  }

  private emitSelected(): void {
    this.eventsSelected.emit(this.events.filter(e => e.selected));
  }

  private updatePage(): void {
    const start = this.pageIndex * this.pageSize;
    this.pagedEvents = this.sortedEvents.slice(start, start + this.pageSize);
  }
}
