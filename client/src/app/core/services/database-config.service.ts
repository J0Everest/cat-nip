import { Injectable, signal, computed } from '@angular/core';
import { Subject } from 'rxjs';
import { SavedScenario } from '../models/event.models';

@Injectable({ providedIn: 'root' })
export class DatabaseConfigService {
  readonly server = signal('');
  readonly database = signal('');
  readonly airEventsDb = signal('');
  readonly perilOptions = signal<string[]>([]);

  readonly isConfigured = computed(() => !!this.server() && !!this.database());

  readonly loadScenario$ = new Subject<SavedScenario>();
  readonly scenarioSaved$ = new Subject<void>();
}
