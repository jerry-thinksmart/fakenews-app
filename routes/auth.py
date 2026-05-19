import re
import secrets
from datetime import datetime, timedelta

import bleach
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Regexp, ValidationError
)

from extensions import db, mail
from models.user import User
from models.log import SystemLog

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RATE_LIMIT_MAX = 5
_RATE_LIMIT_MINUTES = 15


def _log(action: str, level: str = 'INFO', user_id=None):
    entry = SystemLog(
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        level=level,
    )
    db.session.add(entry)
    db.session.commit()


def _is_rate_limited() -> bool:
    failures = session.get('login_failures', 0)
    blocked_until = session.get('login_blocked_until')
    if blocked_until:
        blocked_until_dt = datetime.fromisoformat(blocked_until)
        if datetime.utcnow() < blocked_until_dt:
            return True
        # Block expired – reset
        session.pop('login_failures', None)
        session.pop('login_blocked_until', None)
    return False


def _record_failure():
    failures = session.get('login_failures', 0) + 1
    session['login_failures'] = failures
    if failures >= _RATE_LIMIT_MAX:
        session['login_blocked_until'] = (
            datetime.utcnow() + timedelta(minutes=_RATE_LIMIT_MINUTES)
        ).isoformat()


def _reset_failures():
    session.pop('login_failures', None)
    session.pop('login_blocked_until', None)


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class RegisterForm(FlaskForm):
    full_name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=3, max=150)],
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
    )
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=20),
            Regexp(
                r'^[A-Za-z0-9_]+$',
                message='Username may only contain letters, numbers, and underscores.',
            ),
        ],
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')],
    )
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError('That email is already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError('That username is already taken.')

    def validate_password(self, field):
        pwd = field.data
        if not re.search(r'[A-Z]', pwd):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', pwd):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', pwd):
            raise ValidationError('Password must contain at least one digit.')
        if not re.search(r'[^A-Za-z0-9]', pwd):
            raise ValidationError('Password must contain at least one special character.')


class LoginForm(FlaskForm):
    identifier = StringField(
        'Email or Username',
        validators=[DataRequired(), Length(max=150)],
    )
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        'New Password',
        validators=[DataRequired(), Length(min=8)],
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')],
    )
    submit = SubmitField('Reset Password')

    def validate_password(self, field):
        pwd = field.data
        if not re.search(r'[A-Z]', pwd):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', pwd):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', pwd):
            raise ValidationError('Password must contain at least one digit.')
        if not re.search(r'[^A-Za-z0-9]', pwd):
            raise ValidationError('Password must contain at least one special character.')


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        full_name = bleach.clean(form.full_name.data.strip())
        email = bleach.clean(form.email.data.strip().lower())
        username = bleach.clean(form.username.data.strip())

        user = User(
            full_name=full_name,
            email=email,
            username=username,
            role='user',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        _log(f'New user registered: {username}', level='INFO', user_id=user.id)
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('public/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()

    if _is_rate_limited():
        blocked_until = session.get('login_blocked_until')
        blocked_until_dt = datetime.fromisoformat(blocked_until)
        wait_mins = max(1, int((blocked_until_dt - datetime.utcnow()).total_seconds() // 60) + 1)
        flash(
            f'Too many failed attempts. Please try again in {wait_mins} minute(s).',
            'danger',
        )
        return render_template('public/login.html', form=form)

    if form.validate_on_submit():
        identifier = bleach.clean(form.identifier.data.strip())
        user = (
            User.query.filter_by(email=identifier).first()
            or User.query.filter_by(username=identifier).first()
        )

        if user and user.is_active and user.check_password(form.password.data):
            _reset_failures()
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            _log(f'User logged in: {user.username}', level='INFO', user_id=user.id)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))

        # Failed attempt
        _record_failure()
        _log(
            f'Failed login attempt for identifier: {identifier}',
            level='WARNING',
        )
        failures = session.get('login_failures', 0)
        remaining = max(0, _RATE_LIMIT_MAX - failures)
        flash(
            f'Invalid credentials. {remaining} attempt(s) remaining before lockout.',
            'danger',
        )

    return render_template('public/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    username = current_user.username
    logout_user()
    session.clear()
    _log(f'User logged out: {username}', level='INFO', user_id=user_id)
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.home'))


# ---------------------------------------------------------------------------
# Forgot / Reset Password
# ---------------------------------------------------------------------------

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = bleach.clean(form.email.data.strip().lower())
        user = User.query.filter_by(email=email).first()

        # Always show the same message to prevent email enumeration
        if user and user.is_active:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            try:
                msg = Message(
                    subject='Reset Your FakeNews Detector Password',
                    recipients=[user.email],
                )
                msg.html = f"""
                <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:32px;border-radius:8px;border:1px solid #e0e0e0;">
                  <h2 style="color:#274665;margin-bottom:8px;">Password Reset Request</h2>
                  <p style="color:#555;">Hi <strong>{user.full_name}</strong>,</p>
                  <p style="color:#555;">We received a request to reset the password for your account. Click the button below to choose a new password.</p>
                  <div style="text-align:center;margin:28px 0;">
                    <a href="{reset_url}" style="background:#F08030;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">
                      Reset My Password
                    </a>
                  </div>
                  <p style="color:#888;font-size:13px;">This link will expire in <strong>1 hour</strong>. If you didn't request a password reset, you can safely ignore this email.</p>
                  <hr style="border:none;border-top:1px solid #eee;margin:24px 0;" />
                  <p style="color:#aaa;font-size:12px;text-align:center;">FakeNews Detector &copy; 2026</p>
                </div>
                """
                mail.send(msg)
                _log(f'Password reset email sent to: {user.email}', level='INFO', user_id=user.id)
            except Exception:
                _log(f'Failed to send password reset email to: {user.email}', level='WARNING', user_id=user.id)

        flash('If that email is registered, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('public/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Log out any currently logged-in user so the reset flow can proceed
    if current_user.is_authenticated:
        logout_user()
        session.clear()

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash('This password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        _log('Password reset via email link', level='INFO', user_id=user.id)
        flash('Your password has been reset. You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('public/reset_password.html', form=form, token=token)
