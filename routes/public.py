from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user

from extensions import db
from models.user import User
from models.detection import DetectionHistory
from models.subscriber import Subscriber

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def home():
    stats = {
        "total_detections": 10,
        "fake_count": 5,
        "real_count": 5,
        "user_count": 3
    }
    return render_template('public/home.html', stats=stats)

@public_bp.route('/about')
def about():
    return render_template('public/about.html')


@public_bp.route('/detect-redirect')
def detect_redirect():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.detect'))
    flash('Please login to detect fake news.', 'warning')
    return redirect(url_for('auth.login'))


@public_bp.route('/subscribe', methods=['POST'])
def subscribe():
    import bleach
    email = bleach.clean(request.form.get('email', '').strip().lower())
    phone = bleach.clean(request.form.get('phone', '').strip())
    # Basic phone sanitisation: keep only +, digits, spaces, dashes
    import re
    phone = re.sub(r'[^\d\+\-\s]', '', phone)[:20] or None
    if not email:
        flash('Please enter a valid email address.', 'danger')
        return redirect(request.referrer or url_for('public.home'))
    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            if phone and not existing.phone:
                existing.phone = phone
            db.session.commit()
            flash('Welcome back! You have been re-subscribed.', 'success')
        else:
            if phone and not existing.phone:
                existing.phone = phone
                db.session.commit()
            flash('You are already subscribed!', 'info')
    else:
        db.session.add(Subscriber(email=email, phone=phone))
        db.session.commit()
        flash('Thank you for subscribing!', 'success')
    return redirect(request.referrer or url_for('public.home'))
