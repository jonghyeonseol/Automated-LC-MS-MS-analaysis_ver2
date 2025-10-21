"""
Core models - Base models and mixins
"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base class with created_at and updated_at timestamps
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base class with soft delete functionality
    """
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete - mark as deleted instead of removing from database"""
        self.deleted_at = timezone.now()
        self.is_deleted = True
        self.save(using=using)

    def hard_delete(self):
        """Permanently delete from database"""
        super().delete()

    def restore(self):
        """Restore soft-deleted object"""
        self.deleted_at = None
        self.is_deleted = False
        self.save()
