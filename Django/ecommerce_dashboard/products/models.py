from django.db import models
from django.http import HttpResponse

# Create your models here.
from django.db import models


class Product(models.Model):

    product_id = models.CharField(max_length=20, primary_key=True)

    name = models.CharField(max_length=255)

    category = models.CharField(max_length=100)

    brand = models.CharField(max_length=100)

    price = models.FloatField()

    description = models.TextField()

    image = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Recommendation(models.Model):
    id = models.AutoField(primary_key=True)

    user_id = models.TextField()
    recommendation_rank = models.IntegerField()
    product_id = models.TextField()
    product_name = models.TextField()
    category_name = models.TextField()
    als_score = models.FloatField()
    content_score = models.FloatField()
    hybrid_score = models.FloatField()
    generated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "recommendations"

