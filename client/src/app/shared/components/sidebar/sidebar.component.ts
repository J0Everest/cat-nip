import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatExpansionModule } from '@angular/material/expansion';
import { DatabaseConfigService } from '../../../core/services/database-config.service';
import { ScenarioApiService } from '../../../core/services/scenario-api.service';

@Component({
  selector: 'app-sidebar',
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatIconModule, MatExpansionModule],
  template: `
    <div class="sidebar-header">
      <h2>CAT-NIP</h2>
      <p class="subtitle">Catastrophe Scenario Explorer</p>
    </div>

    <mat-expansion-panel class="db-panel" [expanded]="true">
      <mat-expansion-panel-header>
        <mat-panel-title>Database</mat-panel-title>
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
          <mat-icon>skip_next</mat-icon> Next Quarter
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
  `,
  styles: [`
    :host { display: block; }
    .sidebar-header h2 {
      margin: 0 0 4px;
      font-weight: 700;
      font-size: 1.4rem;
      letter-spacing: 0.02em;
    }
    .subtitle {
      margin: 0 0 24px;
      font-size: 0.78rem;
      color: #A4ABC8;
    }
    .db-panel {
      background: rgba(255,255,255,0.06) !important;
      color: #fff !important;
    }
    ::ng-deep .db-panel .mat-expansion-panel-header-title { color: #A4ABC8 !important; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
    .sidebar-field {
      width: 100%;
      margin-bottom: 8px;
    }
    ::ng-deep .sidebar-field .mat-mdc-text-field-wrapper { background: rgba(255,255,255,0.08) !important; }
    ::ng-deep .sidebar-field .mdc-text-field--outlined .mdc-notched-outline__leading,
    ::ng-deep .sidebar-field .mdc-text-field--outlined .mdc-notched-outline__notch,
    ::ng-deep .sidebar-field .mdc-text-field--outlined .mdc-notched-outline__trailing { border-color: rgba(255,255,255,0.15) !important; }
    ::ng-deep .sidebar-field input { color: #fff !important; }
    ::ng-deep .sidebar-field .mat-mdc-form-field-label { color: #A4ABC8 !important; }
    .sidebar-actions {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }
    .sidebar-actions button { color: #fff; border-color: rgba(255,255,255,0.2); font-size: 0.78rem; }
    .connection-status { font-size: 0.75rem; margin-top: 8px; }
    .connection-status.ok { color: #198038; }
    .connection-status.fail { color: #DA1E28; }
  `],
})
export class SidebarComponent implements OnInit {
  readonly dbConfig = inject(DatabaseConfigService);
  private readonly api = inject(ScenarioApiService);

  serverInput = '';
  databaseInput = '';
  connectionStatus = '';
  connectionOk = false;

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
}
