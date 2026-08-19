import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatListModule } from '@angular/material/list';
import { DatePipe } from '@angular/common';
import { DatabaseConfigService } from '../../../core/services/database-config.service';
import { ScenarioApiService } from '../../../core/services/scenario-api.service';
import { SavedScenario } from '../../../core/models/event.models';

@Component({
  selector: 'app-sidebar',
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule, MatExpansionModule, MatListModule, DatePipe],
  template: `
    <div class="sidebar-header">
      <img src="static/angular/browser/everest-logo-white.png" alt="Everest" class="sidebar-logo">
      <h2>CAT-NIP</h2>
      <p class="subtitle">Catastrophe Scenario Explorer</p>
    </div>

    <mat-expansion-panel class="sidebar-panel db-panel" [expanded]="false">
      <mat-expansion-panel-header>
        <mat-panel-title>
          <mat-icon class="panel-icon">storage</mat-icon>
          <span>{{ databaseInput || 'Database' }}</span>
        </mat-panel-title>
      </mat-expansion-panel-header>

      <mat-form-field appearance="outline" class="sidebar-field">
        <mat-label>Server</mat-label>
        <input matInput [(ngModel)]="serverInput" (blur)="dbConfig.server.set(serverInput)">
      </mat-form-field>

      <mat-form-field appearance="outline" class="sidebar-field">
        <mat-label>Database</mat-label>
        <input matInput [(ngModel)]="databaseInput" (blur)="dbConfig.database.set(databaseInput)">
      </mat-form-field>

      <div class="sidebar-actions">
        <button mat-stroked-button (click)="advanceQuarter()">
          <mat-icon>skip_next</mat-icon> Next Qtr
        </button>
        <button mat-stroked-button (click)="testConnection()">
          <mat-icon>wifi_tethering</mat-icon> Test
        </button>
      </div>

      @if (connectionStatus) {
        <p class="connection-status" [class.ok]="connectionOk" [class.fail]="!connectionOk">
          {{ connectionStatus }}
        </p>
      }
    </mat-expansion-panel>

    <mat-expansion-panel class="sidebar-panel saved-panel" [expanded]="true">
      <mat-expansion-panel-header>
        <mat-panel-title>
          <mat-icon class="panel-icon">bookmark</mat-icon>
          <span>Saved Scenarios</span>
          @if (savedScenarios.length > 0) {
            <span class="badge">{{ savedScenarios.length }}</span>
          }
        </mat-panel-title>
      </mat-expansion-panel-header>

      @if (savedScenarios.length === 0) {
        <p class="empty-msg">No saved scenarios yet. Use the bookmark button after assigning events.</p>
      }

      @for (sc of savedScenarios; track sc.id) {
        <div class="saved-card" (click)="dbConfig.loadScenario$.next(sc)">
          <div class="saved-card-body">
            <div class="saved-name">{{ sc.name }}</div>
            <div class="saved-meta">
              <span class="saved-tag">{{ sc.peril || 'All' }}</span>
              <span>{{ sc.created_at | date:'MMM d, y' }}</span>
            </div>
          </div>
          <button mat-icon-button class="delete-btn" (click)="onDeleteScenario($event, sc.id)">
            <mat-icon>close</mat-icon>
          </button>
        </div>
      }
    </mat-expansion-panel>
  `,
  styles: [`
    :host { display: block; }
    .sidebar-logo {
      width: 140px;
      margin-bottom: 14px;
      opacity: 0.9;
    }
    .sidebar-header h2 {
      margin: 0 0 2px;
      font-weight: 700;
      font-size: 1.3rem;
      letter-spacing: 0.02em;
    }
    .subtitle {
      margin: 0 0 20px;
      font-size: 0.72rem;
      color: #7B83A6;
      letter-spacing: 0.01em;
    }

    .sidebar-panel {
      background: rgba(255,255,255,0.04) !important;
      color: #fff !important;
      border-radius: 10px !important;
      margin-bottom: 10px !important;
      box-shadow: none !important;
    }
    ::ng-deep .sidebar-panel .mat-expansion-panel-header {
      padding: 0 16px !important;
      height: 42px !important;
    }
    ::ng-deep .sidebar-panel .mat-expansion-panel-header-title {
      color: #C0C6DE !important;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    ::ng-deep .sidebar-panel .mat-expansion-indicator::after { color: #7B83A6 !important; }
    ::ng-deep .sidebar-panel .mat-expansion-panel-body { padding: 0 16px 14px !important; }
    .panel-icon { font-size: 16px; width: 16px; height: 16px; opacity: 0.6; }
    .badge {
      background: #235CF4;
      color: #fff;
      font-size: 0.6rem;
      padding: 1px 7px;
      border-radius: 10px;
      margin-left: auto;
      font-weight: 700;
      letter-spacing: 0;
      text-transform: none;
    }

    .sidebar-field {
      width: 100%;
      margin-bottom: 6px;
    }
    ::ng-deep .sidebar-field .mat-mdc-text-field-wrapper { background: rgba(255,255,255,0.06) !important; }
    ::ng-deep .sidebar-field .mdc-text-field--outlined .mdc-notched-outline__leading,
    ::ng-deep .sidebar-field .mdc-text-field--outlined .mdc-notched-outline__notch,
    ::ng-deep .sidebar-field .mdc-text-field--outlined .mdc-notched-outline__trailing { border-color: rgba(255,255,255,0.12) !important; }
    ::ng-deep .sidebar-field input { color: #E8EAF0 !important; font-size: 0.82rem; }
    ::ng-deep .sidebar-field .mat-mdc-form-field-label,
    ::ng-deep .sidebar-field .mdc-floating-label { color: #7B83A6 !important; }
    .sidebar-actions {
      display: flex;
      gap: 6px;
      margin-top: 2px;
    }
    .sidebar-actions button {
      color: #C0C6DE;
      border-color: rgba(255,255,255,0.12);
      font-size: 0.72rem;
      flex: 1;
    }
    .connection-status { font-size: 0.72rem; margin-top: 6px; }
    .connection-status.ok { color: #4ADE80; }
    .connection-status.fail { color: #F87171; }

    .empty-msg { color: #7B83A6; font-size: 0.75rem; margin: 4px 0; line-height: 1.5; }

    .saved-card {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      margin-bottom: 6px;
      background: rgba(255,255,255,0.06);
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .saved-card:hover { background: rgba(255,255,255,0.12); }
    .saved-card-body { flex: 1; min-width: 0; }
    .saved-name {
      font-size: 0.82rem;
      font-weight: 500;
      color: #E8EAF0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.4;
    }
    .saved-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.68rem;
      color: #7B83A6;
      margin-top: 2px;
    }
    .saved-tag {
      background: rgba(35,92,244,0.2);
      color: #8BAAFF;
      padding: 1px 8px;
      border-radius: 4px;
      font-size: 0.62rem;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .delete-btn {
      color: #7B83A6 !important;
      width: 28px !important;
      height: 28px !important;
      line-height: 28px !important;
    }
    ::ng-deep .delete-btn .mat-icon { font-size: 16px; width: 16px; height: 16px; }
    .delete-btn:hover { color: #F87171 !important; }
  `],
})
export class SidebarComponent implements OnInit {
  readonly dbConfig = inject(DatabaseConfigService);
  private readonly api = inject(ScenarioApiService);

  serverInput = '';
  databaseInput = '';
  connectionStatus = '';
  connectionOk = false;
  savedScenarios: SavedScenario[] = [];

  ngOnInit(): void {
    this.api.getConfig().subscribe({
      next: (cfg) => {
        this.dbConfig.server.set(cfg.default_server);
        this.dbConfig.database.set(cfg.default_database);
        this.dbConfig.airEventsDb.set(cfg.air_events_db);
        this.dbConfig.perilOptions.set(cfg.peril_options);
        this.serverInput = cfg.default_server;
        this.databaseInput = cfg.default_database;
      },
      error: () => {
        this.serverInput = 'ERRSACTDBP1';
        this.databaseInput = 'CatAccum2604';
        this.dbConfig.server.set(this.serverInput);
        this.dbConfig.database.set(this.databaseInput);
        this.dbConfig.perilOptions.set(['All', 'EQ', 'TC', 'Winter Storm', 'Severe Storm', 'Fire / Wildfire', 'Flood']);
      },
    });
    this.refreshSavedScenarios();
    this.dbConfig.scenarioSaved$.subscribe(() => this.refreshSavedScenarios());
  }

  refreshSavedScenarios(): void {
    this.api.listSavedScenarios().subscribe({
      next: (list) => this.savedScenarios = list,
    });
  }

  advanceQuarter(): void {
    this.api.nextQuarter(this.dbConfig.database()).subscribe({
      next: (res) => {
        this.databaseInput = res.database;
        this.dbConfig.database.set(res.database);
      },
    });
  }

  testConnection(): void {
    this.connectionStatus = 'Testing...';
    this.api.healthCheck().subscribe({
      next: (res) => {
        this.connectionOk = res.db_reachable;
        this.connectionStatus = res.db_reachable ? 'Connected' : 'DB unreachable';
      },
      error: () => {
        this.connectionOk = false;
        this.connectionStatus = 'API unreachable';
      },
    });
  }

  onDeleteScenario(event: Event, id: number): void {
    event.stopPropagation();
    this.api.deleteSavedScenario(id).subscribe({
      next: () => this.refreshSavedScenarios(),
    });
  }
}
