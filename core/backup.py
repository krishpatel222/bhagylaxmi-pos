import os
import shutil
import sqlite3
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages

from accounts.decorators import admin_required


def get_backup_dir():
    backup_dir = settings.BASE_DIR / 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


@admin_required
def backup_dashboard(request):
    """
    Admin-only Backup Management view.
    Lists existing backups and allows creating a new timestamped backup.
    """
    backup_dir = get_backup_dir()

    if request.method == 'POST' and 'create_backup' in request.POST:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f"backup_{timestamp}.sqlite3"
        backup_path = backup_dir / backup_filename
        db_path = settings.DATABASES['default']['NAME']

        try:
            # Use SQLite online backup API for safe live backup
            src_conn = sqlite3.connect(db_path)
            dst_conn = sqlite3.connect(backup_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            messages.success(request, f"Database backup '{backup_filename}' created successfully!")
        except Exception as e:
            # Fallback to file copy if online backup fails
            try:
                shutil.copy2(db_path, backup_path)
                messages.success(request, f"Database backup '{backup_filename}' created successfully!")
            except Exception as copy_err:
                messages.error(request, f"Failed to create backup: {str(copy_err)}")

        return redirect('backup_dashboard')

    # List backups
    backups = []
    if os.path.exists(backup_dir):
        for fname in sorted(os.listdir(backup_dir), reverse=True):
            if fname.endswith('.sqlite3'):
                fpath = backup_dir / fname
                stat = os.stat(fpath)
                backups.append({
                    'filename': fname,
                    'size_bytes': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime),
                })

    return render(request, 'core/backup_dashboard.html', {'backups': backups})


@admin_required
def backup_download(request, filename):
    """
    Admin-only secure backup file download endpoint.
    Strictly verifies filename to prevent directory traversal attack.
    """
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or not filename.endswith('.sqlite3'):
        raise Http404("Invalid backup filename.")

    backup_dir = get_backup_dir()
    file_path = backup_dir / safe_filename

    if not os.path.exists(file_path):
        raise Http404("Backup file not found.")

    response = HttpResponse(open(file_path, 'rb'), content_type='application/x-sqlite3')
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    return response
