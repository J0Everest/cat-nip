import { Component, Input, Output, EventEmitter, OnChanges, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatRadioModule } from '@angular/material/radio';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { DatabaseConfigService } from '../../../../core/services/database-config.service';
import { ParsedScenario, AirTableProfile } from '../../../../core/models/scenario.models';

@Component({
  selector: 'app-refine-filters',
  imports: [
    DecimalPipe, FormsModule, MatExpansionModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatSliderModule, MatCheckboxModule, MatRadioModule,
    MatButtonModule, MatProgressSpinnerModule,
  ],
  template: `
    <mat-expansion-panel [expanded]="false" class="refine-panel">
      <mat-expansion-panel-header>
        <mat-panel-title>Refine Filters</mat-panel-title>
      </mat-expansion-panel-header>

      <div class="filter-row">
        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Peril</mat-label>
          <mat-select [(ngModel)]="peril" (ngModelChange)="emitChange()">
            @for (opt of dbConfig.perilOptions(); track opt) {
              <mat-option [value]="opt">{{ opt }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Zone (partial match)</mat-label>
          <input matInput [(ngModel)]="zone" (ngModelChange)="emitChange()" placeholder="e.g. FL, Zone 03, Caribbean">
        </mat-form-field>

        <div class="slider-group filter-field">
          <label class="slider-label">Industry Loss ($B): {{ lossLo | number:'1.1-1' }} &ndash; {{ lossHi | number:'1.1-1' }}</label>
          <mat-slider min="0" max="300" step="0.5" [discrete]="true">
            <input matSliderStartThumb [(ngModel)]="lossLo" (ngModelChange)="emitChange()">
            <input matSliderEndThumb [(ngModel)]="lossHi" (ngModelChange)="emitChange()">
          </mat-slider>
        </div>
      </div>

      <mat-radio-group [(ngModel)]="filterMode" (ngModelChange)="emitChange()" class="filter-mode-group">
        <mat-radio-button value="Industry Loss">Industry Loss</mat-radio-button>
        <mat-radio-button value="Event Characteristics">Event Characteristics</mat-radio-button>
        <mat-radio-button value="Both">Both</mat-radio-button>
      </mat-radio-group>

      @if (filterMode !== 'Industry Loss') {
        <div class="char-row">
          <mat-form-field appearance="outline" class="filter-field">
            <mat-label>Event description keyword</mat-label>
            <input matInput [(ngModel)]="eventKeyword" (ngModelChange)="emitChange()">
          </mat-form-field>

          <div class="slider-group filter-field">
            <label class="slider-label">Magnitude: {{ magLo | number:'1.1-1' }} &ndash; {{ magHi | number:'1.1-1' }}</label>
            <mat-slider min="0" max="12" step="0.1" [discrete]="true">
              <input matSliderStartThumb [(ngModel)]="magLo" (ngModelChange)="emitChange()">
              <input matSliderEndThumb [(ngModel)]="magHi" (ngModelChange)="emitChange()">
            </mat-slider>
          </div>
        </div>

        <mat-checkbox [(ngModel)]="useAir" (ngModelChange)="emitChange()">
          Enrich from {{ dbConfig.airEventsDb() || 'AIREvents' }}
        </mat-checkbox>

        @if (useAir && airTables.length > 0) {
          <mat-form-field appearance="outline" class="air-table-field">
            <mat-label>AIR Events Table</mat-label>
            <mat-select [(ngModel)]="selectedAirTable" (ngModelChange)="onAirTableChange()">
              @for (t of airTables; track t.label) {
                <mat-option [value]="t.label">
                  {{ t.label }}
                  @if (t.label === recommendedTable) { (recommended) }
                </mat-option>
              }
            </mat-select>
          </mat-form-field>

          @if (airDescriptions.length > 0) {
            <mat-form-field appearance="outline" class="air-table-field">
              <mat-label>Event description</mat-label>
              <mat-select [(ngModel)]="selectedDescription" (ngModelChange)="onDescriptionChange()">
                <mat-option value="">(any)</mat-option>
                @for (d of airDescriptions; track d) {
                  <mat-option [value]="d">{{ d }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
          }
        }
      }
    </mat-expansion-panel>

    <button mat-flat-button color="primary" class="search-btn" (click)="searchEvents.emit()">
      Find Matching Events
    </button>
  `,
  styles: [`
    .refine-panel { margin-bottom: 16px; }
    .filter-row, .char-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
    .filter-field { flex: 1; min-width: 200px; }
    .slider-group { display: flex; flex-direction: column; }
    .slider-label { font-size: 0.78rem; color: #666; margin-bottom: 4px; }
    .filter-mode-group { display: flex; gap: 16px; margin: 12px 0; }
    .air-table-field { width: 100%; margin-top: 8px; }
    .search-btn { width: 100%; margin: 16px 0; height: 48px; font-size: 1rem; }
  `],
})
export class RefineFiltersComponent implements OnChanges {
  readonly dbConfig = inject(DatabaseConfigService);

  @Input() parsed!: ParsedScenario;
  @Input() airTables: AirTableProfile[] = [];
  @Input() airDescriptions: string[] = [];
  @Input() recommendedTable: string | null = null;

  @Output() filtersChanged = new EventEmitter<{
    peril: string; zone: string; lossLo: number; lossHi: number;
    filterMode: string; eventKeyword: string; useAir: boolean;
    airTableSchema: string; airTableName: string; magLo: number; magHi: number;
  }>();
  @Output() searchEvents = new EventEmitter<void>();

  peril = 'All';
  zone = '';
  lossLo = 0;
  lossHi = 300;
  filterMode = 'Industry Loss';
  eventKeyword = '';
  useAir = true;
  selectedAirTable = '';
  selectedDescription = '';
  magLo = 0;
  magHi = 12;

  ngOnChanges(): void {
    if (this.parsed) {
      if (this.parsed.peril) this.peril = this.parsed.peril;
      if (this.parsed.zone) this.zone = this.parsed.zone;
      if (this.parsed.loss_lo !== null) this.lossLo = this.parsed.loss_lo;
      if (this.parsed.loss_hi !== null) this.lossHi = this.parsed.loss_hi;
      if (this.parsed.event_keyword) this.eventKeyword = this.parsed.event_keyword;
      if (this.parsed.mag_lo !== null) this.magLo = this.parsed.mag_lo;
      if (this.parsed.mag_hi !== null) this.magHi = this.parsed.mag_hi;
    }
    if (this.recommendedTable && !this.selectedAirTable) {
      this.selectedAirTable = this.recommendedTable;
    }
  }

  onAirTableChange(): void {
    this.emitChange();
  }

  onDescriptionChange(): void {
    if (this.selectedDescription) {
      this.eventKeyword = this.selectedDescription;
    }
    this.emitChange();
  }

  emitChange(): void {
    const table = this.airTables.find(t => t.label === this.selectedAirTable);
    this.filtersChanged.emit({
      peril: this.peril,
      zone: this.zone,
      lossLo: this.lossLo,
      lossHi: this.lossHi,
      filterMode: this.filterMode,
      eventKeyword: this.eventKeyword,
      useAir: this.useAir,
      airTableSchema: table?.schema ?? '',
      airTableName: table?.table ?? '',
      magLo: this.magLo,
      magHi: this.magHi,
    });
  }
}
