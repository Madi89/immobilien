from django.db import models


class ObjectItem(models.Model):
    header = models.CharField(max_length=255)
    obj_text = models.TextField()
    date = models.DateField()
    url = models.URLField(null=True, blank=True)