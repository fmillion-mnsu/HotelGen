import random
import re

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import round_price as rp
from xl9045qi.hotelgen.models import Hotel, GiftShop, Product

def generate_giftshop(hotel: Hotel) -> tuple[GiftShop, list[Product]]:

    # The name of the hotel will come from the hotel dict
    giftshop_name = hotel.name

    # Sanitize
    giftshop_name = re.sub('^[Tt]he | at |Hotel|Motel|Resort','',giftshop_name)
    giftshop_name = giftshop_name.strip()
    property_base = giftshop_name

    # Create name
    giftshop_name = random.choice(data.misc['giftshop_name_templates']).format(name=giftshop_name).strip()

    unit_no = random.randint(10,200)
    unit_name = random.choice(data.misc['unit_names'])

    # Form entry
    giftshop_entry = GiftShop(
        name=giftshop_name,
        street=hotel.street + f" {unit_name} {unit_no}",
        city=hotel.city,
        state=hotel.state,
        zip=hotel.zip,
    )

    hotel_class = hotel.type.lower()

    productList = []

    # Generate products specifically for this hotel
    # We'll generate all products but with different prices.
    for product in data.gifts['property_specific']:
        this_name = product['name'].format(name=property_base)

        price = rand(product.get("price",{}).get("mean", 10.00), product.get("price",{}).get("sd",2.00))
        price = rp(price)
        multiplier = rand(
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("mean", 1.0),
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("sd", 0.1),
            min_val=1.0,
            max_val=3.0
        )
        price = rp(price * multiplier)
        if price < product.get("price",{}).get("min", 5.00):
            price = product.get("price",{}).get("min", 5.00)
        
        productList.append(Product(
            name=this_name, 
            price=price, 
            category="state_souvenir",
            sold_at=hotel.id))
    
    for product in data.gifts['state_specific']:
        state_name = data.state_data[hotel.state].get("full_name","State")
        this_name = product['name'].format(name=state_name)

        price = rand(product.get("price",{}).get("mean", 10.00), product.get("price",{}).get("sd",2.00))
        price = rp(price)
        multiplier = rand(
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("mean", 1.0),
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("sd", 0.1),
            min_val=1.0,
            max_val=3.0
        )
        price = rp(price * multiplier)
        if price < product.get("price",{}).get("min", 5.00):
            price = product.get("price",{}).get("min", 5.00)

        productList.append(Product(
            name=this_name, 
            price=price, 
            category="state_souvenir",
            sold_at=hotel.id))

    if hotel.tourist_region:
        for product in data.gifts['tourist_region_specific']:
            this_name = product['name'].format(name=hotel.tourist_region.replace("_"," ").title())

            price = rand(product.get("price",{}).get("mean", 10.00), product.get("price",{}).get("sd",2.00))
            price = rp(price)
            multiplier = rand(
                data.hotel_types[hotel_class].get("price_multiplier",{}).get("mean", 1.0),
                data.hotel_types[hotel_class].get("price_multiplier",{}).get("sd", 0.1),
                min_val=1.0,
                max_val=3.0
            )
            price = rp(price * multiplier)
            if price < product.get("price",{}).get("min", 5.00):
                price = product.get("price",{}).get("min", 5.00)

            productList.append(Product(
                name=this_name, 
                price=price, 
                category="state_souvenir",
                sold_at=hotel.id))
    
    for product in data.gifts['snacks']:
        this_name = product['name']

        price = rand(product.get("price",{}).get("mean", 10.00), product.get("price",{}).get("sd",2.00))
        price = rp(price)
        multiplier = rand(
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("mean", 1.0),
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("sd", 0.1),
            min_val=1.0,
            max_val=3.0
        )
        price = rp(price * multiplier)
        if price < product.get("price",{}).get("min", 5.00):
            price = product.get("price",{}).get("min", 5.00)

        productList.append(Product(
            name=this_name, 
            price=price, 
            category="food",
            sold_at=hotel.id))

    for product in data.gifts['supplies']:
        this_name = product['name']

        price = rand(product.get("price",{}).get("mean", 10.00), product.get("price",{}).get("sd",2.00))
        price = rp(price)
        multiplier = rand(
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("mean", 1.0),
            data.hotel_types[hotel_class].get("price_multiplier",{}).get("sd", 0.1),
            min_val=1.0,
            max_val=3.0
        )
        price = rp(price * multiplier)
        if price < product.get("price",{}).get("min", 5.00):
            price = product.get("price",{}).get("min", 5.00)

        productList.append(Product(
            name=this_name, 
            price=price, 
            category="supply",
            sold_at=hotel.id))

    # Done - Return the tuple
    return giftshop_entry, productList