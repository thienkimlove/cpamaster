## Offer API

### Get list of Networks

* URL : `http://super.antim.vn/core/networks/api/?key=<API_KEY>&length=100`

### List of Allow Devices

```text
DEVICES = (
    (1, "All"),
    (2, "Mobile"),
    (3, "Desktop"),
    (4, "Only Android Mobiles (Phone && Tablet)"),
    (5, "Only iOS Mobiles (Phone && Tablet)"),
    (6, "Only Iphone"),
    (7, "Only Ipad"),
)
```

### Get list of offers

* Main Url `http://super.antim.vn/core/offers/api/?key=<API_KEY>`

* Example response:

```text
{
  "draw": 0,
  "recordsTotal": 12663,
  "recordsFiltered": 12663,
  "data": [
    {
      "id": 7659,
      "name": "noon نون",
      "tracking_net": "https://atracking-auto.appflood.com/transaction/post_click?offer_id=58210499&aff_id=12695&aff_sub=#subId",
      "tracking_site": "http://super.antim.vn/core/camp/&offer_id=7659",
      "countries": "SA, AE",
      "os": "Only iOS Mobiles (Phone && Tablet)",
      "payout": 1.19
    }
  ],
  "result": "ok"
}
```

#### Params for OFFER API

* `length` total records can retrieve one time (max=500)

* `start` offset to start at.

* `name` substring for offer name. Using for search offer by name

* `uid` find offer by `id` or `net_offer_id`.

* `network_id` filter offer list by networkId. Obtain list of network by using  Network API.

* `device` filter offer list by device id, please see the list of devices above.

* `country` filter offer list by country code. Example(`country=VN`)

* `auto` filter offer by `auto`. Example (`auto=1` or `auto=0`)

* `active` filter offer by status. Example (`active=1` or `active=0`)

* `reject` filter offer by `reject`. Example (`reject=1` or `reject=0`)