from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404, redirect
from .forms import *
from django.http import Http404
from .models import Location, Myrating, MyList
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Case, When
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import numpy as np
import random 


# Create your views here.

def index(request):
    locations = Location.objects.all()
    query = request.GET.get('q')

    if query:
        locations = Location.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'recommend/list.html', {'locations': locations})

    return render(request, 'recommend/list.html', {'locations': locations})


# Show details of the Location
def detail(request, location_id):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404
    locations = get_object_or_404(Location, id=location_id)
    location = Location.objects.get(id=location_id)
    temp = list(MyList.objects.all().values().filter(location_id=location_id,user=request.user))
    if request.method == "POST":
        rate = request.POST['rating']
        if Myrating.objects.all().values().filter(location_id=location_id,user=request.user):
            Myrating.objects.all().values().filter(location_id=location_id,user=request.user).update(rating=rate)
        else:
            q=Myrating(user=request.user,location=location,rating=rate)
            q.save()

        messages.success(request, "Rating has been submitted!")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    out = list(Myrating.objects.filter(user=request.user.id).values())

    # To display ratings in the Location detail page
    location_rating = 0
    rate_flag = False
    for each in out:
        if each['location_id'] == location_id:
            location_rating = each['rating']
            rate_flag = True
            break

    context = {'locations': locations,'location_rating':location_rating,'rate_flag':rate_flag}
    return render(request, 'recommend/detail.html', context)

# MyList functionality
def mylist(request):

    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404

    locations = Location.objects.filter(mylist__user=request.user)
    query = request.GET.get('q')
    print(query)

    if query:
        locations = Location.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'recommend/watch.html', {'locations': locations})

    return render(request, 'recommend/watch.html', {'locations': locations})


# To get similar Location based on user rating
def get_similar(location_name,rating,corrMatrix):
    similar_ratings = corrMatrix[location_name]*(rating-2.5)
    similar_ratings = similar_ratings.sort_values(ascending=False)
    return similar_ratings

# Recommendation Algorithm
def recommend(request):


    # this is for checking if user is logged in or not
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404

    # this is for getting all rated locations of logged in user
    location_rating=pd.DataFrame(list(Myrating.objects.all().values()))
    print("location_rating is:")

    # this checks redundency / duplicate
    new_user=location_rating.user_id.unique().shape[0]
    print("new User",new_user)
    current_user_id= request.user.id
    print("current_user_id",current_user_id)
	# if new user not rated any location
    n = random.randint(0,45)
    if current_user_id>new_user:
        location=Location.objects.get(id=19)
        q=Myrating(user=request.user,location=location,rating=0)
        q.save()


    userRatings = location_rating.pivot_table(index=['user_id'],columns=['location_id'],values='rating')
    print("The userRating is:",userRatings)
    userRatings = userRatings.fillna(0,axis=1)
    print("The userRating null fill is:",userRatings)
    corrMatrix = userRatings.corr(method='pearson')
    print("corrMatrix",corrMatrix)
    

    user = pd.DataFrame(list(Myrating.objects.filter(user=request.user).values())).drop(['user_id','id'],axis=1)
    print("user is:",user)
    user_filtered = [tuple(x) for x in user.values]
    print("user_filtered:",user_filtered)
    location_id_visited = [each[0] for each in user_filtered]
    print("location_id_visited:",location_id_visited)

    similar_locations = pd.DataFrame()
    for location,rating in user_filtered:
        similar_locations = similar_locations.append(get_similar(location,rating,corrMatrix),ignore_index = True)
        print("similar_locations",similar_locations)

    location_id = list(similar_locations.sum().sort_values(ascending=False).index)
    print("location_id",location_id)
    location_id_recommend = [each for each in location_id if each not in location_id_visited]
    print("location_id_recommend:",location_id_recommend)
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(location_id_recommend)])
    print("preserved:",preserved)
    location_list=list(Location.objects.filter(id__in = location_id_recommend).order_by(preserved)[:10])
    print("location_list is:",location_list)


    #this is for map 
    geo_code = []
    geo_label = []
    for loc in location_list:
        geo_code.append([float(loc.lalitude),float(loc.longitude)])
        geo_label.append(loc.title)
    
    long=0
    lats=0
    for x in geo_code:
        long=long+x[0]
        lats=lats+x[1]
    long = long/len(geo_code)
    lats = lats/len(geo_code)
    
    m = folium.Map(location=[np.mean(long), np.mean(lats)], zoom_start=10)

    marker_cluster = MarkerCluster().add_to(m)

    for i in range(len(geo_code)):
        folium.Marker(
            location=list(geo_code[i]),
            popup=geo_label[i],
            icon=folium.Icon(color="green", icon="ok-sign"),
        ).add_to(marker_cluster)

    m=m._repr_html_()
    #map code ends here

    context = {'location_list': location_list,'my_map':m}
    return render(request, 'recommend/recommend.html', context)


# Register user
def signUp(request):
    form = UserForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user.set_password(password)
        user.save()
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")

    context = {'form': form}

    return render(request, 'recommend/signUp.html', context)


# Login User
def Login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")
            else:
                return render(request, 'recommend/login.html', {'error_message': 'Your account disable'})
        else:
            return render(request, 'recommend/login.html', {'error_message': 'Invalid Login'})

    return render(request, 'recommend/login.html')


# Logout user
def Logout(request):
    logout(request)
    return redirect("login")


def addToWishlist(request, location_id):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404
    location = Location.objects.get(id=location_id)
    q=MyList(user=request.user,location=location,Visited=True)
    q.save()
    locations = Location.objects.all()
    query = request.GET.get('q')

    if query:
        locations = Location.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'recommend/list.html', {'locations': locations})
    messages.success(request, "Location added to your list!")

    return render(request, 'recommend/list.html', {'locations': locations})
