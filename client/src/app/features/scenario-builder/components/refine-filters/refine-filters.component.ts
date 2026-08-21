import { Component, Input, Output, EventEmitter, OnChanges, OnInit, inject } from '@angular/core';
import { DecimalPipe, SlicePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { DatabaseConfigService } from '../../../../core/services/database-config.service';
import { ScenarioApiService } from '../../../../core/services/scenario-api.service';
import { ParsedScenario, AirTableProfile, ModelInfoResponse } from '../../../../core/models/scenario.models';

@Component({
  selector: 'app-refine-filters',
  imports: [
    DecimalPipe, SlicePipe, FormsModule, MatExpansionModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatSliderModule, MatButtonModule, MatIconModule,
    MatChipsModule, MatAutocompleteModule,
  ],
  template: `
    <mat-expansion-panel [expanded]="autoExpand" class="refine-panel">
      <mat-expansion-panel-header>
        <mat-panel-title>Refine Filters</mat-panel-title>
      </mat-expansion-panel-header>

      <!-- Row 1: Peril, Zone, Loss slider -->
      <div class="filter-row">
        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Peril</mat-label>
          <mat-select [(ngModel)]="peril" (ngModelChange)="onPerilChange()">
            @for (opt of dbConfig.perilOptions(); track opt) {
              <mat-option [value]="opt">{{ opt }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="filter-field">
          <mat-label>Zone</mat-label>
          <input matInput [(ngModel)]="zone" (ngModelChange)="onZoneInput()"
                 [matAutocomplete]="zoneAuto"
                 placeholder="Type to search zones...">
          <mat-autocomplete #zoneAuto (optionSelected)="zone = $event.option.value; emitChange()">
            @for (z of filteredZones; track z) {
              <mat-option [value]="z">{{ z }}</mat-option>
            }
          </mat-autocomplete>
        </mat-form-field>

        <div class="slider-group filter-field">
          <label class="slider-label">Industry Loss ($B): {{ formatLoss(lossLo) }} &ndash; {{ formatLoss(lossHi) }}</label>
          <mat-slider [min]="0" [max]="sliderMax" step="1" [discrete]="true" [displayWith]="displayLoss">
            <input matSliderStartThumb [(ngModel)]="lossLo" (ngModelChange)="onLossChange()">
            <input matSliderEndThumb [(ngModel)]="lossHi" (ngModelChange)="onLossChange()">
          </mat-slider>
        </div>
      </div>

      <!-- Row 2: Keyword search + optional magnitude slider -->
      <div class="char-row">
        <mat-form-field appearance="outline" class="filter-field keyword-field">
          <mat-label>Event description</mat-label>
          <mat-icon matPrefix class="search-icon">search</mat-icon>
          <input matInput [(ngModel)]="descSearch" placeholder="{{ airDescriptions.length > 0 ? 'Search ' + airDescriptions.length + ' descriptions...' : 'Search or type keyword...' }}">
          @if (descSearch) {
            <button matSuffix mat-icon-button (click)="descSearch = ''" aria-label="Clear search">
              <mat-icon>close</mat-icon>
            </button>
          }
        </mat-form-field>

        @if (selectedProfile?.mag_col) {
          <div class="slider-group filter-field">
            <label class="slider-label">{{ peril === 'EQ' ? 'Magnitude' : 'Intensity' }}: {{ magLo | number:'1.1-1' }} &ndash; {{ magHi | number:'1.1-1' }}</label>
            <mat-slider min="0" max="12" step="0.1" [discrete]="true" [displayWith]="displayMag">
              <input matSliderStartThumb [(ngModel)]="magLo" (ngModelChange)="emitChange()">
              <input matSliderEndThumb [(ngModel)]="magHi" (ngModelChange)="emitChange()">
            </mat-slider>
          </div>
        }
      </div>

      <!-- Selected keywords as removable chips -->
      @if (selectedKeywords.length > 0) {
        <div class="selected-keywords">
          @for (kw of selectedKeywords; track kw) {
            <span class="kw-chip" (click)="removeKeyword(kw)">
              {{ kw | slice:0:48 }}{{ kw.length > 48 ? '…' : '' }}
              <mat-icon class="kw-remove">close</mat-icon>
            </span>
          }
          @if (selectedKeywords.length > 1) {
            <button mat-button class="clear-all-btn" (click)="clearKeywords()">Clear all</button>
          }
        </div>
      }

      <!-- Description chips from AIR -->
      @if (airDescriptions.length > 0) {
        <div class="desc-chips">
          @for (d of filteredDescriptions; track d) {
            <span class="desc-chip" [class.active]="isSelected(d)" (click)="toggleKeyword(d)">{{ d }}</span>
          }
          @if (filteredDescriptions.length === 0 && descSearch) {
            <span class="no-match">No descriptions match "{{ descSearch }}"</span>
          }
        </div>
      }

      <!-- AIR table selector + subtle DB reference -->
      @if (airTables.length > 0) {
        <div class="air-row">
          <mat-form-field appearance="outline" class="air-table-field">
            <mat-label>AIR Table</mat-label>
            <mat-select [(ngModel)]="selectedAirTable" (ngModelChange)="onAirTableChange()">
              @for (t of airTables; track t.label) {
                <mat-option [value]="t.label">
                  {{ t.label }}
                  @if (t.label === recommendedTable) { <span class="rec-badge">recommended</span> }
                </mat-option>
              }
            </mat-select>
          </mat-form-field>
          <span class="air-ref">via {{ dbConfig.airEventsDb() || 'AIREvents' }}</span>
        </div>
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
    .keyword-field { flex: 2; }
    .slider-group { display: flex; flex-direction: column; }
    .slider-label { font-size: 0.78rem; color: #666; margin-bottom: 4px; }
    .search-icon { font-size: 18px; color: #A4ABC8; margin-right: 4px; }

    .selected-keywords {
      display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 4px 0 10px;
    }
    .kw-chip {
      display: inline-flex; align-items: center; gap: 4px;
      background: #235CF4; color: #fff;
      font-size: 0.72rem; border-radius: 12px;
      padding: 3px 8px 3px 12px; cursor: pointer;
      transition: background 0.15s;
    }
    .kw-chip:hover { background: #1a47c8; }
    .kw-remove { font-size: 14px; width: 14px; height: 14px; opacity: 0.8; }
    .clear-all-btn { font-size: 0.72rem; color: #A4ABC8; height: 28px; min-width: 0; padding: 0 8px; }

    .desc-chips {
      display: flex; flex-wrap: wrap; gap: 6px;
      margin: 4px 0 12px; max-height: 140px; overflow-y: auto;
    }
    .desc-chip {
      font-size: 0.72rem; background: #EBF0FE; color: #235CF4; border-radius: 12px;
      padding: 3px 12px; cursor: pointer; transition: background 0.15s;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 360px;
    }
    .desc-chip:hover { background: #C7D5FC; }
    .desc-chip.active { background: #235CF4; color: #fff; }
    .no-match { font-size: 0.75rem; color: #A4ABC8; padding: 4px 0; }

    .air-row {
      display: flex; align-items: center; gap: 12px; margin-top: 4px;
    }
    .air-table-field { flex: 1; }
    .air-ref { font-size: 0.68rem; color: #A4ABC8; white-space: nowrap; }
    .rec-badge {
      font-size: 0.6rem; background: #E8F5E9; color: #388E3C;
      padding: 1px 6px; border-radius: 8px; margin-left: 6px; font-weight: 600;
    }

    .search-btn { width: 100%; margin: 16px 0 32px; height: 48px; font-size: 1rem; }
  `],
})
export class RefineFiltersComponent implements OnChanges, OnInit {
  readonly dbConfig = inject(DatabaseConfigService);
  private readonly api = inject(ScenarioApiService);

  @Input() parsed!: ParsedScenario;
  @Input() airTables: AirTableProfile[] = [];
  @Input() airDescriptions: string[] = [];
  @Input() recommendedTable: string | null = null;
  @Input() autoExpand = false;

  @Output() filtersChanged = new EventEmitter<{
    peril: string; zone: string; lossLo: number; lossHi: number;
    filterMode: string; eventKeywords: string[]; useAir: boolean;
    airTableSchema: string; airTableName: string; magLo: number; magHi: number;
  }>();
  @Output() searchEvents = new EventEmitter<void>();

  peril = 'All';
  zone = '';
  lossLo = 0;
  lossHi = 300;
  selectedKeywords: string[] = [];
  descSearch = '';
  selectedAirTable = '';
  magLo = 0;
  magHi = 12;
  sliderMax = 50;

  zones: string[] = [];
  filteredZones: string[] = [];

  modelInfo: ModelInfoResponse = {};

  get selectedProfile(): AirTableProfile | null {
    return this.airTables.find(t => t.label === this.selectedAirTable) ?? this.airTables[0] ?? null;
  }

  get filteredDescriptions(): string[] {
    const q = this.descSearch.toLowerCase();
    return (q
      ? this.airDescriptions.filter(d => d.toLowerCase().includes(q))
      : this.airDescriptions
    ).slice(0, 30);
  }

  isSelected(d: string): boolean {
    return this.selectedKeywords.includes(d);
  }

  toggleKeyword(d: string): void {
    const idx = this.selectedKeywords.indexOf(d);
    if (idx === -1) {
      this.selectedKeywords = [...this.selectedKeywords, d];
    } else {
      this.selectedKeywords = this.selectedKeywords.filter(k => k !== d);
    }
    this.emitChange();
  }

  removeKeyword(kw: string): void {
    this.selectedKeywords = this.selectedKeywords.filter(k => k !== kw);
    this.emitChange();
  }

  clearKeywords(): void {
    this.selectedKeywords = [];
    this.emitChange();
  }

  ngOnInit(): void {
    this.api.getModelInfo().subscribe({
      next: (info) => { this.modelInfo = info; },
    });
  }

  ngOnChanges(): void {
    if (this.parsed) {
      if (this.parsed.peril) this.peril = this.parsed.peril;
      if (this.parsed.zone) this.zone = this.parsed.zone;
      if (this.parsed.loss_lo !== null) this.lossLo = this.parsed.loss_lo;
      if (this.parsed.loss_hi !== null) this.lossHi = this.parsed.loss_hi;
      if (this.parsed.event_keyword && this.selectedKeywords.length === 0) {
        this.selectedKeywords = [this.parsed.event_keyword];
      }
      if (this.parsed.mag_lo !== null) this.magLo = this.parsed.mag_lo;
      if (this.parsed.mag_hi !== null) this.magHi = this.parsed.mag_hi;
      this.updateSliderMax();
      this.loadZones();
      this.filterZones(this.zone);
    }
    if (this.recommendedTable && !this.selectedAirTable) {
      this.selectedAirTable = this.recommendedTable;
    }
    this.emitChange();
  }

  onLossChange(): void {
    this.updateSliderMax();
    this.emitChange();
  }

  private updateSliderMax(): void {
    const ceil = Math.ceil(this.lossHi / 10) * 10;
    this.sliderMax = Math.max(50, ceil + 10);
  }

  onPerilChange(): void {
    this.loadZones();
    this.emitChange();
  }

  private lastLoadedPeril = '__unset__';

  private loadZones(): void {
    if (this.peril === this.lastLoadedPeril) return;
    this.lastLoadedPeril = this.peril;
    this.api.getZones(this.peril).subscribe({
      next: (r) => {
        this.zones = r.zones;
        this.filterZones(this.zone);
      },
    });
  }

  onZoneInput(): void {
    this.filterZones(this.zone);
    this.emitChange();
  }

  filterZones(val: string): void {
    const q = (val || '').toLowerCase();
    this.filteredZones = (q
      ? this.zones.filter(z => z.toLowerCase().includes(q))
      : this.zones
    ).slice(0, 50);
  }

  onAirTableChange(): void {
    this.emitChange();
  }

  formatLoss(value: number): string {
    if (value >= 1) return `$${value}B`;
    return `$${(value * 1000).toFixed(0)}M`;
  }

  displayLoss = (value: number): string => `${value}`;
  displayMag  = (value: number): string => value.toFixed(1);

  emitChange(): void {
    const table = this.airTables.find(t => t.label === this.selectedAirTable);
    this.filtersChanged.emit({
      peril: this.peril,
      zone: this.zone,
      lossLo: this.lossLo,
      lossHi: this.lossHi,
      filterMode: 'Both',
      eventKeywords: this.selectedKeywords,
      useAir: true,
      airTableSchema: table?.schema ?? '',
      airTableName: table?.table ?? '',
      magLo: this.magLo,
      magHi: this.magHi,
    });
  }
}
