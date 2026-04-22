from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('dosen', 'Dosen'),
        ('kaprodi', 'Kepala Prodi'),
        ('dekan', 'Dekan'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='dosen')
    fakultas = models.CharField(max_length=100, blank=True, null=True)
    prodi = models.CharField(max_length=100, blank=True, null=True)
    nidn = models.CharField(max_length=20, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

class Activity(models.Model):
    CATEGORY_CHOICES = (
        ('penelitian', 'Penelitian'),
        ('pengabdian', 'Pengabdian Masyarakat'),
    )
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_kaprodi', 'Pending Kaprodi'),
        ('pending_dekan', 'Pending Dekan'),
        ('approved', 'Approved'),
        ('revision', 'Revisi'),
        ('rejected', 'Ditolak'),
    )

    dosen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    dana = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    proposal_file = models.FileField(upload_to='proposals/')
    report_file = models.FileField(upload_to='reports/', blank=True, null=True)
    output_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Milestone(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='milestones')
    status = models.CharField(max_length=255)
    note = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Activity.STATUS_CHOICES)
    score = models.IntegerField(default=0, help_text="Nilai dari 0-100")
    comments = models.TextField()
    level = models.IntegerField() # 1 for Kaprodi, 2 for Dekan
    created_at = models.DateTimeField(auto_now_add=True)

class Logbook(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='logbooks')
    date = models.DateField()
    description = models.TextField()
    file_evidence = models.FileField(upload_to='logbooks/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Logbook {self.date} - {self.activity.title}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
