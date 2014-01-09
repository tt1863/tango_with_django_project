from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from rango.models import Category, Page
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from datetime import datetime

def index(request):
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)

    # Construct a dictionary to pass to the template engine as its context.
    # Note the key boldmessage is the same as {{ boldmessage }} in the template!
    category_list = Category.objects.order_by('-likes')[:5]
    context_dict = {'categories': category_list}
    
    for category in category_list:
        category.url = encode_url(category.name)
        
    page_list = Page.objects.order_by('-views')[:5]
    context_dict['pages'] = page_list
    
    if request.session.get('last_visit'):
        # The session has a value for the last visit
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)
        
        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        # The get returns None, and the session does not have a value for the last visit.
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1
        
    return render_to_response('rango/index.html', context_dict, context)
    

def about(request):
    context = RequestContext(request)
    
    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0
    
    context_dict = {'title': "About", 'visits': count}
    return render_to_response('rango/about.html', context_dict, context)

def category(request, category_name_url):
    # Request our context from the request passed to us.
    context = RequestContext(request)
    
    # Change underscores in the category name to spaces.
    # URLs don't handle spaces well, so we encode them as underscores.
    # We can then simply replace the underscores with spaces again to get the name.
    category_name = category_name_url.replace('_', ' ')

    # Create a context dictionary which we can pass to the template rendering engine.
    # We start by containing the name of the category passed by the user.
    context_dict = {'category_name': category_name,
                    'category_name_url': category_name_url}

    try:
        # Can we find a category with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(name=category_name)

        # Retrieve all of the associated pages.
        # Note that filter returns >= 1 model instance.
        pages = Page.objects.filter(category=category)

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category
    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything - the template displays the "no category" message for us.
        pass

    # Go render the response and return it to the client.
    return render_to_response('rango/category.html', context_dict, context)

@login_required
def add_category(request):
    context = RequestContext(request)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        
        form.save(commit=True)
        
        return index(request)
    else:
        form = CategoryForm()
        
    return render_to_response('rango/add_category.html', {'form': form}, context)

@login_required
def add_page(request, category_name_url):
    context = RequestContext(request)
    
    category_name = decode_url(category_name_url)
    if request.method == 'POST':
        form = PageForm(request.POST)
        
        if form.is_valid():
            # This time we cannot commit straight away.
            # Not all fields are automatically populated!
            page = form.save(commit=False)
            
            cat = Category.objects.get(name=category_name)
            page.category = cat
            
            # Also, create a default value for the number of views
            page.views = 0
            
            # With this, we can then save our new model instance
            page.save()
            
            # Now that the page is saved, display the category instead
            return category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()
        
    return render_to_response('rango/add_page.html',
                              {'category_name_url': category_name_url,
                               'category_name': category_name,
                               'form': form},
                              context)
    
def register(request):
    # Like before, get the request's context.
    context = RequestContext(request)
    
    # A boolean value for telling the template whether the registration was successful
    # Set to False initially. Code changes value to True when registration succeeds
    registered = False
    
    # If it's a HTTP POST, we're interested in processing form data
    if request.method == 'POST':
        # Attempt to grab information from the raw form information
        # Note that we make use of both UserForm and UserProfileForm
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        
        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database
            user = user_form.save()
            
            # Now we hash the password with the set_password method
            # Once hashed, we can update the user object
            user.set_password(user.password)
            user.save()
            
            # Now we sort out the UserProfile instance
            # Since we need to set the user attribute ourselves, we set commit=False
            # This delays saving the model until we're ready to avoid integrity problems
            profile = profile_form.save(commit=False)
            profile.user = user
            
            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and put it in the UserProfile model...
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
                
            # Now we save the UserProfile model instance
            profile.save()
            
            # Update our variable to tell the template registration is complete
            registered = True
            
        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal
        # They'll also be shown to the user
        else:
            print user_form.errors, profile_form.errors
    
    # Not a HTTP POST, so we render our form using two ModelForm instances
    # These forms will be blank, ready for user input
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()
            
    # Render the template depending on the context
    return render_to_response('rango/register.html',
                              {'user_form': user_form, 'profile_form': profile_form, 'registered': registered},
                              context)
    
def user_login(request):
    # Like before, obtain the context for the user's request
    context = RequestContext(request)
    
    # If the request is a HTTP POST, try to pull out the relevant information
    if request.method == 'POST':
        # Gather the username and password provided by the user
        # This information is obtained from the login form
        username = request.POST['username']
        password = request.POST['password']
        
        # User Django's machinery to attemp to see if the username/password
        # combination is valid - a User object is returned if it is
        user = authenticate(username=username, password=password)
        
        # If we have a User object, the details are correct
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found
        if user is not None:
            # is the account active? It could have been disabled
            if user.is_active:
                # If the account is valid and active, we can log the user in
                login(request, user)
                return HttpResponseRedirect('/rango')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your rango account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid login details supplied.")
    
    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render_to_response('rango/login.html', {}, context)
    
# User the login_required() decorator to ensure only those logged in can access the view
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)
    
    # Take the user back to the homepage.
    return HttpResponseRedirect('/rango/')
    
@login_required
def restricted(request):
    context = RequestContext(request)
    message = "Since you're logged in, you can see this text!"
    return render_to_response('rango/restricted.html', {'message': message}, context)
    
def decode_url(category_name_url):
    category_name = category_name_url.replace('_', ' ')
    return category_name

def encode_url(category_name):
    category_name_url = category_name.replace(' ', '_')
    return category_name_url
    
    
    