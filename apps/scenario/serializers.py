from rest_framework import serializers


class ParseQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000)


class ParsedScenarioSerializer(serializers.Serializer):
    peril = serializers.CharField(allow_null=True)
    zone = serializers.CharField(allow_null=True)
    model_no = serializers.IntegerField(allow_null=True)
    loss_lo = serializers.FloatField(allow_null=True)
    loss_hi = serializers.FloatField(allow_null=True)
    mag_lo = serializers.FloatField(allow_null=True)
    mag_hi = serializers.FloatField(allow_null=True)
    event_keyword = serializers.CharField(allow_null=True)
    confidence = serializers.CharField()
    confidence_parts = serializers.IntegerField()
    confidence_total = serializers.IntegerField()


class AirEnrichmentSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(default=False)
    table_schema = serializers.CharField(required=False, allow_blank=True)
    table_name = serializers.CharField(required=False, allow_blank=True)
    mag_lo = serializers.FloatField(default=0.0)
    mag_hi = serializers.FloatField(default=12.0)


class SearchEventsSerializer(serializers.Serializer):
    peril = serializers.CharField(default="All")
    zone_filter = serializers.CharField(default="", allow_blank=True)
    loss_lo = serializers.FloatField(default=0.0)
    loss_hi = serializers.FloatField(default=300.0)
    filter_mode = serializers.ChoiceField(
        choices=["Industry Loss", "Event Characteristics", "Both"],
        default="Industry Loss",
    )
    event_keyword = serializers.CharField(default="", allow_blank=True)
    air_enrichment = AirEnrichmentSerializer(required=False)


class AnalyzeSerializer(serializers.Serializer):
    low_event_id = serializers.IntegerField(min_value=0)
    med_event_id = serializers.IntegerField(min_value=0)
    high_event_id = serializers.IntegerField(min_value=0)


class PreviewSqlSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["search", "waterfall"])
    zone_filter = serializers.CharField(default="", allow_blank=True)
    loss_lo = serializers.FloatField(default=0.0)
    loss_hi = serializers.FloatField(default=300.0)
    peril = serializers.CharField(default="All")
    filter_mode = serializers.CharField(default="Industry Loss")
    event_keyword = serializers.CharField(default="", allow_blank=True)
    low_event_id = serializers.IntegerField(required=False, default=0)
    med_event_id = serializers.IntegerField(required=False, default=0)
    high_event_id = serializers.IntegerField(required=False, default=0)


class NextQuarterSerializer(serializers.Serializer):
    database = serializers.CharField(max_length=100)
