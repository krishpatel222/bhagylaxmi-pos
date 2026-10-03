from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q

from accounts.decorators import admin_required
from .models import Expense
from .forms import ExpenseForm


@admin_required
def expense_list(request):
    """
    Admin-only view listing expenses with search, date filter, category filter, and pagination.
    """
    qs = Expense.objects.select_related('created_by').all()

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(expense_id__icontains=q) |
            Q(description__icontains=q) |
            Q(notes__icontains=q)
        )

    # Category filter
    category = request.GET.get('category', '').strip()
    if category:
        qs = qs.filter(category=category)

    # Date filter
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        qs = qs.filter(expense_date__gte=date_from)
    if date_to:
        qs = qs.filter(expense_date__lte=date_to)

    total_amount = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'expenses': page_obj,
        'page_obj': page_obj,
        'total_amount': total_amount,
        'categories': Expense.CATEGORY_CHOICES,
        'q': q,
        'category': category,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'expenses/expense_list.html', context)


@admin_required
def expense_create(request):
    """
    Admin-only view to add a new expense.
    """
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, f"Expense {expense.expense_id} created successfully!")
            return redirect('expenses:list')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ExpenseForm()

    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add New Expense'})


@admin_required
def expense_detail(request, expense_id):
    """
    Admin-only view for expense detail.
    """
    expense = get_object_or_404(Expense.objects.select_related('created_by'), expense_id=expense_id)
    return render(request, 'expenses/expense_detail.html', {'expense': expense})


@admin_required
def expense_edit(request, expense_id):
    """
    Admin-only view to edit an existing expense.
    """
    expense = get_object_or_404(Expense, expense_id=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f"Expense {expense.expense_id} updated successfully!")
            return redirect('expenses:detail', expense_id=expense.expense_id)
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expenses/expense_form.html', {'form': form, 'expense': expense, 'title': f'Edit Expense {expense.expense_id}'})


@admin_required
def expense_delete(request, expense_id):
    """
    Admin-only view to delete an expense via POST request.
    """
    expense = get_object_or_404(Expense, expense_id=expense_id)
    if request.method == 'POST':
        e_id = expense.expense_id
        expense.delete()
        messages.success(request, f"Expense {e_id} deleted successfully.")
        return redirect('expenses:list')

    return redirect('expenses:detail', expense_id=expense_id)
