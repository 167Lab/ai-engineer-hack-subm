from django.db import models


class Node(models.Model):
    key = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=256)
    category = models.CharField(max_length=64)
    summary = models.TextField(blank=True, default="")
    io_signature = models.JSONField(default=dict)
    tags = models.JSONField(default=list)

    def __str__(self) -> str:
        return self.key


class NodeVersion(models.Model):
    STATUS_CHOICES = (
        ("stable", "stable"),
        ("beta", "beta"),
        ("deprecated", "deprecated"),
    )

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="versions")
    semver = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="stable")
    param_schema = models.JSONField(default=dict)
    runtimes = models.JSONField(default=dict)

    class Meta:
        unique_together = ("node", "semver")

    def __str__(self) -> str:
        return f"{self.node.key}@{self.semver}"


