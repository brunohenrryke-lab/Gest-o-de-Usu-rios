import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from extensions import db, login_manager, mail, bcrypt, csrf
from config import Config
from models import User, PasswordReset
from forms import (LoginForm, RegistrationForm, ForgotPasswordForm,
                   ResetPasswordForm, ChangePasswordForm,
                   AdminChangePasswordForm)
from utils import send_reset_code, generate_reset_code

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    mail.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        db.create_all()
        # Create first admin user if none exists
        if User.query.filter_by(is_admin=True).count() == 0:
            admin_email = app.config.get('ADMIN_EMAIL')
            admin_password = app.config.get('ADMIN_PASSWORD')
            if admin_email and admin_password:
                admin = User(
                    username='admin',
                    email=admin_email,
                    password_hash=bcrypt.generate_password_hash(admin_password).decode('utf-8'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                app.logger.info('Admin user created.')

    # Routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=hashed_password,
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created. You can now log in.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        form = ForgotPasswordForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                code = generate_reset_code()
                # NÃO passar expires_at; o default do modelo será usado (5 minutos)
                reset = PasswordReset(email=form.email.data, code=code)
                db.session.add(reset)
                db.session.commit()
                send_reset_code(form.email.data, code)
                flash('A verification code has been sent to your email.', 'info')
                return redirect(url_for('reset_password', email=form.email.data))
            else:
                flash('No account with that email exists.', 'danger')
        return render_template('forgot_password.html', form=form)

    @app.route('/reset-password/<email>', methods=['GET', 'POST'])
    def reset_password(email):
        form = ResetPasswordForm()
        if form.validate_on_submit():
            reset = PasswordReset.query.filter_by(email=email, code=form.code.data).first()
            if reset and reset.expires_at > datetime.utcnow():
                user = User.query.filter_by(email=email).first()
                if user:
                    user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
                    db.session.delete(reset)
                    db.session.commit()
                    flash('Your password has been updated. Please log in.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('User not found.', 'danger')
            else:
                flash('Invalid or expired code.', 'danger')
        return render_template('reset_password.html', form=form, email=email)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        form = ChangePasswordForm()
        if form.validate_on_submit():
            if bcrypt.check_password_hash(current_user.password_hash, form.current_password.data):
                current_user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
                db.session.commit()
                flash('Your password has been updated.', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Current password is incorrect.', 'danger')
        return render_template('profile.html', user=current_user, form=form)

    @app.route('/admin/users')
    @login_required
    def user_list():
        if not current_user.is_admin:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard'))

        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')

        query = User.query
        if search:
            query = query.filter(
                (User.username.ilike(f'%{search}%')) |
                (User.email.ilike(f'%{search}%'))
            )
        pagination = query.order_by(User.id).paginate(page=page, per_page=10, error_out=False)
        users = pagination.items

        return render_template('user_list.html', users=users, pagination=pagination, search=search)

    @app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if not current_user.is_admin:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard'))

        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('You cannot delete yourself.', 'danger')
            return redirect(url_for('user_list'))

        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
        return redirect(url_for('user_list'))

    @app.route('/admin/user/<int:user_id>/change-password', methods=['POST'])
    @login_required
    def admin_change_password(user_id):
        if not current_user.is_admin:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard'))

        user = User.query.get_or_404(user_id)
        form = AdminChangePasswordForm()
        if form.validate_on_submit():
            user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            db.session.commit()
            flash(f'Password for {user.username} has been changed.', 'success')
        else:
            flash('Invalid password.', 'danger')
        return redirect(url_for('user_list'))

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)