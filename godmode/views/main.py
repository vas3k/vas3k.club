from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied
from godmode.config import ADMIN, ITEMS_PER_PAGE
from godmode.filters import apply_filters, get_filterable_fields, FILTER_OPERATORS


@require_auth
def godmode(request):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    return render(request, "godmode/layout.html", {
        "admin": ADMIN,
    })


@require_auth
def godmode_list_model(request, model_name):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_list_access(request.me):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"У вас нет прав для просмотра раздела «{admin_model.title}», "
                       f"это могут делать только админы с ролями: {', '.join(admin_model.list_roles)}.",
        })

    # Get pagination parameters
    page = request.GET.get("page", 1)

    # Get filter parameters
    filter_field = request.GET.get("filter_field", "")
    filter_operator = request.GET.get("filter_operator", "")
    filter_value = request.GET.get("filter_value", "")

    # Get sorting parameters
    sort_field = request.GET.get("sort_field", "")
    sort_direction = request.GET.get("sort_direction", "")

    # Get all objects with pagination
    queryset = admin_model.model.objects.all()

    # Apply filters and sorting using the filters module
    queryset = apply_filters(queryset, admin_model.model, filter_field, filter_operator, filter_value, sort_field, sort_direction)

    paginator = Paginator(queryset, ITEMS_PER_PAGE)

    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)

    # Extract model fields for table columns
    columns = admin_model.get_list_fields()
    primary_key_field = admin_model.model._meta.pk.name

    # Get available fields for filtering
    filters = get_filterable_fields(admin_model.model)

    return render(request, "godmode/list.html", {
        "admin": ADMIN,
        "admin_model": admin_model,
        "columns": columns,
        "items": page_obj,
        "filters": filters,
        "filter_operators": FILTER_OPERATORS,
        "current_filters": {
            "field": filter_field,
            "operator": filter_operator,
            "value": filter_value,
        },
        "current_sort": {
            "field": sort_field,
            "direction": sort_direction,
        },
        "primary_key_field": primary_key_field,
        "show_create_button": admin_model.has_create_access(request.me),
    })


@require_auth
def godmode_edit_model(request, model_name, item_id):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_edit_access(request.me):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"У вас нет прав для редактирования записей таблицы «{admin_model.title}», "
                       f"это могут делать только админы с ролями: {', '.join(admin_model.edit_roles)}.",
        })

    # Get the model instance
    primary_key_field = admin_model.model._meta.pk.name
    item = get_object_or_404(admin_model.model, **{primary_key_field: item_id})

    # Create a dynamic form for the model
    EditFormClass = admin_model.get_form_class()

    # Handle form submission
    if request.method == "POST":
        form = EditFormClass(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("godmode_list_model", model_name=model_name)
    else:
        form = EditFormClass(instance=item)

    return render(request, "godmode/edit.html", {
        "admin": ADMIN,
        "admin_model": admin_model,
        "item": item,
        "form": form,
        "primary_key_field": primary_key_field,
        "show_delete_button": admin_model.has_delete_access(request.me),
    })


@require_auth
def godmode_delete_model(request, model_name, item_id):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_delete_access(request.me):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"У вас нет прав для удаления записей из таблицы «{admin_model.title}», "
                       f"это могут делать только админы с ролями: {', '.join(admin_model.delete_roles)}.",
        })

    # Get the primary key field name dynamically
    primary_key_field = admin_model.model._meta.pk.name

    # Get the model instance
    item = get_object_or_404(admin_model.model, **{primary_key_field: item_id})

    # Delete the item
    item.delete()

    # Redirect to the list view of the model
    return redirect("godmode_list_model", model_name=model_name)


@require_auth
def godmode_create_model(request, model_name):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    if not admin_model.has_create_access(request.me):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"У вас нет прав для создания записей в таблице «{admin_model.title}», "
                       f"это могут делать только админы с ролями: {', '.join(admin_model.create_roles)}.",
        })

    # Create a dynamic form for the model
    CreateFormClass = admin_model.get_form_class()

    # Handle form submission
    if request.method == "POST":
        form = CreateFormClass(request.POST)
        if form.is_valid():
            form.save()
            return redirect("godmode_list_model", model_name=model_name)
    else:
        form = CreateFormClass()

    return render(request, "godmode/create.html", {
        "admin": ADMIN,
        "admin_model": admin_model,
        "form": form,
    })


def godmode_show_page(request, page_name):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    admin_page = ADMIN.get_page(page_name)
    if not admin_page:
        raise Http404()

    if not admin_page.has_access(request.me):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"У вас нет прав для просмотра страницы «{admin_page.title}», "
                       f"это могут делать только админы с ролями: {', '.join(admin_page.access_roles)}.",
        })

    if not admin_page.view:
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Страницу еще не напрограммировали",
            "message": f"Вам нужно объявить view у страницы и написать функцию её обработки.",
        })

    return render(request, "godmode/page.html", {
        "admin": ADMIN,
        "admin_page": admin_page,
        "page": admin_page.view(request, admin_page)
    })


@require_auth
def godmode_action(request, model_name, item_id, action_code):
    if not ADMIN.has_access(request.me):
        raise AccessDenied()

    admin_model = ADMIN.get_model(model_name)
    if not admin_model or not admin_model.model:
        raise Http404()

    admin_action = admin_model.actions.get(action_code)
    if not admin_action:
        raise Http404()

    if not admin_action.has_access(request.me):
        return render(request, "godmode/message.html", {
            "admin": ADMIN,
            "title": "🥲 Вам сюда нельзя",
            "message": f"У вас нет прав для выполнения действия «{admin_action.title}», "
                       f"это могут делать только админы с ролями: {', '.join(admin_action.access_roles)}.",
        })

    # Get the model instance
    primary_key_field = admin_model.model._meta.pk.name
    item = get_object_or_404(admin_model.model, **{primary_key_field: item_id})

    # run the action
    context = dict(
        admin=ADMIN,
        admin_model=admin_model,
        admin_action=admin_action
    )
    if request.method == "GET":
        return admin_action.get(request, item, **context)
    elif request.method == "POST":
        return admin_action.post(request, item, **context)
    else:
        raise Http404()
