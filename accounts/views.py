from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages,auth
from .models import Account,UserProfile
from .forms import RegistrationForm,UserForm,UserProfileForm
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from carts.views import _cart_id
from carts.models import Cart, CartItem 
import requests
from orders.models import Order,OrderProduct
# Create your views here.
@csrf_exempt
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            password = form.cleaned_data['password']
            username = email.split('@')[0]
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email,username=username, password=password)
            user.phone_number = phone_number
            user.save()
            # user activation
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string('accounts/account_verification_email.html',{
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            messages.success(request, 'Thank you for registering with us. We have sent you a verification email to your email address. Please verify it.')
            return redirect('/accounts/login/?command=verification&email='+email)
    else:
        
        form = RegistrationForm()
    context = {
        'form': form,
    }
    return render(request,'accounts/register.html', context)
@csrf_exempt
def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(email=email, password=password)
        
        if user is not None:
            try:
                # Get session cart
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                
                if is_cart_item_exists:
                    # Get session cart items
                    session_cart_items = CartItem.objects.filter(cart=cart)
                    
                    # Get user's existing cart items
                    user_cart_items = CartItem.objects.filter(user=user)
                    
                    # Create lists for user's existing variations and IDs
                    ex_var_list = []
                    id_list = []
                    
                    for item in user_cart_items:
                        existing_variation = list(item.variations.all())
                        ex_var_list.append(existing_variation)
                        id_list.append(item.id)
                    
                    # Process each session cart item
                    for session_item in session_cart_items:
                        # Get variations of session cart item
                        product_variation = list(session_item.variations.all())
                        
                        # Check if this variation exists in user's cart
                        if product_variation in ex_var_list:
                            # Variation exists - update quantity
                            index = ex_var_list.index(product_variation)
                            item_id = id_list[index]
                            existing_item = CartItem.objects.get(id=item_id)
                            
                            # Add session item quantity to existing item
                            existing_item.quantity += session_item.quantity
                            existing_item.save()
                            
                            # Delete the session item
                            session_item.delete()
                        else:
                            # Variation doesn't exist - assign to user
                            session_item.user = user
                            session_item.cart = None
                            session_item.save()
                    
                    # Delete the empty session cart
                    cart.delete()
                    
            except Cart.DoesNotExist:
                pass
            except Exception as e:
                print(f"Error in login merge: {e}")
            
            # Login the user
            auth.login(request, user)
            messages.success(request, 'You are now logged in!')
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                # next=/cart/checkout/
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')
    return render(request, 'accounts/login.html')
@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out!')
    return redirect('login')

def activate(request,uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Congratulations! Your account is activated.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')
@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()
    userprofile, created = UserProfile.objects.get_or_create(
    user=request.user
)
    context = {
        'orders_count': orders_count,
        'userprofile': userprofile,
    }
    return render(request,'accounts/dashboard.html',context)

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user=Account.objects.get(email__exact=email)
            # Reset password
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html',{
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            messages.success(request, 'Password reset email has been sent to your email address.')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist!')
            return redirect('forgotPassword')
    return render(request,'accounts/forgotPassword.html')
def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid']=uid
        messages.success(request,'Please reset your password')
        return redirect('resetPassword')
    
    else:
        messages.error(request,'This link has been expired!')
        return redirect('login')
    
def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request,'Password reset successful')
            return redirect('login')
        else:
            messages.error(request,'Password do not match!')
            return redirect ('resetPassword')
    return render(request,'accounts/resetPassword.html')
@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders':orders
    }
    return render(request,'accounts/my_orders.html', context)
@login_required(login_url='login')    
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'userprofile':userprofile,
    }
    return render(request, 'accounts/edit_profile.html', context)

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Password updated successfully.')
                return redirect('change_password')
            else:
                messages.error(request, 'Please enter valid current password')
                return redirect('change_password')
        else:
            messages.error(request, 'Password does not match!')
            return redirect('change_password')
    
    return render(request, 'accounts/change_password.html')

@login_required(login_url='login')
def order_detail(request, order_id):
    """Display detailed information for a specific order"""
    # Get the order by order_number (which is a string)
    order = get_object_or_404(Order, order_number=order_id, user=request.user)
    
    # Get order products
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    
    # Calculate subtotal
    subtotal = 0
    for item in order_detail:
        subtotal += item.product_price * item.quantity
    
    # ===== GET TRANSACTION ID =====
    transaction_id = None
    try:
        # Try to get from order payment
        if order.payment:
            transaction_id = order.payment.payment_id
        # If not, try to get from order products
        elif order_detail and order_detail.first():
            if order_detail.first().payment:
                transaction_id = order_detail.first().payment.payment_id
    except:
        pass
    
    # If still no transaction ID, generate a fallback
    if not transaction_id:
        transaction_id = f"COD_{order.order_number}"
    
    # ===== GET PAYMENT STATUS =====
    payment_status = None
    try:
        if order.payment:
            payment_status = order.payment.status
        elif order_detail and order_detail.first() and order_detail.first().payment:
            payment_status = order_detail.first().payment.status
    except:
        payment_status = "Pending"
    
    context = {
        'order_detail': order_detail,
        'order': order,
        'subtotal': subtotal,
        'transaction_id': transaction_id,  # Pass transaction ID to template
        'payment_status': payment_status,  # Pass payment status
    }
    return render(request, 'accounts/order_detail.html', context)