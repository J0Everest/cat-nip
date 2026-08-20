import { Component, Input, Output, EventEmitter, OnChanges, OnInit, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { DatabaseConfigService } from '../../../../core/services/database-config.service';
import { ScenarioApiService } from '../../../../core/services/scenario-api.service';
import { ParsedScenario, AirTableProfile, ModelInfoResponse, ModelEntry } from '../../../../core/models/scenario.models';

@Component({
  selector: 'app-refine-filters',
  imports: [
    DecimalPipe, FormsModule, MatExpansionModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatSliderModule, MatCheckboxModule,
    MatButtonModule, MatIconModule, MatChipsModule, MatProgressSpinnerModule, MatAutocompleteModule,
  ],
  template: `
    <mat-expansion-panel [expanded]="autoExpand" class="refine-panel">
      <mat-expansion-panel-header>
        <mat-panel-title>Refine Filters</mat-panel-title>
      </mat-expansion-panel-header>

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

      @if (availableRegions.length > 0) {
        <div class="region-section">
          <label class="region-label">Available Regions for {{ peril }}</label>
          <mat-chip-listbox [(ngModel)]="selectedRegion" (ngModelChange)="onRegionChange()">
            <mat-chip-option value="">All Regions</mat-chip-option>
            @for (r of availableRegions; track r) {
              <mat-chip-option [value]="r">{{ r }}</mat-chip-option>
            }
          </mat-chip-listbox>
          @if (regionModels.length > 0) {
            <div class="model-labels">
              @for (m of regionModels; track m.model_no) {
                <span class="model-chip">{{ m.label }}</span>
              }
            </div>
          }
        </div>
      }

      <div class="char-row">
        <mat-form-field appearance="outline" class="filter-field keyword-field">
          <mat-label>Event keyword or description</mat-label>
          <input matInput [(ngModel)]="eventKeyword" (ngModelChange)="emitChange()"
                 placeholder="{{ airDescriptions.length > 0 ? 'Type to filter ' + airDescriptions.length + ' descriptions...' : 'e.g. Florida, Gulf Coast...' }}">
          @if (eventKeyword) {
            <button matSuffix mat-icon-button (click)="clearKeyword()" aria-label="Clear">
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
          <div class="desc-chips">
            @for (d of filteredDescriptions; track d) {
              <span class="desc-chip" [class.active]="eventKeyword === d" (click)="onDescChipClick(d)">{{ d }}</span>
            }
            @if (filteredDescriptions.length === 0) {
              <span class="no-match">No descriptions match "{{ eventKeyword }}"</span>
            }
          </div>
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
    .keyword-field { flex: 2; }
    .slider-group { display: flex; flex-direction: column; }
    .slider-label { font-size: 0.78rem; color: #666; margin-bottom: 4px; }
    .air-table-field { width: 100%; margin-top: 8px; }
    .search-btn { width: 100%; margin: 16px 0 32px; height: 48px; font-size: 1rem; }
    .region-section { margin: 12px 0; }
    .region-label { font-size: 0.78rem; color: #666; display: block; margin-bottom: 6px; }
    .model-labels { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .model-chip {
      font-size: 0.7rem; background: #EBF0FE; color: #235CF4;
      padding: 2px 10px; border-radius: 12px; font-weight: 500;
    }
    .desc-chips {
      display: flex; flex-wrap: wrap; gap: 6px;
      margin: 8px 0 4px; max-height: 140px; overflow-y: auto;
    }
    .desc-chip {
      font-size: 0.72rem; background: #EBF0FE; color: #235CF4; border-radius: 12px;
      padding: 3px 10px; cursor: pointer; transition: background 0.15s;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 360px;
    }
    .desc-chip:hover { background: #C7D5FC; }
    .desc-chip.active { background: #235CF4; color: #fff; }
    .no-match { font-size: 0.75rem; color: #A4ABC8; padding: 4px 0; }
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
    filterMode: string; eventKeyword: string; useAir: boolean;
    airTableSchema: string; airTableName: string; magLo: number; magHi: number;
  }>();
  @Output() searchEvents = new EventEmitter<void>();

  peril = 'All';
  zone = '';
  lossLo = 0;
  lossHi = 300;
  eventKeyword = '';
  useAir = true;
  selectedAirTable = '';
  magLo = 0;
  magHi = 12;
  sliderMax = 50;

  zones: string[] = [];
  filteredZones: string[] = [];

  modelInfo: ModelInfoResponse = {};
  availableRegions: string[] = [];
  selectedRegion = '';
  regionModels: ModelEntry[] = [];

  get selectedProfile(): AirTableProfile | null {
    return this.airTables.find(t => t.label === this.selectedAirTable) ?? this.airTables[0] ?? null;
  }

  get filteredDescriptions(): string[] {
    const q = this.eventKeyword.toLowerCase();
    return (q
      ? this.airDescriptions.filter(d => d.toLowerCase().includes(q))
      : this.airDescriptions
    ).slice(0, 20);
  }

  ngOnInit(): void {
    this.api.getModelInfo().subscribe({
      next: (info) => {
        this.modelInfo = info;
        this.updateRegions();
      },
    });
  }

  ngOnChanges(): void {
    if (this.parsed) {
      if (this.parsed.peril) this.peril = this.parsed.peril;
      if (this.parsed.zone) this.zone = this.parsed.zone;
      if (this.parsed.loss_lo !== null) this.lossLo = this.parsed.loss_lo;
      if (this.parsed.loss_hi !== null) this.lossHi = this.parsed.loss_hi;
      if (this.parsed.event_keyword) this.eventKeyword = this.parsed.event_keyword;
      if (this.parsed.mag_lo !== null) this.magLo = this.parsed.mag_lo;
      if (this.parsed.mag_hi !== null) this.magHi = this.parsed.mag_hi;
      this.updateSliderMax();
      this.updateRegions();
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
    this.selectedRegion = '';
    this.updateRegions();
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

  onRegionChange(): void {
    this.updateRegionModels();
    this.emitChange();
  }

  private updateRegions(): void {
    if (this.peril && this.peril !== 'All' && this.modelInfo[this.peril]) {
      this.availableRegions = Object.keys(this.modelInfo[this.peril]);
    } else {
      this.availableRegions = [];
    }
    this.updateRegionModels();
  }

  private updateRegionModels(): void {
    if (!this.peril || this.peril === 'All' || !this.modelInfo[this.peril]) {
      this.regionModels = [];
      return;
    }
    const perilData = this.modelInfo[this.peril];
    if (this.selectedRegion && perilData[this.selectedRegion]) {
      this.regionModels = perilData[this.selectedRegion];
    } else {
      this.regionModels = Object.values(perilData).flat();
    }
  }

  onAirTableChange(): void {
    this.emitChange();
  }

  onDescChipClick(d: string): void {
    this.eventKeyword = d;
    this.emitChange();
  }

  clearKeyword(): void {
    this.eventKeyword = '';
    this.emitChange();
  }

  formatLoss(value: number): string {
    if (value >= 1) return `$${value}B`;
    return `$${(value * 1000).toFixed(0)}M`;
  }

  displayLoss = (value: number): string => {
    return `${value}`;
  };

  displayMag = (value: number): string => {
    return value.toFixed(1);
  };

  emitChange(): void {
    const table = this.airTables.find(t => t.label === this.selectedAirTable);
    this.filtersChanged.emit({
      peril: this.peril,
      zone: this.zone,
      lossLo: this.lossLo,
      lossHi: this.lossHi,
      filterMode: 'Both',
      eventKeyword: this.eventKeyword,
      useAir: this.useAir,
      airTableSchema: table?.schema ?? '',
      airTableName: table?.table ?? '',
      magLo: this.magLo,
      magHi: this.magHi,
    });
  }
}
