from django.http import HttpResponse
from django.shortcuts import render
from store.models import Product,Variation
from .models import Cart,CartItem
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt, csrf_protect
# Create your views here.

def _cart_id(request):
    cart =  request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart
@csrf_exempt
def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)  # get product
    product_variation = []
    
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
            except:
                pass
    
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()
    
    is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
    
    if is_cart_item_exists:
        cart_items = CartItem.objects.filter(product=product, cart=cart)
        
        # Check if the same variation already exists in cart
        variation_found = False
        
        for cart_item in cart_items:
            existing_variations = list(cart_item.variations.all())
            
            # Compare by variation IDs instead of objects
            existing_var_ids = sorted([v.id for v in existing_variations])
            current_var_ids = sorted([v.id for v in product_variation])
            
            if existing_var_ids == current_var_ids:
                # Variation exists, increase quantity
                cart_item.quantity += 1
                cart_item.save()
                variation_found = True
                break
        
        if not variation_found:
            # Variation doesn't exist, create new cart item
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart,
            )
            if product_variation:
                cart_item.variations.add(*product_variation)
            cart_item.save()
    
    else:
        # No cart item exists for this product at all
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart,
        )
        if product_variation:
            cart_item.variations.add(*product_variation)
        cart_item.save()
    
    return redirect('cart')
    
def remove_cart(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    try:
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
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')

def cart(request,total=0,quantity=0,cart_items=None):
    try:
        tax = 0
        grand_total = 0
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