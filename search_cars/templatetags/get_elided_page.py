from django import template

register = template.Library()


@register.simple_tag
def get_elided_page(page_obj, page_num):
    return page_obj.paginator.get_elided_page_range(number=page_num if page_num else 1)