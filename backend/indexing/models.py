from django.db import models


class URLSubmission(models.Model):
    """Ek submit kiya hua URL."""

    # NOTE: unique=True nahi lagaya. MySQL (utf8mb4) mein itne lambe column par
    # unique index nahi ban sakta (3072 byte limit).
    url = models.URLField(max_length=2048)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']  # sabse naya sabse pehle

    def __str__(self):
        return self.url