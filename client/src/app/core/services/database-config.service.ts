import { Injectable, signal, computed } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class DatabaseConfigService {
  readonly server = signal('');
  readonly database = signal('');
  readonly airEventsDb = signal('');
  readonly perilOptions = signal<string[]>([]);

  readonly isConfigured = computed(() => !!this.server() && !!this.database());
}
