import { Component, inject, OnInit, signal, DestroyRef } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver } from '@angular/cdk/layout';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { SidebarComponent } from './shared/components/sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, MatSidenavModule, MatButtonModule, MatIconModule, SidebarComponent],
  template: `
    <mat-sidenav-container class="app-container">
      <mat-sidenav #sidenav [mode]="isMobile() ? 'over' : 'side'" [opened]="!isMobile()" class="app-sidebar">
        @if (isMobile()) {
          <button mat-icon-button class="close-btn" (click)="sidenav.close()">
            <mat-icon>close</mat-icon>
          </button>
        }
        <app-sidebar />
      </mat-sidenav>

      <mat-sidenav-content class="app-content">
        @if (isMobile()) {
          <div class="mobile-bar">
            <button mat-icon-button (click)="sidenav.toggle()">
              <mat-icon style="color:#fff">menu</mat-icon>
            </button>
            <span class="mobile-title">CAT-NIP</span>
          </div>
        }
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

    .close-btn {
      color: #7B83A6;
      display: block;
      margin: -12px -8px 8px auto;
    }

    .mobile-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #061C49;
      height: 56px;
      padding: 0 8px;
      margin: -24px -32px 16px;
    }

    .mobile-title {
      font-size: 1.1rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.05em;
    }

    @media (max-width: 960px) {
      .app-content { padding: 0 16px 24px; }
      .mobile-bar { margin: 0 -16px 16px; }
    }
  `],
})
export class AppComponent implements OnInit {
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly destroyRef = inject(DestroyRef);

  readonly isMobile = signal(false);

  ngOnInit(): void {
    this.breakpointObserver
      .observe(['(max-width: 960px)'])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(result => this.isMobile.set(result.matches));
  }
}
