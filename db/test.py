import requests
import json

url = "https://apiv2.shiprocket.in/v1/external/auth/login"

payload = json.dumps({
  "email": "sohil19158912@gmail.com",
  "password": "Faraz@19158912"
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)
token = response.text
print(token)

import requests
import json

url = "https://apiv2.shiprocket.in/v1/external/orders/create/adhoc"

payload = json.dumps({
  "order_id": "224-447",
  "order_date": "2019-07-24 11:11",
  "pickup_location": "Jammu",
  "comment": "Reseller: M/s Goku",
  "billing_customer_name": "Naruto",
  "billing_last_name": "Uzumaki",
  "billing_address": "House 221B, Leaf Village",
  "billing_address_2": "Near Hokage House",
  "billing_city": "New Delhi",
  "billing_pincode": 110002,
  "billing_state": "Delhi",
  "billing_country": "India",
  "billing_email": "naruto@uzumaki.com",
  "billing_phone": 9876543210,
  "shipping_is_billing": True,
  "shipping_customer_name": "Arreyan",
  "shipping_last_name": "Hamid",
  "shipping_address": "Here",
  "shipping_address_2": "There",
  "shipping_city": "Delhi",
  "shipping_pincode": "110001",
  "shipping_country": "India",
  "shipping_state": "Delhi",
  "shipping_email": "arreyanhamid@icloud.com",
  "shipping_phone": "9821870330",
  "order_items": [
    {
      "name": "Kunai",
      "sku": "chakra123",
      "units": 10,
      "selling_price": 900,
      "discount": "",
      "tax": "",
      "hsn": 441122
    }
  ],
  "payment_method": "Prepaid",
  "shipping_charges": 0,
  "giftwrap_charges": 0,
  "transaction_charges": 0,
  "total_discount": 0,
  "sub_total": 9000,
  "length": 10,
  "breadth": 15,
  "height": 20,
  "weight": 2.5
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjY1MzY5NjcsInNvdXJjZSI6InNyLWF1dGgtaW50IiwiZXhwIjoxNzQ5MDM2OTA3LCJqdGkiOiJ1b1ZCUG5PeU9yWkpBZFdGIiwiaWF0IjoxNzQ4MTcyOTA3LCJpc3MiOiJodHRwczovL3NyLWF1dGguc2hpcHJvY2tldC5pbi9hdXRob3JpemUvdXNlciIsIm5iZiI6MTc0ODE3MjkwNywiY2lkIjo2MzE2MjQxLCJ0YyI6MzYwLCJ2ZXJib3NlIjpmYWxzZSwidmVuZG9yX2lkIjowLCJ2ZW5kb3JfY29kZSI6IiJ9.wXBo5knthH-X1yJrkJ_hn0a5EWAAIlM6LERe3Sn1Er0'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
