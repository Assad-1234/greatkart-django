from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from carts.models import CartItem
from .forms import OrderForm
import datetime
from .models import Order,OrderProduct,Payment
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib import messages
from store.models import Product
from django.core.mail import send_mail
from django.conf import settings
from .models import Tax
# Create your views here.
@login_required(login_url='login')
def payments(request, order_number):
    """
    Payment page - Handles COD payment processing
    """
    current_user = request.user
    
    # Get the order
    order = get_object_or_404(Order, order_number=order_number, user=current_user, is_ordered=False)
    
    # Get cart items
    cart_items = CartItem.objects.filter(user=current_user, is_active=True)
    
    # Calculate totals
    total = order.order_total - order.tax
    tax = order.tax
    grand_total = order.order_total
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'COD')
        
        if payment_method == 'COD':
            try:
                # Create Payment record for COD
                payment = Payment()
                payment.user = current_user
                payment.payment_id = f"COD_{order_number}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                payment.payment_method = 'Cash on Delivery'
                payment.amount_paid = order.order_total
                payment.status = 'Pending'
                payment.save()
                
                # Update order
                order.payment = payment
                order.is_ordered = True
                order.status = 'New'
                order.save()
                
                # Process each cart item
                for cart_item in cart_items:
                    # Create order product
                    order_product = OrderProduct()
                    order_product.order = order
                    order_product.payment = payment
                    order_product.user = current_user
                    order_product.product = cart_item.product
                    order_product.quantity = cart_item.quantity
                    order_product.product_price = cart_item.product.price
                    order_product.ordered = True
                    order_product.save()
                    
                    # Add variations to order product
                    product_variation = cart_item.variations.all()
                    order_product.variations.set(product_variation)
                    order_product.save()
                    
                    # Reduce product stock
                    product = Product.objects.get(id=cart_item.product_id)
                    product.stock -= cart_item.quantity
                    product.save()
                
                # Clear the cart
                cart_items.delete()

                order_products = OrderProduct.objects.filter(order=order)

                products_list = ""

                for item in order_products:

                    variations = ""

                    for variation in item.variations.all():
                        variations += f"{variation.variation_category}: {variation.variation_value}, "

                    products_list += f"""
                Product: {item.product.product_name}
                Variations: {variations}
                Quantity: {item.quantity}
                Price: Rs{item.product_price}

                """

                send_mail(
                    subject=f'New Order #{order.order_number}',
                    message=f'''
                New Order Received!

                Order Number: {order.order_number}
                Customer: {order.full_name()}
                Phone: {order.phone}
                Email: {order.email}

                Products Ordered:
                {products_list}

                Tax: Rs{order.tax}
                Grand Total: Rs{order.order_total}
                ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=False,
                )

                # Clear the cart
                cart_items.delete()
                
                # ========== SEND ORDER RECEIVED EMAIL TO CUSTOMER ==========
                try:
                    mail_subject = 'Thank you for your order!'
                    message = render_to_string('orders/order_received_email.html', {
                        'user': request.user,
                        'order': order,
                        'payment': payment,
                    })
                    to_email = request.user.email
                    send_email = EmailMessage(mail_subject, message, to=[to_email])
                    send_email.send()
                except Exception as e:
                    print(f"Email sending failed: {e}")
                
                # ========== SEND ORDER NUMBER AND TRANSACTION ID BACK VIA JSONRESPONSE ==========
                # Check if it's an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    data = {
                        'order_number': order_number,
                        'transID': payment.payment_id,
                        'status': 'success',
                        'message': 'Order placed successfully!',
                    }
                    return JsonResponse(data)
                
                # For regular form submission (non-AJAX)
                messages.success(request, f'Order #{order_number} placed successfully! Transaction ID: {payment.payment_id}')
                return redirect('order_complete', order_number=order_number)
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': str(e)})
                else:
                    messages.error(request, f'Error processing order: {str(e)}')
                    return redirect('checkout')
    
    context = {
        'order': order,
        'cart_items': cart_items,
        'total': total,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'orders/payments.html', context)
def place_order(request, total=0, quantity=0):
    current_user = request.user
    # If the cart count is less than or equal to 0, then redirect back to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

        product_total = cart_item.product.price * cart_item.quantity

        product_tax = (
            product_total * cart_item.product.tax_percentage
        ) / 100

        tax += product_tax

    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order  = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order':order,
                'cart_items':cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request,'orders/payments.html',context)
        else:
            return redirect('checkout')
        
def order_complete(request ,order_number):

    # Get parameters from URL (for GET requests)
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')
    
    # If no order_number in GET, try to get from POST or session
    if not order_number and request.method == 'POST':
        order_number = request.POST.get('order_number')
    
    # If still no order_number, try to get from redirect parameters
    if not order_number:
        try:
            # Get the most recent order for the user
            latest_order = Order.objects.filter(user=request.user, is_ordered=True).latest('created_at')
            order_number = latest_order.order_number
        except Order.DoesNotExist:
            messages.error(request, 'No order found')
            return redirect('home')
    
    try:
        # Get the order
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        
        # Get ordered products
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity
        
        # Get payment details
        payment = Payment.objects.get(order=order) if hasattr(order, 'payment') else None
        
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order_number,
            'transID': transID or (payment.payment_id if payment else None),
            'payment': payment,
            'subtotal':subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
        
    except (Order.DoesNotExist, Payment.DoesNotExist) as e:
        messages.error(request, f'Order not found: {str(e)}')
        return redirect('home')


