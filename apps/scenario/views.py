import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.conf import settings

from apps.db.connection import run_sql
from apps.scenario.models import SavedScenario
from apps.scenario.catalogs import MODEL_CATALOG, _PERIL_TO_MODELS
from apps.scenario.serializers import (
    ParseQuerySerializer, SearchEventsSerializer,
    AnalyzeSerializer, PreviewSqlSerializer,
    SavedScenarioSerializer,
)
from apps.scenario.services import (
    parse_scenario_query, compute_confidence,
    discover_air_event_tables, prefilter_air_profiles_by_peril,
    infer_model_from_industry, match_table_by_model,
    infer_table_by_keyword_match, fetch_air_event_details,
    fetch_air_descriptions_for_peril, best_fallback_table,
    get_distinct_zones,
)
from apps.scenario.sql_builders import build_event_search_sql, build_output_sql


def _get_db_context(request):
    server = request.headers.get("X-DB-Server", settings.DB_SERVER)
    database = request.headers.get("X-DB-Database", settings.DB_CATACCUM_DATABASE)
    return server, database


class ParseQueryView(APIView):
    def post(self, request):
        ser = ParseQuerySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        parsed = parse_scenario_query(ser.validated_data["query"])
        confidence, parts, total = compute_confidence(parsed)
        return Response({
            **parsed,
            "confidence": confidence,
            "confidence_parts": parts,
            "confidence_total": total,
        })


class AirTablesView(APIView):
    def get(self, request):
        server, database = _get_db_context(request)
        peril = request.query_params.get("peril", "All")
        scenario_text = request.query_params.get("scenario_text", "")
        zone_filter = request.query_params.get("zone_filter", "")

        all_profiles = discover_air_event_tables(server, database)
        profiles, prefiltered = prefilter_air_profiles_by_peril(all_profiles, peril)

        recommended = None
        if profiles:
            labels = [f"{p['schema']}.{p['table']}" for p in profiles]
            recommended = infer_table_by_keyword_match(
                server, database, profiles, peril, zone_filter, scenario_text
            )
            if not recommended:
                model_hint = infer_model_from_industry(server, database, peril, zone_filter)
                if model_hint:
                    recommended = match_table_by_model(labels, model_hint)
            if not recommended and labels:
                recommended = best_fallback_table(profiles, zone_filter)
            if not recommended and labels:
                recommended = labels[0]

        return Response({
            "tables": [
                {
                    "schema": p["schema"],
                    "table": p["table"],
                    "label": f"{p['schema']}.{p['table']}",
                    "event_id_col": p["event_id_col"],
                    "desc_col": p.get("desc_col"),
                    "mag_col": p.get("mag_col"),
                    "loc_col": p.get("loc_col"),
                }
                for p in profiles
            ],
            "prefiltered": prefiltered,
            "recommended_table": recommended,
        })


class AirDescriptionsView(APIView):
    def get(self, request):
        server, database = _get_db_context(request)
        peril = request.query_params.get("peril", "All")
        zone_filter = request.query_params.get("zone_filter", "")
        table_schema = request.query_params.get("table_schema", "")
        table_name = request.query_params.get("table_name", "")

        if not table_schema or not table_name:
            return Response({"descriptions": []})

        all_profiles = discover_air_event_tables(server, database)
        profile = next(
            (p for p in all_profiles if p["schema"] == table_schema and p["table"] == table_name),
            None,
        )
        if not profile:
            return Response({"descriptions": []})

        descriptions = fetch_air_descriptions_for_peril(
            server, database, profile, peril, zone_filter
        )
        return Response({"descriptions": descriptions})


class SearchEventsView(APIView):
    def post(self, request):
        ser = SearchEventsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        server, database = _get_db_context(request)

        air = d.get("air_enrichment", {})
        use_air = air.get("enabled", True)  # always enriched

        # Resolve keyword list: prefer explicit list, fall back to single string
        keywords = [k.strip() for k in d.get("event_keywords", []) if k.strip()]
        if not keywords and d.get("event_keyword", "").strip():
            keywords = [d["event_keyword"].strip()]

        event_kw_for_sql = "" if use_air else (keywords[0] if keywords else "")

        try:
            sql = build_event_search_sql(
                database, d["zone_filter"], d["loss_lo"], d["loss_hi"],
                d["peril"], d["filter_mode"], event_kw_for_sql,
            )
            df = run_sql(server, database, sql)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if df is None or df.empty:
            return Response({"events": [], "count": 0})

        if use_air and air.get("table_schema") and air.get("table_name"):
            all_profiles = discover_air_event_tables(server, database)
            profile = next(
                (p for p in all_profiles
                 if p["schema"] == air["table_schema"] and p["table"] == air["table_name"]),
                None,
            )
            if profile:
                event_ids = [int(v) for v in df["EventID"].dropna().tolist()]
                air_df = fetch_air_event_details(server, database, event_ids, profile)
                if air_df is not None and not air_df.empty:
                    df = df.merge(air_df, on="EventID", how="left")
                    if keywords and "AIR_Description" in df.columns:
                        mask = df["AIR_Description"].astype(str).str.contains(
                            keywords[0], case=False, na=False
                        )
                        for kw in keywords[1:]:
                            mask |= df["AIR_Description"].astype(str).str.contains(
                                kw, case=False, na=False
                            )
                        df = df[mask]
                    mag_lo = air.get("mag_lo", 0.0)
                    mag_hi = air.get("mag_hi", 12.0)
                    if not (float(mag_lo) <= 0.0 and float(mag_hi) >= 12.0):
                        if "AIR_Magnitude" in df.columns:
                            mag_vals = pd.to_numeric(df["AIR_Magnitude"], errors="coerce")
                            df = df[(mag_vals >= float(mag_lo)) & (mag_vals <= float(mag_hi))]

        events = []
        for _, row in df.iterrows():
            event = {
                "event_id": int(row.get("EventID", 0)),
                "description": str(row.get("Description", "")),
                "peril": str(row.get("Peril", "")),
                "industry_loss_b": float(row.get("Industry Loss ($B)", 0)),
            }
            if "AIR_Description" in row.index:
                event["air_description"] = str(row["AIR_Description"]) if pd.notna(row["AIR_Description"]) else None
            if "AIR_Magnitude" in row.index:
                event["air_magnitude"] = float(row["AIR_Magnitude"]) if pd.notna(row["AIR_Magnitude"]) else None
            if "AIR_Location" in row.index:
                event["air_location"] = str(row["AIR_Location"]) if pd.notna(row["AIR_Location"]) else None
            events.append(event)

        return Response({"events": events, "count": len(events)})


class AnalyzeView(APIView):
    def post(self, request):
        ser = AnalyzeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        server, database = _get_db_context(request)

        try:
            sql = build_output_sql(database, d["low_event_id"], d["med_event_id"], d["high_event_id"])
            df = run_sql(server, database, sql)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if df is None or df.empty:
            return Response({"summary": [], "contracts": [], "detail": [], "generated_sql": sql})

        summary_df = (
            df.groupby("Scenario", dropna=False)
            .agg(
                contracts=("Contract #", "nunique"),
                industry_b=("Industry Loss ($B)", "max"),
                gross_m=("Gross Loss $M", "sum"),
                net_m=("Net Loss $M", "sum"),
            )
            .reset_index()
        )
        summary_df["market_share_pct"] = (
            summary_df["gross_m"] / (summary_df["industry_b"] * 1000.0) * 100.0
        ).where(summary_df["industry_b"] > 0, 0.0)

        order = pd.CategoricalDtype(categories=["Low", "Med", "High"], ordered=True)
        summary_df["Scenario"] = summary_df["Scenario"].astype(order)
        summary_df = summary_df.sort_values("Scenario").reset_index(drop=True)

        summary = [
            {
                "scenario": row["Scenario"],
                "gross_loss_m": round(float(row["gross_m"]), 4),
                "net_loss_m": round(float(row["net_m"]), 4),
                "contracts": int(row["contracts"]),
                "industry_loss_b": float(row["industry_b"]),
                "market_share_pct": round(float(row["market_share_pct"]), 4),
            }
            for _, row in summary_df.iterrows()
        ]

        gross_pivot = df.pivot_table(
            index=["layerkey", "Department", "Company", "SubType", "Contract #",
                   "Terms", "100% Limit ($)", "ROL", "Share"],
            columns="Scenario",
            values="Gross Loss $M",
            aggfunc="sum",
            fill_value=0.0,
        ).reset_index()
        for sc in ["Low", "Med", "High"]:
            if sc not in gross_pivot.columns:
                gross_pivot[sc] = 0.0

        net_pivot = df.pivot_table(
            index=["layerkey"],
            columns="Scenario",
            values="Net Loss $M",
            aggfunc="sum",
            fill_value=0.0,
        ).reset_index()
        for sc in ["Low", "Med", "High"]:
            if sc not in net_pivot.columns:
                net_pivot[sc] = 0.0
        net_pivot = net_pivot.rename(columns={"Low": "Net_Low", "Med": "Net_Med", "High": "Net_High"})

        pivot = gross_pivot.merge(net_pivot[["layerkey", "Net_Low", "Net_Med", "Net_High"]], on="layerkey", how="left")

        contracts = [
            {
                "layerkey": str(int(row.get("layerkey", 0))),
                "department": str(row.get("Department", "")),
                "company": str(row.get("Company", "")),
                "subtype": str(row.get("SubType", "")),
                "contract": str(row.get("Contract #", "")),
                "terms": str(row.get("Terms", "")),
                "everest_limit": float(row.get("100% Limit ($)", 0)),
                "rol": float(row.get("ROL", 0)),
                "share": float(row.get("Share", 0)),
                "low_gross_m": round(float(row.get("Low", 0)), 4),
                "med_gross_m": round(float(row.get("Med", 0)), 4),
                "high_gross_m": round(float(row.get("High", 0)), 4),
                "low_net_m": round(float(row.get("Net_Low", 0)), 4),
                "med_net_m": round(float(row.get("Net_Med", 0)), 4),
                "high_net_m": round(float(row.get("Net_High", 0)), 4),
            }
            for _, row in pivot.iterrows()
        ]

        detail = [
            {
                "layerkey": str(int(row.get("layerkey", 0))),
                "scenario": str(row.get("Scenario", "")),
                "department": str(row.get("Department", "")),
                "company": str(row.get("Company", "")),
                "contract": str(row.get("Contract #", "")),
                "industry_loss_b": float(row.get("Industry Loss ($B)", 0)),
                "gross_loss_m": round(float(row.get("Gross Loss $M", 0)), 4),
                "reins_recovery_m": round(float(row.get("Reins Recovery $M", 0)), 4),
                "net_loss_m": round(float(row.get("Net Loss $M", 0)), 4),
            }
            for _, row in df.iterrows()
        ]

        return Response({
            "summary": summary,
            "contracts": contracts,
            "detail": detail,
            "generated_sql": sql,
        })


class PreviewSqlView(APIView):
    def post(self, request):
        ser = PreviewSqlSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        _, database = _get_db_context(request)

        if d["type"] == "search":
            sql = build_event_search_sql(
                database, d["zone_filter"], d["loss_lo"], d["loss_hi"],
                d["peril"], d["filter_mode"], d["event_keyword"],
            )
        else:
            sql = build_output_sql(
                database, d["low_event_id"], d["med_event_id"], d["high_event_id"],
            )
        return Response({"sql": sql})


class SavedScenarioListCreateView(ListCreateAPIView):
    queryset = SavedScenario.objects.all()
    serializer_class = SavedScenarioSerializer


class SavedScenarioDetailView(RetrieveUpdateDestroyAPIView):
    queryset = SavedScenario.objects.all()
    serializer_class = SavedScenarioSerializer


class ModelInfoView(APIView):
    def get(self, request):
        result: dict[str, dict[str, list[dict]]] = {}
        for peril_name, model_nos in _PERIL_TO_MODELS.items():
            regions: dict[str, list[dict]] = {}
            for mno in model_nos:
                entry = MODEL_CATALOG.get(mno)
                if not entry:
                    continue
                region = entry["region"]
                regions.setdefault(region, []).append({
                    "model_no": mno,
                    "label": entry["label"],
                })
            if regions:
                result[peril_name] = regions
        return Response(result)


class ZonesView(APIView):
    def get(self, request):
        server, database = _get_db_context(request)
        peril = request.query_params.get("peril", "All")
        zones = get_distinct_zones(server, database, peril)
        return Response({"zones": zones})
