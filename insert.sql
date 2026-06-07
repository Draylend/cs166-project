COPY users(login, password, phone_num, address, role, favorite_category)
FROM 'users.csv'
DELIMITER ','
CSV HEADER;

COPY item(item_id, item_name, category, starting_price, image_url, item_condition, description, seller_login, seller_role)
FROM 'item.csv'
DELIMITER ','
CSV HEADER;

COPY auction(auction_id, item_id, seller_login, seller_role, current_highest_bid, auction_status, start_time, end_time, winner_login, winner_role)
FROM 'auction.csv'
DELIMITER ','
CSV HEADER;

COPY bid(bid_id, auction_id, buyer_login, buyer_role, bid_amount, bid_timestamp)
FROM 'bid.csv'
DELIMITER ','
CSV HEADER;

COPY payment(payment_id, auction_id, buyer_login, buyer_role, amount, payment_status)
FROM 'payment.csv'
DELIMITER ','
CSV HEADER;

COPY shipment(shipment_id, auction_id, address, shipment_status, tracking_number)
FROM 'shipment.csv'
DELIMITER ','
CSV HEADER;
