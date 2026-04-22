from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.http import HttpResponse
import csv

from .models import Activity, Milestone, Review, Notification, User
from .forms import ActivityForm, ReportForm, ProfileForm, UserAdminCreationForm, UserAdminChangeForm

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

# ─── AUTH ─────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Selamat datang kembali, {user.get_full_name() or username}!")
                return redirect('dashboard')
        messages.error(request, "Username atau password salah.")
    else:
        form = AuthenticationForm()
    return render(request, 'monitoring/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "Anda telah berhasil logout.")
    return redirect('login')

# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    if user.role == 'dosen':
        activities = Activity.objects.filter(dosen=user).order_by('-updated_at')
        stats = {
            'total_usulan': activities.count(),
            'selesai': activities.filter(status='approved').count(),
            'revision_count': activities.filter(status='revision').count(),
            'serapan_dana': activities.filter(status='approved').aggregate(total=Sum('dana'))['total'] or 0,
        }
    elif user.role == 'kaprodi':
        activities = Activity.objects.filter(status='pending_kaprodi').order_by('-updated_at')
        stats = {
            'total_pending': activities.count(),
            'total_approved': Activity.objects.filter(status__in=['pending_dekan', 'approved']).count(),
        }
    elif user.role == 'dekan':
        activities = Activity.objects.filter(status='pending_dekan').order_by('-updated_at')
        stats = {
            'total_pending': activities.count(),
            'total_approved': Activity.objects.filter(status='approved').count(),
        }
    else:  # admin
        activities = Activity.objects.all().order_by('-updated_at')
        stats = {
            'total_usulan': activities.count(),
            'selesai': activities.filter(status='approved').count(),
            'serapan_dana': activities.filter(status='approved').aggregate(total=Sum('dana'))['total'] or 0,
        }

    notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
    unread_count = Notification.objects.filter(user=user, is_read=False).count()

    context = {
        'activities': activities[:10],
        'notifications': notifications,
        'unread_count': unread_count,
        'stats': stats,
    }
    return render(request, 'monitoring/dashboard.html', context)

# ─── ACTIVITY LIST ────────────────────────────────────────────────────────────

@login_required
def activity_list(request):
    user = request.user
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '')

    if user.role == 'dosen':
        qs = Activity.objects.filter(dosen=user)
    elif user.role == 'kaprodi':
        qs = Activity.objects.filter(status='pending_kaprodi')
    elif user.role == 'dekan':
        qs = Activity.objects.filter(status='pending_dekan')
    else:
        qs = Activity.objects.all()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category=category_filter)
    if search_query:
        qs = qs.filter(title__icontains=search_query)

    qs = qs.order_by('-updated_at')
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'status_choices': Activity.STATUS_CHOICES,
        'category_choices': Activity.CATEGORY_CHOICES,
    }
    return render(request, 'monitoring/activity_list.html', context)

# ─── ACTIVITY CREATE ──────────────────────────────────────────────────────────

@login_required
def activity_create(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.dosen = request.user
            activity.status = request.POST.get('status', 'draft')
            activity.save()
            Milestone.objects.create(
                activity=activity,
                status=f"Usulan {activity.get_status_display()}",
                note="Usulan baru dibuat oleh dosen.",
                updated_by=request.user
            )
            messages.success(request, f"Usulan '{activity.title}' berhasil disimpan sebagai {activity.get_status_display()}.")
            return redirect('dashboard')
    else:
        form = ActivityForm()
    return render(request, 'monitoring/activity_form.html', {'form': form, 'mode': 'create'})

# ─── ACTIVITY EDIT ────────────────────────────────────────────────────────────

@login_required
def activity_edit(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.user != activity.dosen:
        messages.error(request, "Anda tidak memiliki akses untuk mengedit kegiatan ini.")
        return redirect('dashboard')
    if activity.status not in ['draft', 'revision']:
        messages.error(request, "Kegiatan ini tidak dapat diedit pada status saat ini.")
        return redirect('activity_detail', pk=pk)
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.status = request.POST.get('status', 'draft')
            updated.save()
            note_msg = "Dosen melakukan revisi dan menyimpan sebagai draft." if updated.status == 'draft' else "Dosen melakukan revisi dan mengirim ulang usulan."
            Milestone.objects.create(
                activity=updated, status=f"Diperbarui: {updated.get_status_display()}",
                note=note_msg, updated_by=request.user
            )
            messages.success(request, f"Usulan '{updated.title}' berhasil diperbarui.")
            return redirect('activity_detail', pk=pk)
    else:
        form = ActivityForm(instance=activity)
    return render(request, 'monitoring/activity_edit.html', {'form': form, 'activity': activity})

# ─── ACTIVITY DETAIL ──────────────────────────────────────────────────────────

@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    milestones = activity.milestones.all().order_by('-created_at')
    reviews = activity.reviews.all().order_by('-created_at')
    show_review_form = (
        (request.user.role == 'kaprodi' and activity.status == 'pending_kaprodi') or
        (request.user.role == 'dekan' and activity.status == 'pending_dekan')
    )
    can_edit = (request.user == activity.dosen and activity.status in ['draft', 'revision'])
    can_upload_report = (request.user == activity.dosen and activity.status == 'approved')
    report_form = ReportForm(instance=activity) if can_upload_report else None

    context = {
        'activity': activity,
        'milestones': milestones,
        'reviews': reviews,
        'show_review_form': show_review_form,
        'can_edit': can_edit,
        'can_upload_report': can_upload_report,
        'report_form': report_form,
    }
    return render(request, 'monitoring/activity_detail.html', context)

# ─── ACTIVITY REVIEW ──────────────────────────────────────────────────────────

@login_required
def activity_review(request, pk):
    if request.method != 'POST':
        return redirect('dashboard')
    activity = get_object_or_404(Activity, pk=pk)
    status_input = request.POST.get('status')
    comments = request.POST.get('comments')

    if request.user.role == 'kaprodi' and activity.status == 'pending_kaprodi':
        level = 1
        activity.status = 'pending_dekan' if status_input == 'approved' else status_input
    elif request.user.role == 'dekan' and activity.status == 'pending_dekan':
        level = 2
        activity.status = status_input if status_input != 'approved' else 'approved'
    else:
        messages.error(request, "Anda tidak memiliki akses untuk mereview kegiatan ini.")
        return redirect('activity_detail', pk=pk)

    activity.save()
    Review.objects.create(activity=activity, reviewer=request.user,
                          status=status_input, comments=comments, level=level)
    Milestone.objects.create(
        activity=activity,
        status=f"Review {request.user.get_role_display()}: {activity.get_status_display()}",
        note=comments, updated_by=request.user
    )
    Notification.objects.create(
        user=activity.dosen,
        message=f"Kegiatan '{activity.title}' direview oleh {request.user.get_role_display()}. Status: {activity.get_status_display()}"
    )
    messages.success(request, f"Review berhasil. Status: {activity.get_status_display()}.")
    return redirect('activity_detail', pk=pk)

# ─── SUBMIT REPORT ────────────────────────────────────────────────────────────

@login_required
def activity_submit_report(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if request.user != activity.dosen or activity.status != 'approved':
        messages.error(request, "Tidak dapat mengunggah laporan untuk kegiatan ini.")
        return redirect('activity_detail', pk=pk)
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            form.save()
            Milestone.objects.create(
                activity=activity, status="Laporan Akhir Diunggah",
                note="Dosen mengunggah laporan akhir kegiatan.", updated_by=request.user
            )
            messages.success(request, "Laporan berhasil diunggah!")
    return redirect('activity_detail', pk=pk)

# ─── STATISTIK ────────────────────────────────────────────────────────────────

@login_required
def dosen_statistics(request):
    user = request.user
    if user.role not in ['kaprodi', 'dekan', 'admin']:
        messages.error(request, "Anda tidak memiliki akses ke halaman statistik dosen.")
        return redirect('dashboard')

    dosen_list = User.objects.filter(role='dosen')

    if user.role == 'kaprodi':
        dosen_list = dosen_list.filter(prodi=user.prodi)
    elif user.role == 'dekan':
        dosen_list = dosen_list.filter(fakultas=user.fakultas)

    from decimal import Decimal
    dosen_stats = dosen_list.annotate(
        total_penelitian=Count('activities', filter=Q(activities__category='penelitian')),
        total_pengabdian=Count('activities', filter=Q(activities__category='pengabdian')),
        total_dana=Coalesce(Sum('activities__dana'), Decimal('0.00'))
    ).order_by('first_name', 'username')

    context = {
        'dosen_stats': dosen_stats
    }
    return render(request, 'monitoring/dosen_statistics.html', context)

@login_required
def dosen_detail_statistics(request, dosen_id):
    user = request.user
    if user.role not in ['kaprodi', 'dekan', 'admin']:
        messages.error(request, "Anda tidak memiliki akses ke halaman ini.")
        return redirect('dashboard')

    dosen = get_object_or_404(User, id=dosen_id, role='dosen')

    # Security check: Does Kaprodi/Dekan have authority over this Dosen?
    if user.role == 'kaprodi' and dosen.prodi != user.prodi:
        messages.error(request, "Dosen ini tidak berada di bawah program studi Anda.")
        return redirect('statistik')
    elif user.role == 'dekan' and dosen.fakultas != user.fakultas:
        messages.error(request, "Dosen ini tidak berada di bawah fakultas Anda.")
        return redirect('statistik')

    # Get all activities for this dosen
    activities = Activity.objects.filter(dosen=dosen).order_by('-updated_at')

    # Calculate summary metrics for the header
    total_usulan = activities.count()
    approved_activities = activities.filter(status='approved')
    total_penelitian = activities.filter(category='penelitian').count()
    total_pengabdian = activities.filter(category='pengabdian').count()
    serapan_dana = approved_activities.aggregate(total=Sum('dana'))['total'] or 0

    context = {
        'dosen': dosen,
        'activities': activities,
        'total_usulan': total_usulan,
        'total_penelitian': total_penelitian,
        'total_pengabdian': total_pengabdian,
        'serapan_dana': serapan_dana,
    }
    return render(request, 'monitoring/dosen_detail_statistics.html', context)

# ─── PROFILE ──────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'monitoring/profile.html', {'form': form})

# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('dashboard')

@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Semua notifikasi telah ditandai sebagai dibaca.")
    return redirect('dashboard')

@login_required
def notification_list(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(notifs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'monitoring/notification_list.html', {'page_obj': page_obj})

# ─── ADMIN FEATURES ───────────────────────────────────────────────────────────

@user_passes_test(is_admin)
def export_activities_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="data_kegiatan_litabdimas.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Judul', 'Dosen', 'Kategori', 'Dana (Rp)', 'Status', 'Tgl Dibuat', 'Tgl Update'])

    activities = Activity.objects.all().order_by('-created_at')
    for act in activities:
        writer.writerow([
            act.id, act.title, act.dosen.get_full_name() or act.dosen.username,
            act.get_category_display(), act.dana, act.get_status_display(),
            act.created_at.strftime('%Y-%m-%d %H:%M'), act.updated_at.strftime('%Y-%m-%d %H:%M')
        ])
    return response

@user_passes_test(is_admin)
def user_list(request):
    role_filter = request.GET.get('role', '')
    users = User.objects.all().order_by('username')
    
    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'role_filter': role_filter,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'monitoring/user_list.html', context)

@user_passes_test(is_admin)
def user_create(request):
    if request.method == 'POST':
        form = UserAdminCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Pengguna baru berhasil ditambahkan.")
            return redirect('user_list')
    else:
        form = UserAdminCreationForm()
    return render(request, 'monitoring/user_form.html', {'form': form, 'title': 'Tambah Pengguna Baru'})

@user_passes_test(is_admin)
def user_edit(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserAdminChangeForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Data pengguna {target_user.username} berhasil diperbarui.")
            return redirect('user_list')
    else:
        form = UserAdminChangeForm(instance=target_user)
    return render(request, 'monitoring/user_form.html', {'form': form, 'title': f'Edit Pengguna: {target_user.username}'})
