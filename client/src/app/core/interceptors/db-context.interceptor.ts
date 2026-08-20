import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { DatabaseConfigService } from '../services/database-config.service';

export const dbContextInterceptor: HttpInterceptorFn = (req, next) => {
  const dbConfig = inject(DatabaseConfigService);
  const server = dbConfig.server();
  const database = dbConfig.database();

  if (server || database) {
    const headers: Record<string, string> = {};
    if (server) headers['X-DB-Server'] = server;
    if (database) headers['X-DB-Database'] = database;
    req = req.clone({ setHeaders: headers });
  }

  return next(req);
};
