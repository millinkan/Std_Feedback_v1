from django import template

register = template.Library()


def _initial(name: str) -> str:
    if not name or not name.strip():
        return '?'
    return name.strip()[0].upper()


@register.inclusion_tag('club/includes/member_avatar.html')
def member_avatar(member, size=48, extra_class='', alt=None):
    px = int(size)
    alt_text = alt if alt is not None else getattr(member, 'display_name', 'Member')
    show_img = bool(getattr(member, 'avatar', None) and getattr(member.avatar, 'name', ''))
    font_px = max(11, min(round(px * 0.42), 40))
    return {
        'member': member,
        'size': px,
        'font_px': font_px,
        'extra_class': extra_class.strip(),
        'alt': alt_text,
        'show_img': show_img,
        'initial': _initial(getattr(member, 'display_name', '') or ''),
    }
