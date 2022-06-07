import collections

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import generic

from .models import AuctionSetting, Item, Bid
from urllib.parse import quote


class AuctionSettingMixin:
  def __init__(self, **kwargs):
      super().__init__(**kwargs)
      self.active_auctions = None

  def dispatch(self, request, *args, **kwargs):
    self.active_auctions = AuctionSetting.objects.filter(active=True).order_by("id")
    if not self.active_auctions:
        return HttpResponseRedirect(reverse_lazy("no_active_auction_error"))
    return super().dispatch(request, *args, **kwargs)

  def get_context_data(self, **kwargs):
    ctxt = super().get_context_data(**kwargs)
    ctxt["auction_setting"] = self.active_auctions.first()
    ctxt["name"] = self.request.GET.get("name", "")
    ctxt["phone_number"] = self.request.GET.get("phone_number", "")    
    return ctxt

    
class NoActiveAuctionErrorView(generic.TemplateView):
  template_name = "no_active_auction_error.html"



class NameInputView(AuctionSettingMixin, generic.TemplateView):
  template_name = 'name_input.html'

  def post(self, request, *args, **kwargs):
    return HttpResponseRedirect("/bidding/?name=" + quote(request.POST["name"]) + "&phone_number=" + quote(request.POST["phone_number"]))
        


class BiddingView(AuctionSettingMixin, generic.TemplateView):
  template_name = 'bidding.html'

  def get_context_data(self, **kwargs):
    ctxt = super().get_context_data(**kwargs)
    items = Item.objects.all().order_by("-dt_closed")
    items_upcoming = []
    items_live = []
    items_closed = []
    for item in items:
      item.additional_winners = item.additional_winners()
      if item.live:
        items_live.append(item)
      elif item.closed:
        items_closed.append(item)
      else:
        items_upcoming.append(item)
    ctxt["items_upcoming"] = items_upcoming
    ctxt["items_live"] = items_live
    ctxt["items_closed"] = items_closed
    return ctxt


# Called by ajax.
def update_bids(request):
  items = Item.objects.all()
  item_updates = {}
  for item in items:
    if item.status != "upcoming":
      item_updates[item.id] = {"status": item.status, "winning_price": item.formatted_winning_price, "winning_name": item.winning_name, "additional_winners": item.additional_winners()}
      if item.status == "live":
        item_updates[item.id]["dt_closed"] = item.dt_closed.strftime("%d-%m-%Y %H:%M")
        item_updates[item.id]["remaining"] = item.time_until_close()
  return JsonResponse({'item_updates': item_updates})


# Called by ajax.
def add_bid(request, item_id, price, name, phone_number):
  item = get_object_or_404(Item, id=item_id)
  error = ""
  try:
    price = float(price)
  except:
    return JsonResponse({"error": "Your bid must be a number! What are you playing at? O.o"})
  if item.status != "live":
    if item.status == "unopened":
      error = "This item has not yet gone live. How did you even get here? :/"
    else:
      error = "This item is no longer live. Sorry about that. :("
  elif item.winning_price:
    if item.winners_num == 1:
      if price <= item.winning_price:
        error = "Your bid must be higher than the current winning bid (£" + item.formatted_winning_price + ")."
      elif item.winning_name == name and item.winning_phone_number == phone_number:
        error = "You're already winning this item - no need to outbid yourself!"
    elif item.winners_num > 1:
      lowest_winning_price = item.lowest_winning_price()
      highest_user_price = item.highest_user_price(name, phone_number)
      if price <= lowest_winning_price:
        error = "Your bid must be higher than the current lowest winning bid (£" + '{:0,.2f}'.format(lowest_winning_price) + ")."
      elif price <= highest_user_price:
        error = "Your bid must be higher than your previous bid (£" + '{:0,.2f}'.format(highest_user_price) + ")."
  elif price < item.base_price:
    error = "You bid must be higher than base price (£" + item.formatted_base_price + ")."
  if error == "":
    Bid.objects.create(item=item, name=name, price=price, phone_number=phone_number)
    if not item.winning_price or price > item.winning_price:
      item.winning_price = price
      item.winning_name = name
      item.winning_phone_number = phone_number
      item.save()
  return JsonResponse({'error': error})


class LeaderboardView(AuctionSettingMixin, generic.TemplateView):
  template_name = "leaderboard.html"

  def get_context_data(self, **kwargs):
    ctxt = super().get_context_data(**kwargs)
    items = Item.objects.all().order_by("-dt_closed")
    item_winners = []
    for item in items:
      if (item.live or item.closed) and item.winning_name:
        item_winners.append({"item": f"{item.promiser} - {item.name}", "name": item.winning_name, "name_phone_number": f"{item.winning_name}_{item.winning_phone_number}", "price": item.formatted_winning_price, "price_raw": item.winning_price})
        item.additional_winners = item.additional_winners()
        for winner in item.additional_winners:
          item_winners.append({"item": f"{item.promiser} - {item.name}", "name": winner["name"], "name_phone_number": f"{winner['name']}_{winner['phone_number']}", "price": winner["price"], "price_raw": winner["price_raw"]})
    leaderboard_dict = {}
    for item_winner in item_winners:
      if item_winner["name_phone_number"] in leaderboard_dict.keys():
        leaderboard_dict[item_winner["name_phone_number"]]["total_spend"] += item_winner["price_raw"]
      else:
        leaderboard_dict[item_winner["name_phone_number"]] = {"total_spend": item_winner["price_raw"], "name": item_winner["name"], "won_items": []}
      leaderboard_dict[item_winner["name_phone_number"]]["won_items"].append(f"{item_winner['item']} (£{item_winner['price']})")
    for i, bidder in leaderboard_dict.items():
      bidder["won_items"] = ", ".join([item for item in bidder["won_items"]])
    leaderboard_dict = collections.OrderedDict(sorted(leaderboard_dict.items(), key=lambda t:t[1]["total_spend"], reverse=True))
    ctxt["leaderboard_dict"] = leaderboard_dict
    return ctxt



class SuperuserOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
  def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class AdminPanelView(SuperuserOnlyMixin, AuctionSettingMixin, generic.TemplateView):
  template_name = "admin_panel.html"

  def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class MessageGeneratorView(SuperuserOnlyMixin, AuctionSettingMixin, generic.TemplateView):
  template_name = 'message_generator.html'
