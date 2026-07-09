from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("search", "0005_searchindex_author_searchindex_upvotes_searchindex_title"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="searchindex",
            constraint=models.UniqueConstraint(
                fields=("type", "post"),
                condition=models.Q(type="post", post__isnull=False),
                name="search_index_unique_post_per_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="searchindex",
            constraint=models.UniqueConstraint(
                fields=("type", "comment"),
                condition=models.Q(type="comment", comment__isnull=False),
                name="search_index_unique_comment_per_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="searchindex",
            constraint=models.UniqueConstraint(
                fields=("type", "user"),
                condition=models.Q(type="user", user__isnull=False),
                name="search_index_unique_user_per_type",
            ),
        ),
    ]
