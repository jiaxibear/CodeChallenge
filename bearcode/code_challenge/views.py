from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import transaction

# Decorator to use built-in authentication system
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import PasswordResetTokenGenerator

# Used to create and manually log in a user
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate

from code_challenge.models import *
from code_challenge.forms import *
import os
import time

@login_required
def home(request):
    # Sets up list of just the logged-in user's (request.user's) items
    user = request.user
    items = Post.objects.all().order_by('-created_at')
    return render(request, 'code_challenge/global_stream.html', {'items' : items, 'currentuser' : user})

@login_required
@transaction.atomic
def add_post(request):
    context = {}
    if request.method == 'GET':
        context['form'] = PostForm()
        return render(request, 'code_challenge/global_stream.html', context)

    # Creates a new item if it is present as a parameter in the request
    new_post = Post(text=request.POST['posttext'], user=request.user)
    
    new_post_form = PostForm(request.POST, instance=new_post)
    if not new_post_form.is_valid():
        print 'invalid here'  # something going wrong here
        context['form'] = new_post_form
        context['user'] = request.user
        context['items'] = Post.objects.all().order_by('-created_at')
        context['currentuser'] = request.user
        new_post = Post(text=request.POST['posttext'], user=request.user)
        new_post.save()
        return render(request, 'code_challenge/global_stream.html', context)
    new_post_form.save()

    return redirect(reverse('home'))

@login_required
@transaction.atomic
def add_comment(request):
    print "running into add comment"
    context = {}
    print "post id:" + str(request.GET['post_id'])

    if not 'post_id' in request.GET or not request.GET['post_id'] or not 'new_comment' in request.GET or not request.GET['new_comment']:
        print "invalid comment"
        context = {'comment_user': '', 'user_photo': '', 'created_at': '', 'comment_text': ''}
        return render(request, 'code_challenge/comment.json', context, content_type="application/json")

    request_user = str(request.user)
    comment_text = request.GET['new_comment'].strip()
    #print comment_text

    comment_post = Post.objects.get(id=int(request.GET['post_id']))
    comment_user = UserProfile.objects.get(username=request_user)
    #print comment_user
    #print type(comment_user)

    to_comment = Comment(user=comment_user, text=comment_text, post=comment_post)
    to_comment.save()

    try:
        resp = Comment.objects.get(id=to_comment.id)
        comment = {'comment_user': comment_user.username, 'user_photo': comment_user.image, 'created_at': to_comment.created_at, 'comment_text': to_comment.text}
        print comment
        return render(request, 'code_challenge/comment.json', {'comment': comment}, content_type="application/json")
    except Comment.DoesNotExist:
        print "error"
        comment = {'comment_user': '', 'user_photo': '', 'created_at': '', 'comment_text': ''}
        return render(request, 'code_challenge/comment.json', {'comment': comment}, content_type="application/json")

@login_required
@transaction.atomic
def get_comments(request):
    comments_set = Comment.get_comments(int(request.GET['post_id']))

    context = {}
    comments = []
    comments_iter = comments_set.iterator()
    # Peek at the first item in the iterator.
    try:
        first_item = next(comments_iter)
    except StopIteration:
        # No rows were found, so do nothing.
        context = {'size': 0, 'items': None}
        return render(request, 'code_challenge/comments.json', context, content_type='application/json')
    else:
        # At least one row was found, so iterate over
        # all the rows, including the first one.
        #print "found"
        from itertools import chain
        for comment in chain([first_item], comments_iter):
            profile_img = UserProfile.get_profile(comment.user.user.id).image

            item = {'comment_user': comment.user.username, 'user_photo': profile_img, 'created_at': comment.created_at, 'comment_text': comment.text}
            print item
            comments.append(item)

    #print "end"
    #print comments
    context = {'size': len(comments), 'comments': comments};
    #print context
    return render(request, 'code_challenge/comments.json', context, content_type='application/json')

@login_required
@transaction.atomic
def profile(request, username):
    # Show the profile page with the matching id
    user = get_object_or_404(User, username=username)
    # the profile of the user with matching id
    userprofile = get_object_or_404(UserProfile, user=user)
    # users that the current user is following
    currentuser = request.user
    currentuserprofile = get_object_or_404(UserProfile, user=currentuser)
    #currentuserprofile = currentuserprofiles[0]
    following = currentuserprofile.following.all()
    print following
    posts = Post.objects.filter(user=user).order_by('-created_at')

    context = {'user': user, 'posts': posts, 'userprofile': userprofile, 'currentuser': currentuser, 'following': following}
    return render(request, 'code_challenge/profile.html', context)

@login_required
@transaction.atomic
def follow(request, username):
    user = get_object_or_404(User, username=username)
    userprofile = get_object_or_404(UserProfile, user=user)
    #userprofile = userprofiles[0]
    posts = Post.objects.filter(user=user).order_by('-created_at')

    currentuser = request.user
    currentuserprofiles = get_object_or_404(UserProfile, user=currentuser)
    currentuserprofile = currentuserprofiles[0]
    currentuserprofile.following.add(user)
    currentuserprofile.save()
    following = currentuserprofile.following.all()
    context = {'user' : user, 'posts' : posts, 'currentuser' : currentuser, 'currentuserprofile' : currentuserprofile, 'userprofile': userprofile, 'following': following}
    print 'follow success'
    return render(request, 'code_challenge/profile.html', context)

@login_required
@transaction.atomic
def unfollow(request, username):
    user = get_object_or_404(User, username=username)
    userprofile = get_object_or_404(UserProfile, user=user)
    #userprofile = userprofiles[0]
    posts = get_object_or_404(Post, user=user).order_by('-created_at')

    currentuser = request.user
    currentuserprofiles = get_object_or_404(UserProfile, user=currentuser)
    currentuserprofile = currentuserprofiles[0]
    if user in currentuserprofile.following.all():
        currentuserprofile.following.remove(user) 
    currentuserprofile.save()
    following = currentuserprofile.following.all()
    context = {'user' : user, 'posts' : posts, 'currentuser' : currentuser, 'currentuserprofile' : currentuserprofile, 'userprofile': userprofile, 'following': following}
    print 'follow success'
    return render(request, 'code_challenge/profile.html', context)

@login_required
@transaction.atomic
def follower_stream(request):
    user = request.user
    userprofile = get_object_or_404(UserProfile, user=user)
    #userprofile = userprofiles[0]
    following = userprofile.following.all()
    posts = Post.objects.filter(user__in = following).order_by('-created_at');

    context = {'userprofile' : userprofile, 'posts': posts, 'currentuser': user}
    print len(posts)
    return render(request, 'code_challenge/follower_stream.html', context)

@login_required
@transaction.atomic
def edit_profile(request):
    profile_to_edit = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'GET':
        form = ProfileForm(instance=profile_to_edit)  # Creates form
        context = {'form':form, 'currentuser': request.user}        
        print "We are here at GET in edit_profile"  
        return render(request, 'code_challenge/edit_profile.html', context)

    # if method is POST, get form data to update the model
    form = ProfileForm(request.POST, instance=profile_to_edit)

    if form.is_valid():
        #context = {'form':form, 'currentuser': request.user} 
        #print "form is not valid"
        #form = ProfileForm() # A empty, unbound form
    #else:
        print "This is valid"
        print request.FILES.get('image', False);
        form.image =  handle_uploaded_file(request.FILES.get('image', False))
        form.save()
        userprofile = get_object_or_404(UserProfile, user=request.user)
        userprofile.image = form.image
        userprofile.save()
    posts = get_object_or_404(Post, user=request.user).order_by('-created_at')

    return render(request, 'code_challenge/profile.html', {'form': form, 'userprofile' : userprofile, 'currentuser': request.user, 'posts' : posts})

def handle_uploaded_file(f):
    if f != False :
        fileName, fileExtension = os.path.splitext(f.name)
        url = '/static/photos/{}{}'.format(time.time(), fileExtension)
        with open('./code_challenge'+ url, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)
        return url

@login_required
@transaction.atomic
def change_password(request):
    user = request.user
    #user.set_password('new_password')
    #user.save()
    return render(request, 'code_challenge/password_change_form.html', {'currentuser': request.user})

@transaction.atomic
def register(request):
    context = {}
    
    # Just display the registration form if this is a GET request
    if request.method == 'GET':
        context['form'] = RegistrationForm()
        return render(request, 'code_challenge/register.html', context)

    form = RegistrationForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'code_challenge/register.html', context)

    username = form.cleaned_data['username']
    password = form.cleaned_data['password1']
    firstname = form.cleaned_data['firstname']
    lastname = form.cleaned_data['lastname']
    

    # Creates the new user from the valid form data
    new_user = User.objects.create_user(username=username, \
                                        password=password, \
                                        first_name=firstname, \
                                        last_name=lastname, \
                                        email=username)
    new_user.save()

    # Logs in the new user and redirects to global stream
    new_user = authenticate(username=username, \
                            password=password)

    #print new_user.username + 'before create profile'
    new_profile = UserProfile(user=new_user, username=username, \
                                first_name=firstname, \
                                last_name=lastname)
    new_profile.save()
    #print 'after create profile'
    #print new_profile.username
    #print new_profile.first_name
    #print new_profile.last_name

    login(request, new_user)
    return redirect(reverse('home'))

def get_changes(request, log_id=-1):
    max_logentry = LogEntry.get_max_id()
    #posts = Post.get_changes(log_id)
    user = request.user
    items = Post.objects.all().order_by('-created_at')
    context = {"max_entry":max_logentry, "items":items, "currentuser":user} 
    return render(request, 'items.json', context, content_type='application/json')
    
