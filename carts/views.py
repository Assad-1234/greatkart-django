from django.http import HttpResponse
from django.shortcuts import render
from store.models import Product,Variation
from .models import Cart,CartItem
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
# Create your views here.

def _cart_id(request):
    cart =  request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart
@csrf_exempt
def add_cart(request, product_id):
    current_user = request.user
    product = Product.objects.get(id=product_id)  # get product
    product_variation = []
    
    # Get variations from POST request
    if request.method == 'POST':
        for item in request.POST:
            key = item
            value = request.POST[key]
            try:
                variation = Variation.objects.get(
                    product=product, 
                    variation_category__iexact=key, 
                    variation_value__iexact=value
                )
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass
    
    # ========== FOR AUTHENTICATED USERS ==========
    if current_user.is_authenticated:
        # Get all cart items for this user and product
        cart_items = CartItem.objects.filter(product=product, user=current_user, is_active=True)
        
        if cart_items.exists():
            # Check if the same variation already exists
            variation_found = False
            current_var_ids = sorted([v.id for v in product_variation])
            cart_item_to_update = None
            
            for cart_item in cart_items:
                existing_var_ids = sorted([v.id for v in cart_item.variations.all()])
                
                if existing_var_ids == current_var_ids:
                    # Same variation found - update this cart item
                    variation_found = True
                    cart_item_to_update = cart_item
                    break
            
            if variation_found:
                # Variation exists, increase quantity
                cart_item_to_update.quantity += 1
                cart_item_to_update.save()
            else:
                # Different variation - create new cart item
                cart_item = CartItem.objects.create(
                    product=product,
                    quantity=1,
                    user=current_user,
                    is_active=True
                )
                if product_variation:
                    cart_item.variations.add(*product_variation)
                cart_item.save()
        else:
            # No cart items for this product - create new
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                user=current_user,
                is_active=True
            )
            if product_variation:
                cart_item.variations.add(*product_variation)
            cart_item.save()
    
    # ========== FOR NON-AUTHENTICATED USERS ==========
    else:
        # Get or create cart using session
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))
        cart.save()
        
        # Get all cart items for this cart and product
        cart_items = CartItem.objects.filter(product=product, cart=cart, is_active=True)
        
        if cart_items.exists():
            # Check if the same variation already exists
            variation_found = False
            current_var_ids = sorted([v.id for v in product_variation])
            cart_item_to_update = None
            
            for cart_item in cart_items:
                existing_var_ids = sorted([v.id for v in cart_item.variations.all()])
                
                if existing_var_ids == current_var_ids:
                    # Same variation found - update this cart item
                    variation_found = True
                    cart_item_to_update = cart_item
                    break
            
            if variation_found:
                # Variation exists, increase quantity
                cart_item_to_update.quantity += 1
                cart_item_to_update.save()
            else:
                # Different variation - create new cart item
                cart_item = CartItem.objects.create(
                    product=product,
                    quantity=1,
                    cart=cart,
                    is_active=True
                )
                if product_variation:
                    cart_item.variations.add(*product_variation)
                cart_item.save()
        else:
            # No cart items for this product - create new
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart,
                is_active=True
            )
            if product_variation:
                cart_item.variations.add(*product_variation)
            cart_item.save()
    
    return redirect('cart')
    
def remove_cart(request, product_id, cart_item_id):
   
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    
    return redirect('cart')

def remove_cart_item(request, product_id, cart_item_id):
    
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')

def cart(request,total=0,quantity=0,cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items=CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items=CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total +=(cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2*total)/100
        grand_total = total + tax
    except ObjectDoesNotExist:
        pass #just ignore
    context = {
        'total':total,
        'quantity':quantity,
        'cart_items':cart_items,
        'tax':tax,
        'grand_total':grand_total,
    }
    return render(request, 'store/cart.html',context)
@login_required(login_url='login')
def checkout(request,total=0,quantity=0,cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items=CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items=CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total +=(cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2*total)/100
        grand_total = total + tax
    except ObjectDoesNotExist:
        pass #just ignore

    context = {
        'total':total,
        'quantity':quantity,
        'cart_items':cart_items,
        'tax':tax,
        'grand_total':grand_total,
    }
    return render(request,'store/checkout.html',context)