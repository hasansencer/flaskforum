from flask import render_template, url_for, flash, redirect, request, Blueprint, current_app, abort
from app import db, bcrypt, mail
from app.forms import RegistrationForm, LoginForm, ApprovePostForm, RequestResetForm, EditUserForm, AddModeratorForm, ResetPasswordForm, DeleteModeratorForm, UpdateAccountForm, BanUserForm, PostForm, CommentForm, LikeForm, DislikeForm, SearchForm, ModeratorForm, DeleteForm
from app.models import User, Post, Comment, Like, Dislike
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from config import Config
import os
from flask_paginate import Pagination, get_page_parameter

import secrets
from PIL import Image
from sqlalchemy import func

main = Blueprint('main', __name__)

@main.app_errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@main.app_errorhandler(500)
def internal_error(error):
    db.session.rollback() 
    return render_template('500.html'), 500

@main.route("/", methods=['GET', 'POST'])
@main.route("/home", methods=['GET', 'POST'])
def home():
    sort_by = request.args.get('sort_by', 'newest')
    comment_form = CommentForm()
    like_form = LikeForm()
    dislike_form = DislikeForm()
    search_form = SearchForm()
    delete_form = DeleteForm()

    if search_form.validate_on_submit():
        search_query = search_form.search_query.data
        if search_query.startswith('@'):
            search_user = search_query[1:]
            posts = Post.query.join(User).filter(User.username.ilike(f"%{search_user}%"), Post.is_approved == True).all()
        elif search_query.startswith('#'):
            title = search_query[1:]
            posts = Post.query.filter(Post.title.ilike(f'%{title}%'), Post.is_approved == True).all()
        else:
            posts = Post.query.filter(Post.content.ilike(f"%{search_query}%"), Post.is_approved == True).all()
        return render_template('home.html', posts=posts, comment_form=comment_form, like_form=like_form, dislike_form=dislike_form, search_form=search_form, delete_form=delete_form, sort_by=sort_by)

    if sort_by == 'most_liked':
        posts = sorted(Post.query.filter_by(is_approved=True).all(), key=lambda p: p.net_likes, reverse=True)
    elif sort_by == 'least_liked':
        posts = sorted(Post.query.filter_by(is_approved=True).all(), key=lambda p: p.net_likes)
    elif sort_by == 'newest':
        posts = Post.query.filter_by(is_approved=True).order_by(Post.date_posted.desc()).all()
    elif sort_by == 'oldest':
        posts = Post.query.filter_by(is_approved=True).order_by(Post.date_posted.asc()).all()
    else:
        posts = Post.query.filter_by(is_approved=True).order_by(Post.date_posted.desc()).all()

    if comment_form.validate_on_submit() and 'comment_submit' in request.form:
        post_id = request.form.get('post_id')
        post = Post.query.get_or_404(post_id)
        comment = Comment(content=comment_form.content.data, comment_author=current_user, post=post)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
        return redirect(url_for('main.home'))

    return render_template('home.html', posts=posts, comment_form=comment_form, like_form=like_form, dislike_form=dislike_form, search_form=search_form, delete_form=delete_form, sort_by=sort_by)

def save_post_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/post_pics', picture_fn)

    i = Image.open(form_picture)
    i.save(picture_path)

    return picture_fn

@main.route("/approve_post/<int:post_id>", methods=['POST'])
@login_required
def approve_post(post_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.home'))

    post = Post.query.get_or_404(post_id)
    post.is_approved = True
    db.session.commit()
    flash('Post has been approved!', 'success')
    return redirect(url_for('main.admin'))

@main.route("/moderator_posts", methods=['GET', 'POST'])
@login_required
def moderator_posts():
    form = PostForm()
    like_form = LikeForm()
    dislike_form = DislikeForm()
    search_form = SearchForm()
    delete_form = DeleteForm()
    sort_by = request.args.get('sort_by', 'newest')

    if search_form.validate_on_submit():
        search_query = search_form.search_query.data
        if search_query.startswith('@'):
            search_user = search_query[1:]
            posts = Post.query.filter_by(is_moderator_post=True, is_approved=True).join(User).filter(User.username.ilike(f"%{search_user}%")).all()
        elif search_query.startswith('#'):
            title = search_query[1:]
            posts = Post.query.filter(Post.is_moderator_post == True, Post.is_approved == True, Post.title.ilike(f'%{title}%')).all()
        else:
            posts = Post.query.filter(Post.is_moderator_post == True, Post.is_approved == True, Post.content.ilike(f"%{search_query}%")).all()
    else:
        if sort_by == 'most_liked':
            posts = sorted(Post.query.filter_by(is_moderator_post=True, is_approved=True).all(), key=lambda p: p.net_likes, reverse=True)
        elif sort_by == 'least_liked':
            posts = sorted(Post.query.filter_by(is_moderator_post=True, is_approved=True).all(), key=lambda p: p.net_likes)
        elif sort_by == 'oldest':
            posts = Post.query.filter_by(is_moderator_post=True, is_approved=True).order_by(Post.date_posted.asc()).all()
        else:
            posts = Post.query.filter_by(is_moderator_post=True, is_approved=True).order_by(Post.date_posted.desc()).all()

    if current_user.is_moderator or current_user.is_admin:
        if form.validate_on_submit():
            if form.image.data:
                image_file = save_post_picture(form.image.data)
                post = Post(title=form.title.data, content=form.content.data, author=current_user, is_moderator_post=True, is_approved=False, image_file=image_file)
            else:
                post = Post(title=form.title.data, content=form.content.data, author=current_user, is_moderator_post=True, is_approved=False)
            db.session.add(post)
            db.session.commit()
            flash('Your post has been created and is awaiting approval!', 'success')
            return redirect(url_for('main.moderator_posts'))

    return render_template('moderator_posts.html', title='Moderator Posts', form=form, posts=posts, like_form=like_form, dislike_form=dislike_form, search_form=search_form, delete_form=delete_form, sort_by=sort_by, can_post=current_user.is_moderator or current_user.is_admin)


@main.route("/admin", methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    ban_form = BanUserForm()
    add_mod_form = AddModeratorForm()
    delete_mod_form = DeleteModeratorForm()
    approve_post_form = ApprovePostForm()
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    users = User.query.paginate(page=page, per_page=5)
    moderators = User.query.filter_by(is_moderator=True).all()
    pending_posts = Post.query.filter_by(is_approved=False).all()

    pagination = Pagination(page=page, total=users.total, search=False, record_name='users', per_page=5)

    if add_mod_form.validate_on_submit():
        user = User.query.filter_by(username=add_mod_form.username.data).first()
        if user:
            user.is_moderator = True
            db.session.commit()
            flash(f'{user.username} is now a moderator!', 'success')
        else:
            flash('User not found.', 'danger')
        return redirect(url_for('main.admin'))

    return render_template('admin.html', title='Admin Panel', ban_form=ban_form, add_mod_form=add_mod_form, delete_mod_form=delete_mod_form, approve_post_form=approve_post_form, users=users, moderators=moderators, pending_posts=pending_posts, pagination=pagination)


@main.route("/admin/moderators", methods=['GET', 'POST'])
@login_required
def admin_moderators():
    if not current_user.is_admin:
        flash('Bu sayfaya erişim izniniz yok.', 'danger')
        return redirect(url_for('main.home'))
    
    add_mod_form = AddModeratorForm()
    delete_mod_form = DeleteModeratorForm()
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    moderators = User.query.filter_by(is_moderator=True).paginate(page=page, per_page=5)

    if add_mod_form.validate_on_submit():
        user = User.query.filter_by(username=add_mod_form.username.data).first()
        if user:
            user.is_moderator = True
            db.session.commit()
            flash(f'{user.username} moderatör olarak atandı!', 'success')
        else:
            flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('main.admin_moderators'))

    return render_template('admin_moderators.html', title='Admin - Moderators', add_mod_form=add_mod_form, delete_mod_form=delete_mod_form, moderators=moderators)



@main.route("/admin/users", methods=['GET', 'POST'])
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.home'))

    page_user = request.args.get('page_user', type=int, default=1)
    users = User.query.filter_by(is_moderator=False).paginate(page=page_user, per_page=5)

    return render_template('admin_users.html', title='Admin - Users', users=users)



@main.route("/edit_user/<int:user_id>", methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    user = User.query.get_or_404(user_id)
    form = EditUserForm(original_username=user.username, original_email=user.email)

    if form.validate_on_submit():
        if form.username.data != user.username:
            user.username = form.username.data
        if form.email.data != user.email:
            user.email = form.email.data
        if form.password.data:
            user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        db.session.commit()
        flash('User has been updated!', 'success')
        return redirect(url_for('main.admin_users'))
    
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
    
    return render_template('edit_user.html', title='Edit User', form=form, user=user)

@main.route("/ban_user", methods=['POST'])
@login_required
def ban_user():
    if not current_user.is_admin:
        flash('Bu sayfaya erişim izniniz yok.', 'danger')
        return redirect(url_for('main.home'))
    
    ban_form = BanUserForm()
    if ban_form.validate_on_submit():
        user = User.query.filter_by(username=ban_form.username.data).first()
        if user:
            posts = Post.query.filter_by(user_id=user.id).all()
            for post in posts:
                db.session.delete(post)
            comments = Comment.query.filter_by(user_id=user.id).all()
            for comment in comments:
                db.session.delete(comment)
            likes = Like.query.filter_by(user_id=user.id).all()
            for like in likes:
                db.session.delete(like)
            dislikes = Dislike.query.filter_by(user_id=user.id).all()
            for dislike in dislikes:
                db.session.delete(dislike)
            db.session.delete(user)
            db.session.commit()
            flash(f'Kullanıcı {user.username} başarıyla banlandı!', 'success')
        else:
            flash('Kullanıcı bulunamadı.', 'danger')
    return redirect(url_for('main.admin'))

@main.route("/remove_moderator", methods=['POST'])
@login_required
def remove_moderator_user():
    if not current_user.is_admin:
        flash('Bu sayfaya erişim izniniz yok.', 'danger')
        return redirect(url_for('main.home'))
    
    delete_mod_form = DeleteModeratorForm()
    if delete_mod_form.validate_on_submit():
        user = User.query.filter_by(username=delete_mod_form.username.data).first()
        if user:
            user.is_moderator = False
            db.session.commit()
            flash(f'{user.username} moderatörlükten çıkarıldı!', 'success')
        else:
            flash('Kullanıcı bulunamadı.', 'danger')
    return redirect(url_for('main.admin_moderators'))


@main.route("/new_post", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        if form.image.data:
            image_file = save_post_picture(form.image.data)
            post = Post(title=form.title.data, content=form.content.data, author=current_user, is_approved=True, image_file=image_file)
        else:
            post = Post(title=form.title.data, content=form.content.data, author=current_user, is_approved=True)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created and is awaiting approval!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_post.html', title='New Post', form=form)

@main.route("/new_moderator_post", methods=['GET', 'POST'])
@login_required
def new_moderator_post():
    form = PostForm()
    if form.validate_on_submit():
        if form.image.data:
            image_file = save_post_picture(form.image.data)
            post = Post(title=form.title.data, content=form.content.data, author=current_user, is_moderator_post=True, is_approved=False, image_file=image_file)
        else:
            post = Post(title=form.title.data, content=form.content.data, author=current_user, is_moderator_post=True, is_approved=False)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created and is awaiting approval!', 'success')
        return redirect(url_for('main.moderator_posts'))
    return render_template('create_post.html', title='New Moderator Post', form=form)

@main.route("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).all()
    return render_template('profile.html', user=user, posts=posts)

@main.route("/post/<int:post_id>/like", methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if like:
        db.session.delete(like)
        flash('You have unliked the post.', 'info')
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        dislike = Dislike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        if dislike:
            db.session.delete(dislike)
        flash('You liked the post!', 'success')
    db.session.commit()
    return redirect(url_for('main.home'))

@main.route("/post/<int:post_id>/dislike", methods=['POST'])
@login_required
def dislike_post(post_id):
    post = Post.query.get_or_404(post_id)
    dislike = Dislike.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if dislike:
        db.session.delete(dislike) 
        flash('You have removed your dislike.', 'info')
    else:
        dislike = Dislike(user_id=current_user.id, post_id=post_id)
        db.session.add(dislike)
        like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        if like:
            db.session.delete(like)
        flash('You disliked the post.', 'danger')
    db.session.commit()
    return redirect(url_for('main.home'))

@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@main.route("/settings", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.age = form.age.data
        current_user.my_past = form.my_past.data
        try:
            db.session.commit()  # Veritabanına kaydet
            flash('Your account has been updated!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating account: {e}', 'danger')
        return redirect(url_for('main.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.age.data = current_user.age
        form.my_past.data = current_user.my_past
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Settings', image_file=image_file, form=form)


@main.route("/search", methods=['POST'])
def search():
    search_query = request.form.get('search_query')
    if search_query.startswith('@'):
        username = search_query[1:]
        user = User.query.filter_by(username=username).first()
        if user:
            posts = Post.query.filter_by(author=user, is_approved=True).all()
        else:
            posts = []
    else:
        posts = Post.query.filter(Post.content.contains(search_query), Post.is_approved == True).all()

    comment_form = CommentForm()
    like_form = LikeForm()
    dislike_form = DislikeForm()
    delete_form = DeleteForm()
    search_form = SearchForm()
    
    return render_template('search_results.html', posts=posts, comment_form=comment_form, like_form=like_form, dislike_form=dislike_form, delete_form=delete_form, search_form=search_form)

@main.route("/make_moderator/<int:user_id>")
@login_required
def make_moderator(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.home'))
    user = User.query.get(user_id)
    if user:
        user.is_moderator = True
        db.session.commit()
        flash(f'{user.username} is now a moderator!', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('main.admin'))

@main.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_moderator and not current_user.is_admin:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('main.home'))
    db.session.delete(post)
    db.session.commit()
    flash('The post has been deleted.', 'success')
    return redirect(url_for('main.home'))

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Şifre Sıfırlama İsteği',
                  sender='sifresifirlaflask@gmail.com',
                  recipients=[user.email])
    msg.body = f'''Şifrenizi sıfırlamak için aşağıdaki bağlantıyı ziyaret edin:
{url_for('main.reset_token', token=token, _external=True)}

Bu isteği siz yapmadıysanız bu e-postayı görmezden gelin ve hiçbir değişiklik yapılmayacaktır.
'''
    try:
        mail.send(msg)
        print(f"Şifre sıfırlama e-postası {user.email} adresine gönderildi.")
    except Exception as e:
        print(f"E-posta gönderilemedi: {user.email}: {e}")

@main.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
            flash('Şifre sıfırlama talimatları içeren bir e-posta gönderildi.', 'info')
        else:
            flash('Bu e-posta adresi ile kayıtlı bir hesap bulunamadı.', 'danger')
        return redirect(url_for('main.login'))
    return render_template('reset_request.html', title='Şifre Sıfırla', form=form)

@main.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Geçersiz veya süresi dolmuş token.', 'warning')
        return redirect(url_for('main.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Şifreniz güncellendi! Artık giriş yapabilirsiniz.', 'success')
        return redirect(url_for('main.login'))
    return render_template('reset_token.html', title='Şifre Sıfırla', form=form)
