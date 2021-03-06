from email.utils import parseaddr
from smtplib import SMTPException

from django.contrib.auth.models import User
from api.models import Trip
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.modules.email.templates import WELCOME_MAIL_SUBJECT, WELCOME_MAIL_CONTENT
from api.modules.users.serializers import UserSerializer
from api.modules.users.validators import validate_password, validate_email
from nomad.settings import DEFAULT_EMAIL_SENDER


@api_view(['POST'])
@permission_classes((AllowAny,))
def sign_up(request):
    """
    Adds a new user to database
    Note: client's email is stored as username in database (NO explicit difference in email and username)
    :param request: contains first name, last name, email Id (username) and password
    :return: 400 if incorrect parameters are sent or email ID already exists
    :return: 201 successful
    """
    firstname = request.POST.get('firstname', None)
    lastname = request.POST.get('lastname', None)
    username = parseaddr(request.POST.get('email', None))[1].lower()
    password = request.POST.get('password', None)

    if not firstname or not lastname or not username or not password:
        # incorrect request received
        error_message = "Missing parameters in request. Send firstname, lastname, email, password"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    if not validate_email(username):
        error_message = "Invalid email Id"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    if not validate_password(password):
        error_message = "Invalid Password"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    try:
        User.objects.get(username=username)
        error_message = "Email Id already exists"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        user = User.objects.create_user(username, password=password)
        user.first_name = firstname
        user.last_name = lastname
        user.is_superuser = False
        user.is_staff = False
        user.save()
        try:
            to_list = [user.username]
            fullname = "{} {}".format(firstname, lastname)
            mail_subject = WELCOME_MAIL_SUBJECT.format(firstname)
            mail_content = WELCOME_MAIL_CONTENT.format(fullname)
            send_mail(mail_subject, mail_content, DEFAULT_EMAIL_SENDER, to_list, fail_silently=False)
        except SMTPException as e:
            error_message = "Registration successful. Unable to send a welcome email to user"
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        error_message = str(e)
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    success_message = "Successfully registered"
    return Response(success_message, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_user_profile(request):
    """
    Returns user object using user email address
    :param request:
    :param email:
    :return: 200 successful
    """
    if not hasattr(request.user, 'profile'):
        request.user.save()
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
def get_users_by_email(request, email):
    """
    Returns user object using user email address
    :param request:
    :param email:
    :return: 200 successful
    """
    users = User.objects.filter(is_staff=False, is_superuser=False, username__startswith=email)[:5]
    for user in users:
        if not hasattr(user, 'profile'):
            request.user.save()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_user_by_id(request, user_id):
    """
    Returns user object using user id
    :param request:
    :param user_id:
    :return: 400 if incorrect user ID is sent
    :return: 200 successful
    """
    try:
        user = User.objects.get(pk=user_id)
        if not hasattr(user, 'profile'):
            user.save()
    except User.DoesNotExist:
        error_message = "Invalid user ID"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
    serializer = UserSerializer(user)
    return Response(serializer.data)


@api_view(['POST'])
def update_profile_image(request):
    """
    Add a profile image for user
    :param request: contain profile_image_url
    :return: 400 if incorrect parameters are sent
    :return: 201 successful
    """
    profile_image_url = request.POST.get('profile_image_url')
    if not profile_image_url:
        # incorrect request received
        error_message = "Missing parameters in request. Send profile_image_url"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    if not hasattr(user, 'profile'):
        user.save()  # to handle RelatedObjectDoenNotExist exception on existing users
    user.profile.profile_image = profile_image_url
    user.save()
    return Response(None, status=status.HTTP_200_OK)


@api_view(['POST'])
def update_user_details(request):
    updated_firstname = request.POST.get('firstname', None)
    updated_lastname = request.POST.get('lastname', None)

    if not updated_firstname or not updated_lastname:
        error_message = "Missing parameters in request. Send firstname, lastname"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        user.first_name = updated_firstname
        user.last_name = updated_lastname
        user.save()
    except Exception as e:
        error_message = "User update failed due to {0}".format(str(e))
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def trip_friends_all(request):
    """
    Returns a list of friends user had been to trip
    :param request:
    :return: 200 successful
    """
    try:
        all_trips = User.objects.filter(trip__users=request.user).distinct()

    except User.DoesNotExist:
        error_message = "Trip does not exist"
        return Response(error_message, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    serializer = UserSerializer(all_trips, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def update_user_status(request):
    """
    Adds user status for user
    :param request:
    :return: 400 if incorrect parameters are sent
    :return: 200 successful
    """
    updated_status = request.POST.get('status', None)

    if not updated_status:
        error_message = "Missing parameters in request. Send user status"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = request.user.profile
        user.status = updated_status
        user.save(update_fields=['status'])
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def remove_profile_image(request):
    """
    Remove Profile image of user
    :param request:
    :return: 200 successful
    """
    user = request.user
    if not hasattr(user, 'profile'):
        user.save()  # to handle RelatedObjectDoenNotExist exception on existing users
    user.profile.profile_image = None
    user.save()
    return Response("Profile image succesfully removed.", status=status.HTTP_200_OK)


@api_view(['GET'])
def remove_user_status(request):
    """
    Remove user status of a user
    :param request:
    :return: 400 if profile does not exist
    :return: 200 successful
    """
    try:
        user = request.user.profile
        user.status = None
        user.save(update_fields=['status'])
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def delete_profile(request):
    """
    Remove user profile
    :param request:
    :return: 404 if profile does not exist
    :return: 200 successful
    """
    try:
        user_profile = request.user.profile
        if user_profile:
            user_profile.delete()
        for trip in Trip.objects.all():
            if request.user in trip.users.all():
                if trip.users.count() == 1:
                    trip.delete()
                else:
                    trip.users.remove(request.user)
        User.objects.get(id=request.user.id).delete()
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_200_OK)
=======
@api_view(['POST'])
def update_password(request):
    """
    update password
    :param request:
    :return: 400 if incorrect parameters are sent
    :return: 200 successful
    """
    old_password = request.POST.get('old_password', None)
    new_password = request.POST.get('new_password', None)

    if not old_password or not new_password:
        error_message = "Missing parameters in request. Send old_password, new_password"
        return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
    try:
        if request.user.check_password(old_password):
            if validate_password(new_password):
                request.user.set_password(new_password)
                request.user.save()
            else:
                return Response("Invalid new password", status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("Incorrect old password", status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    return Response("Password updated succesfully", status=status.HTTP_200_OK)
