import os
import uuid
from datetime import datetime, timedelta

import bleach
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, make_response, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename

from extensions import db
from models.user import User
from models.detection import DetectionHistory
from models.article import NewsRecord
from models.log import SystemLog
from services.predictor import predict_news
from services.report_generator import generate_csv, generate_pdf
from config import Config

dashboard_bp = Blueprint('dashboard', __name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _log(action: str, level: str = 'INFO'):
    entry = SystemLog(
        user_id=current_user.id,
        action=action,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        level=level,
    )
    db.session.add(entry)
    db.session.commit()


def _global_stats():
    return {
        'total_detections': DetectionHistory.query.count(),
        'fake_count': DetectionHistory.query.filter_by(prediction='Fake').count(),
        'real_count': DetectionHistory.query.filter_by(prediction='Real').count(),
        'user_count': User.query.count(),
    }


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

@dashboard_bp.route('/')
@login_required
def index():
    stats = _global_stats()
    page = request.args.get('page', 1, type=int)

    # Deduplicate: keep only the latest record per unique (article_snippet, prediction)
    subq = (
        db.session.query(func.max(DetectionHistory.id).label('id'))
        .filter(DetectionHistory.user_id == current_user.id)
        .group_by(DetectionHistory.article_snippet, DetectionHistory.prediction)
        .subquery()
    )
    recent_detections = (
        DetectionHistory.query
        .filter(DetectionHistory.id.in_(subq))
        .order_by(DetectionHistory.detected_at.desc())
        .paginate(page=page, per_page=5, error_out=False)
    )

    # Last 7 days daily counts for current user
    weekly_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = (
            DetectionHistory.query
            .filter(
                DetectionHistory.user_id == current_user.id,
                DetectionHistory.detected_at >= day_start,
                DetectionHistory.detected_at <= day_end,
            )
            .count()
        )
        weekly_data.append({'date': day.strftime('%a'), 'count': count})

    return render_template(
        'dashboard/index.html',
        stats=stats,
        recent_detections=recent_detections,
        weekly_data=weekly_data,
    )


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------

@dashboard_bp.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    if request.method == 'POST':
        try:
            raw_text = request.form.get('article_text', '')
            article_text = bleach.clean(raw_text.strip())

            result = predict_news(article_text)
            prediction = result.get('prediction', 'Error')
            snippet = article_text[:300] if article_text else ''

            # Only persist meaningful predictions — never store Error or Invalid
            if prediction in ('Fake', 'Real', 'Uncertain'):
                # Deduplication guard — skip if same article saved in last 10 seconds
                # (regardless of prediction type, to avoid Error/Fake duplicates)
                cutoff = datetime.utcnow() - timedelta(seconds=10)
                duplicate = DetectionHistory.query.filter(
                    DetectionHistory.user_id == current_user.id,
                    DetectionHistory.article_snippet == snippet,
                    DetectionHistory.detected_at >= cutoff,
                ).first()

                if not duplicate:
                    detection = DetectionHistory(
                        user_id=current_user.id,
                        article_snippet=snippet,
                        full_article=article_text,
                        prediction=prediction,
                        confidence=result.get('confidence', 0.0),
                        message=result.get('message', ''),
                    )
                    db.session.add(detection)
            else:
                duplicate = False  # allow _log to still fire

            # Also save as a news record when we have a meaningful prediction
            if prediction in ('Fake', 'Real') and not duplicate:
                title = (article_text[:77] + '...') if len(article_text) > 80 else article_text
                record = NewsRecord(
                    title=title,
                    content=article_text,
                    prediction=prediction,
                    confidence=result.get('confidence', 0.0),
                    user_id=current_user.id,
                )
                db.session.add(record)

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

            try:
                _log(
                    f'Detection performed: {prediction} '
                    f'(confidence={result.get("confidence", 0.0):.2%})'
                )
            except Exception:
                pass

            return jsonify({
                'prediction': prediction,
                'confidence': result.get('confidence'),
                'message': result.get('message'),
            })

        except Exception as exc:
            db.session.rollback()
            return jsonify({
                'prediction': 'Error',
                'confidence': 0.0,
                'message': f'Server error: {str(exc)}',
            }), 500

    return render_template('dashboard/detect.html')


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@dashboard_bp.route('/history')
@login_required
def history():
    search = request.args.get('search', '').strip()
    filter_val = request.args.get('filter', '').strip()
    page = request.args.get('page', 1, type=int)

    query = DetectionHistory.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            DetectionHistory.article_snippet.ilike(f'%{search}%')
        )
    if filter_val:
        query = query.filter_by(prediction=filter_val)

    detections = (
        query.order_by(DetectionHistory.detected_at.desc())
        .paginate(page=page, per_page=5, error_out=False)
    )

    return render_template(
        'dashboard/history.html',
        detections=detections,
        search=search,
        filter_val=filter_val,
    )


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

@dashboard_bp.route('/records')
@login_required
def records():
    search = request.args.get('search', '').strip()
    filter_val = request.args.get('filter', '').strip()
    page = request.args.get('page', 1, type=int)

    query = NewsRecord.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            (NewsRecord.title.ilike(f'%{search}%')) |
            (NewsRecord.content.ilike(f'%{search}%'))
        )
    if filter_val:
        query = query.filter_by(prediction=filter_val)

    records_data = (
        query.order_by(NewsRecord.created_at.desc())
        .paginate(page=page, per_page=12, error_out=False)
    )

    return render_template(
        'dashboard/records.html',
        records=records_data,
        search=search,
        filter_val=filter_val,
    )


# ---------------------------------------------------------------------------
# Analytics page + API
# ---------------------------------------------------------------------------

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    return render_template('dashboard/analytics.html')


@dashboard_bp.route('/api/analytics')
@login_required
def api_analytics():
    user_detections = DetectionHistory.query.filter_by(user_id=current_user.id)

    total = user_detections.count()
    fake_count = user_detections.filter_by(prediction='Fake').count()
    real_count = user_detections.filter_by(prediction='Real').count()
    uncertain_count = user_detections.filter(
        DetectionHistory.prediction.in_(['Uncertain', 'Invalid', 'Error'])
    ).count()

    # Last 30 days – daily breakdown
    daily_counts = []
    for i in range(29, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        base = DetectionHistory.query.filter(
            DetectionHistory.user_id == current_user.id,
            DetectionHistory.detected_at >= day_start,
            DetectionHistory.detected_at <= day_end,
        )
        daily_counts.append({
            'date': day.strftime('%Y-%m-%d'),
            'count': base.count(),
            'fake': base.filter_by(prediction='Fake').count(),
            'real': base.filter_by(prediction='Real').count(),
        })

    # Last 7 days weekly
    weekly_counts = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        count = DetectionHistory.query.filter(
            DetectionHistory.user_id == current_user.id,
            DetectionHistory.detected_at >= day_start,
            DetectionHistory.detected_at <= day_end,
        ).count()
        weekly_counts.append({'date': day.strftime('%a'), 'count': count})

    # Confidence ranges
    high = user_detections.filter(DetectionHistory.confidence >= 0.85).count()
    medium = user_detections.filter(
        DetectionHistory.confidence >= 0.60,
        DetectionHistory.confidence < 0.85,
    ).count()
    low = user_detections.filter(
        DetectionHistory.confidence < 0.60
    ).count()

    return jsonify({
        'total': total,
        'fake_count': fake_count,
        'real_count': real_count,
        'uncertain_count': uncertain_count,
        'daily_counts': daily_counts,
        'weekly_counts': weekly_counts,
        'confidence_ranges': {'high': high, 'medium': medium, 'low': low},
    })


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@dashboard_bp.route('/reports')
@login_required
def reports():
    return render_template('dashboard/reports.html')


@dashboard_bp.route('/export/csv', methods=['POST'])
@login_required
def export_csv():
    date_range = request.form.get('date_range', '')
    export_type = request.form.get('type', 'detection')

    query = DetectionHistory.query.filter_by(user_id=current_user.id)
    query = _apply_date_filter(query, date_range, DetectionHistory.detected_at)
    records_data = query.order_by(DetectionHistory.detected_at.desc()).all()

    csv_content = generate_csv(records_data)
    _log(f'CSV export: {len(records_data)} records')

    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=detections_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    )
    return response


@dashboard_bp.route('/export/pdf', methods=['POST'])
@login_required
def export_pdf():
    date_range = request.form.get('date_range', '')

    query = DetectionHistory.query.filter_by(user_id=current_user.id)
    query = _apply_date_filter(query, date_range, DetectionHistory.detected_at)
    records_data = query.order_by(DetectionHistory.detected_at.desc()).all()

    pdf_bytes = generate_pdf(
        records_data,
        title='Fake News Detection Report',
        date_range=date_range or 'All Time',
    )
    _log(f'PDF export: {len(records_data)} records')

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=report_{datetime.utcnow().strftime("%Y%m%d")}.pdf'
    )
    return response


def _apply_date_filter(query, date_range: str, date_column):
    """Apply a simple date-range filter. Expects 'YYYY-MM-DD to YYYY-MM-DD'."""
    if date_range and ' to ' in date_range:
        try:
            parts = date_range.split(' to ')
            start = datetime.strptime(parts[0].strip(), '%Y-%m-%d')
            end = datetime.strptime(parts[1].strip(), '%Y-%m-%d').replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(date_column >= start, date_column <= end)
        except ValueError:
            pass
    return query


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------

@dashboard_bp.route('/model')
@login_required
def model_management():
    last_modified = None
    try:
        mtime = os.path.getmtime(Config.MODEL_PATH)
        last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    except OSError:
        last_modified = 'N/A'

    model_info = {
        'name': 'Logistic Regression Fake News Classifier',
        'file': os.path.basename(Config.MODEL_PATH),
        'accuracy': 98.2,
        'precision': 97.8,
        'recall': 98.6,
        'f1': 98.2,
        'last_modified': last_modified,
    }
    return render_template('dashboard/model_management.html', model_info=model_info)


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@dashboard_bp.route('/logs')
@login_required
def logs():
    level = request.args.get('level', '').strip()
    page = request.args.get('page', 1, type=int)

    query = SystemLog.query
    if level:
        query = query.filter_by(level=level.upper())

    log_entries = (
        query.order_by(SystemLog.timestamp.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template('dashboard/logs.html', log_entries=log_entries, level=level)


# ---------------------------------------------------------------------------
# Delete record
# ---------------------------------------------------------------------------

@dashboard_bp.route('/records/<int:record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    record = NewsRecord.query.filter_by(
        id=record_id, user_id=current_user.id
    ).first_or_404()

    db.session.delete(record)
    db.session.commit()
    _log(f'Deleted NewsRecord id={record_id}', level='WARNING')

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dashboard_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'profile':
            full_name = bleach.clean(request.form.get('full_name', '').strip())
            username = bleach.clean(request.form.get('username', '').strip())

            if not full_name or not username:
                flash('Full name and username are required.', 'danger')
                return redirect(url_for('dashboard.settings'))

            # Check username uniqueness (exclude self)
            existing = User.query.filter(
                User.username == username,
                User.id != current_user.id
            ).first()
            if existing:
                flash('Username is already taken.', 'danger')
                return redirect(url_for('dashboard.settings'))

            current_user.full_name = full_name
            current_user.username = username

            # Handle profile photo upload
            photo = request.files.get('profile_photo')
            if photo and photo.filename:
                allowed_ext = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                ext = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else ''
                if ext not in allowed_ext:
                    flash('Invalid file type. Only PNG, JPG, GIF, and WEBP are allowed.', 'danger')
                    return redirect(url_for('dashboard.settings'))
                upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'profile_photos')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                photo.save(os.path.join(upload_dir, filename))
                # Remove old photo if different
                if current_user.profile_photo and current_user.profile_photo != filename:
                    old_path = os.path.join(upload_dir, current_user.profile_photo)
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                current_user.profile_photo = filename

            db.session.commit()
            _log('Updated profile settings')
            flash('Profile updated successfully.', 'success')

        elif action == 'password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('dashboard.settings'))

            if len(new_pw) < 8:
                flash('New password must be at least 8 characters.', 'danger')
                return redirect(url_for('dashboard.settings'))

            if new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('dashboard.settings'))

            current_user.set_password(new_pw)
            db.session.commit()
            _log('Changed password')
            flash('Password changed successfully.', 'success')

        return redirect(url_for('dashboard.settings'))

    return render_template('dashboard/settings.html')


# ---------------------------------------------------------------------------
# Subscribers
# ---------------------------------------------------------------------------

@dashboard_bp.route('/subscribers', methods=['GET', 'POST'])
@login_required
def subscribers():
    from models.subscriber import Subscriber
    from flask_mail import Message
    from extensions import mail

    # Bulk email action
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'send_email':
            subject = bleach.clean(request.form.get('subject', '').strip())
            body = bleach.clean(request.form.get('body', '').strip(), tags=['p', 'b', 'i', 'br', 'ul', 'li', 'strong', 'em', 'a'], attributes={'a': ['href']})
            selected = request.form.getlist('subscriber_ids')

            if not subject or not body:
                flash('Subject and message body are required.', 'danger')
                return redirect(url_for('dashboard.subscribers'))

            if not selected:
                flash('Please select at least one subscriber.', 'danger')
                return redirect(url_for('dashboard.subscribers'))

            recipients = []
            for sid in selected:
                sub = Subscriber.query.get(int(sid))
                if sub and sub.is_active:
                    recipients.append(sub.email)

            sent = 0
            failed = 0
            for email_addr in recipients:
                try:
                    msg = Message(subject=subject, recipients=[email_addr])
                    msg.html = f"""
                    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;border-radius:8px;border:1px solid #e0e0e0;">
                      {body}
                      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;" />
                      <p style="color:#aaa;font-size:12px;text-align:center;">FakeNews Detector &copy; 2026</p>
                    </div>
                    """
                    mail.send(msg)
                    sent += 1
                except Exception:
                    failed += 1

            _log(f'Bulk email sent to {sent} subscriber(s), {failed} failed')
            flash(f'Email sent to {sent} subscriber(s).{" " + str(failed) + " failed." if failed else ""}', 'success' if sent else 'danger')
            return redirect(url_for('dashboard.subscribers'))

        elif action == 'delete':
            selected = request.form.getlist('subscriber_ids')
            if selected:
                Subscriber.query.filter(Subscriber.id.in_([int(i) for i in selected])).delete(synchronize_session=False)
                db.session.commit()
                _log(f'Deleted {len(selected)} subscriber(s)')
                flash(f'{len(selected)} subscriber(s) removed.', 'success')
            return redirect(url_for('dashboard.subscribers'))

        elif action == 'send_sms':
            sms_body = bleach.clean(request.form.get('sms_body', '').strip(), tags=[], strip=True)
            selected = request.form.getlist('subscriber_ids')

            if not sms_body:
                flash('SMS message body is required.', 'danger')
                return redirect(url_for('dashboard.subscribers'))

            if not selected:
                flash('Please select at least one subscriber.', 'danger')
                return redirect(url_for('dashboard.subscribers'))

            account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
            auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
            from_number = current_app.config.get('TWILIO_FROM_NUMBER')

            if not account_sid or not auth_token or not from_number:
                flash('Twilio credentials are not configured. Update your .env file.', 'danger')
                return redirect(url_for('dashboard.subscribers'))

            from twilio.rest import Client as TwilioClient
            from twilio.base.exceptions import TwilioRestException

            client = TwilioClient(account_sid, auth_token)
            sent = 0
            failed = 0
            no_phone = 0

            for sid in selected:
                sub = Subscriber.query.get(int(sid))
                if not sub or not sub.is_active:
                    continue
                if not sub.phone:
                    no_phone += 1
                    continue
                try:
                    client.messages.create(
                        body=sms_body,
                        from_=from_number,
                        to=sub.phone
                    )
                    sent += 1
                except TwilioRestException:
                    failed += 1

            parts = [f'SMS sent to {sent} subscriber(s).']
            if failed:
                parts.append(f'{failed} failed.')
            if no_phone:
                parts.append(f'{no_phone} skipped (no phone number).')
            _log(f'Bulk SMS: sent={sent}, failed={failed}, no_phone={no_phone}')
            flash(' '.join(parts), 'success' if sent else 'danger')
            return redirect(url_for('dashboard.subscribers'))

    q = request.args.get('q', '').strip()
    query = Subscriber.query
    if q:
        query = query.filter(Subscriber.email.ilike(f'%{q}%'))
    all_subscribers = query.order_by(Subscriber.subscribed_at.desc()).all()
    return render_template('dashboard/subscribers.html', subscribers=all_subscribers, q=q)
