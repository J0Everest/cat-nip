import { Routes } from '@angular/router';
import { ScenarioBuilderComponent } from './features/scenario-builder/scenario-builder.component';

export const routes: Routes = [
  { path: '', component: ScenarioBuilderComponent },
  { path: '**', redirectTo: '' },
];
