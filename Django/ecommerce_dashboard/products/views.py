from django.shortcuts import render
from .models import Product, Recommendation


def home(request):
    products = Product.objects.all()

    return render(
        request,
        "products/home.html",
        {
            "products": products
        }
    )


def recommendations(request):
    recs = Recommendation.objects.order_by("recommendation_rank")[:20]

    recommended_products = []

    for rec in recs:
        try:
            product = Product.objects.get(product_id=rec.product_id)

            recommended_products.append({
                "product": product,
                "user_id": rec.user_id,
                "rank": rec.recommendation_rank,
            })

        except Product.DoesNotExist:
            # Ignore recommendations whose product doesn't exist
            pass

    return render(
        request,
        "products/recommendations.html",
        {
            "recommended_products": recommended_products
        }
    )