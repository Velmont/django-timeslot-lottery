from django.core.mail import EmailMultiAlternatives
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from timeslot_lottery.models import Template
from timeslot_lottery.models import Week


def home(request):
    pass

def week_detail(request, template_slug, year, week_no):
    user = request.user
    try:
        week = Week.objects.get(template__slug=template_slug,
                                year=year, week_no=week_no)
    except Week.DoesNotExist:
        if not user.is_staff:
            raise Http404("Week not found")
        template = Template.objects.get(slug=template_slug)
        week = template.create_new_week((year, week_no))
    slots = week.slots.all()
    has_bid = user.slots_bid_for.filter(week=week).exists()
    if request.method == 'POST':
        slot_ids_bid_for = []
        for key, value in request.POST.items():
            if key.startswith('slot-'):
                slot_ids_bid_for.append(int(key[len('slot-'):]))
        for slot in slots:
            if slot.id in slot_ids_bid_for:
                slot.bidders.add(user)
            else:
                slot.bidders.remove(user)

    return render(request, 'timeslot_lottery/week_detail.html', {
        'slots': slots,
        'week': week,
        'user': request.user,
        'has_bid': has_bid,
    })


def template_detail(request, template_slug):
    template = get_object_or_404(Template, slug=template_slug)
    return render(request, 'timeslot_lottery/template_detail.html', {
        'template': template,
    })


# Utils

def notify_week_winners(week, winner_slots=None):
    if winner_slots is None:
        winner_slots = week.slots.filter(winner__isnull=False)
    for slot in winner_slots:
        _send_winner_email(slot.winner, slot)

def _send_winner_email(user, slot):
    if not user.email:
        return
    text_body, html_body = _create_winner_email_body(user, slot)
    title = "Got slot for {s.week.template} {s.week}".format(s=slot)
    msg = EmailMultiAlternatives(title, text_body, "skriv@nynorsk.no",
                                 [user.email])
    msg.attach_alternative(html_body, 'text/html')
    msg.send()

def _create_winner_email_body(user, slot):
    ctx = Context({
        'slot': slot,
        'template': slot.week.template,
        'user': user,
        'week': slot.week,
   })
    text_body = (
        get_template('timeslot_lottery/emails/winner.txt').render(ctx))
    html_body = (
        get_template('timeslot_lottery/emails/winner.html').render(ctx))
    return text_body, html_body
