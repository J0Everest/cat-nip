from django.db import models


class SavedScenario(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    query_text = models.TextField(blank=True, default="")
    peril = models.CharField(max_length=50, blank=True, default="")
    zone = models.CharField(max_length=100, blank=True, default="")
    loss_lo = models.FloatField(default=0.0)
    loss_hi = models.FloatField(default=300.0)
    filter_mode = models.CharField(max_length=30, default="Industry Loss")
    event_keyword = models.CharField(max_length=200, blank=True, default="")

    low_event_id = models.IntegerField(default=0)
    med_event_id = models.IntegerField(default=0)
    high_event_id = models.IntegerField(default=0)

    database = models.CharField(max_length=100, blank=True, default="")
    candidate_event_ids = models.JSONField(default=list)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name
