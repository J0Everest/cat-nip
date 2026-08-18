import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { SidebarComponent } from './shared/components/sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatSidenavModule, SidebarComponent],
  template: `
    <mat-sidenav-container class="app-container">
      <mat-sidenav mode="side" opened class="app-sidebar">
        <app-sidebar />
      </mat-sidenav>
      <mat-sidenav-content class="app-content">
        <router-outlet />
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .app-container { height: 100vh; }
    .app-sidebar {
      width: 280px;
      background: #061C49;
      color: #fff;
      padding: 24px 20px;
    }
    .app-content {
      padding: 24px 32px;
      background: #F5F5F5;
    }
  `],
})
export class AppComponent {}
