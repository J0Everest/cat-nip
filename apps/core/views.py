from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings

from apps.db.utils import next_quarter
from apps.db.connection import run_sql
from apps.scenario.catalogs import PERIL_OPTIONS, DESIGN_TOKENS


class ConfigView(APIView):
    def get(self, request):
        return Response({
            "peril_options": PERIL_OPTIONS,
            "default_server": settings.DB_SERVER,
            "default_database": settings.DB_CATACCUM_DATABASE,
            "air_events_db": settings.AIR_EVENTS_DB,
            "design_tokens": DESIGN_TOKENS,
        })


class NextQuarterView(APIView):
    def post(self, request):
        database = request.data.get("database", settings.DB_CATACCUM_DATABASE)
        return Response({"database": next_quarter(database)})


class HealthView(APIView):
    def get(self, request):
        server = request.headers.get("X-DB-Server", settings.DB_SERVER)
        database = request.headers.get("X-DB-Database", settings.DB_CATACCUM_DATABASE)
        db_ok = False
        try:
            df = run_sql(server, database, "SELECT 1 AS ok")
            db_ok = df is not None and not df.empty
        except Exception:
            pass
        return Response({
            "status": "ok",
            "db_reachable": db_ok,
            "server": server,
            "database": database,
        })
