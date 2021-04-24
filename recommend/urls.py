from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signUp, name='signup'),
    path('login/', views.Login, name='login'),
    path('logout/', views.Logout, name='logout'),
    path('location/<int:location_id>/', views.detail, name='detail'),
    path('mylist/', views.mylist, name='mylist'),
    path('recommend/', views.recommend, name='recommend'),
    path('addwishlist/<int:location_id>/', views.addToWishlist, name='addToWishlist'),
]